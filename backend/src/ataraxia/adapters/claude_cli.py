"""Lesson generation through the Claude Code CLI in print mode, on the owner's subscription.

The CLI runs with no tools, MCP servers, project settings, or session history; an
empty working directory; an explicit environment that never contains API keys (so
the subscription is always what pays); and a hard timeout that ends the whole
process group. The lesson comes back as structured output validated against
`LessonContent`.

The CLI still expands `@path` mentions in the prompt into file contents, even with
tools disabled, and the prompt carries owner text and stored lessons. Every `@` is
therefore sent with a zero-width space after it, and the space is removed from the
answer, so no prompt can make the worker read its own files (such as its login).
"""

import json
import os
import re
import signal
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from importlib import resources
from typing import Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from ataraxia.application.ports import (
    GeneratedLesson,
    GenerationError,
    GenerationUsage,
    LessonBrief,
    LoginStatus,
)
from ataraxia.domain.jobs import JobErrorCode
from ataraxia.domain.lessons import WORD_TARGETS, LessonContent
from ataraxia.domain.subjects import SUBJECT_IDS, SUBJECTS, subject

PROMPT_VERSION = "lesson-2026-11-24"
SYSTEM_PROMPT = resources.files("ataraxia.adapters.prompts").joinpath("lesson_system.md")
MAX_MESSAGE_CHARS = 300
SAFE_PATH = "/usr/local/bin:/usr/bin:/bin"
AT = "@"
INERT_AT = "@\u200b"  # "@" followed by a zero-width space: not a file mention


@dataclass(frozen=True)
class CliResult:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int


class CliRunner(Protocol):
    def run(
        self, args: Sequence[str], stdin: str, env: Mapping[str, str], timeout: float
    ) -> CliResult:
        """Run a command with exactly `env`, feeding `stdin`; never raises on failure."""
        ...


class SubprocessCliRunner:
    """Runs the CLI in a fresh empty directory in its own process group.

    On timeout the group gets SIGTERM, then SIGKILL after `grace_seconds`.
    """

    def __init__(self, grace_seconds: float = 10) -> None:
        self._grace_seconds = grace_seconds

    def run(
        self, args: Sequence[str], stdin: str, env: Mapping[str, str], timeout: float
    ) -> CliResult:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="ataraxia-claude-") as workdir:
            try:
                process = subprocess.Popen(
                    list(args),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=workdir,
                    env=dict(env),
                    text=True,
                    start_new_session=True,
                )
            except OSError as error:
                return CliResult(None, "", str(error), False, _elapsed_ms(started))
            timed_out = False
            try:
                stdout, stderr = process.communicate(stdin, timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                stdout, stderr = _stop(process, self._grace_seconds)
        return CliResult(process.returncode, stdout, stderr, timed_out, _elapsed_ms(started))


def _stop(process: subprocess.Popen[str], grace_seconds: float) -> tuple[str, str]:
    """Ask the process group to stop, then kill it if it does not in time."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
        return process.communicate(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        return process.communicate()
    except ProcessLookupError:
        return process.communicate()


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


@dataclass(frozen=True)
class ClaudeCliConfig:
    """Where the CLI is and how it authenticates. `oauth_token` overrides the login."""

    executable: str
    model: str
    timeout_seconds: float
    home: str
    config_dir: str | None = None
    oauth_token: str | None = field(default=None, repr=False)


class ClaudeCliGenerator:
    """`LessonGenerator` backed by `claude -p`."""

    def __init__(self, config: ClaudeCliConfig, runner: CliRunner) -> None:
        self._config = config
        self._runner = runner

    def generate(self, brief: LessonBrief) -> GeneratedLesson:
        result = self._runner.run(
            command(self._config, brief),
            build_prompt(brief),
            environment(self._config),
            self._config.timeout_seconds,
        )
        return parse_result(result, brief)


class ClaudeCliLogin:
    """`LoginProbe` backed by `claude auth status`, which makes no model request."""

    def __init__(self, config: ClaudeCliConfig, runner: CliRunner) -> None:
        self._config = config
        self._runner = runner

    def status(self) -> LoginStatus | None:
        result = self._runner.run(
            [self._config.executable, "auth", "status"], "", environment(self._config), 30
        )
        if result.timed_out:
            return None
        try:
            payload = _AuthStatus.model_validate_json(result.stdout)
        except ValidationError:
            return None
        return LoginStatus(logged_in=payload.loggedIn, expires_at=payload.loginExpiresAt)


class _AuthStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    loggedIn: bool  # the CLI's own camelCase names
    loginExpiresAt: datetime | None = None


def command(config: ClaudeCliConfig, brief: LessonBrief) -> list[str]:
    """The CLI arguments; flags verified against Claude Code 2.1.332."""
    return [
        config.executable,
        "--print",
        "--safe-mode",
        "--tools",
        "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--max-turns",
        "3",
        "--model",
        config.model,
        "--system-prompt",
        SYSTEM_PROMPT.read_text(encoding="utf-8"),
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(lesson_schema(brief), separators=(",", ":")),
    ]


def environment(config: ClaudeCliConfig) -> dict[str, str]:
    """An explicit environment. Nothing is inherited, so API keys can never leak in."""
    env = {
        "PATH": SAFE_PATH,
        "HOME": config.home,
        "LANG": "C.UTF-8",
        "DISABLE_UPDATES": "1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    }
    if config.config_dir:
        env["CLAUDE_CONFIG_DIR"] = config.config_dir
    if config.oauth_token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = config.oauth_token
    return env


def lesson_schema(brief: LessonBrief) -> dict[str, object]:
    """`LessonContent`'s JSON schema with references inlined and titles removed.

    A non-topic brief allows only its own subject, so the writer cannot drift.
    """
    schema = LessonContent.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(node: object, field_names: bool = False) -> object:
        # Inside a `properties` mapping the keys are field names (one is "title"),
        # not schema keywords, so they are all kept.
        if isinstance(node, dict):
            if "$ref" in node:
                return inline(definitions[str(node["$ref"]).rsplit("/", 1)[-1]])
            return {
                key: inline(value, field_names=key == "properties")
                for key, value in node.items()
                if field_names or key != "title"
            }
        if isinstance(node, list):
            return [inline(item) for item in node]
        return node

    inlined = inline(schema)
    properties = inlined.get("properties") if isinstance(inlined, dict) else None
    if not isinstance(inlined, dict) or not isinstance(properties, dict):
        raise TypeError("LessonContent schema has no properties")
    allowed = list(SUBJECT_IDS) if brief.subject is None else [brief.subject]
    properties["subject"] = {"type": "string", "enum": allowed}
    return inlined


def build_prompt(brief: LessonBrief) -> str:
    """The user message: the brief as plain sections. Owner text is fenced as data."""
    low, high = WORD_TARGETS[brief.length]
    parts: list[str] = []
    if brief.parent is not None:
        parts.append(_follow_up_section(brief))
    elif brief.topic is not None:
        catalog = "\n".join(f"- {item.id}: {item.label} ({item.description})" for item in SUBJECTS)
        parts.append(
            "Write a lesson on the topic the reader asked for. Interpret the request "
            "generously; if it is broad, choose a specific, rewarding angle on it.\n\n"
            f"<reader_request>\n{brief.topic}\n</reader_request>\n\n"
            "Set `subject` to the best fit from this catalog and follow that subject's "
            f"usual approach:\n{catalog}"
        )
    else:
        assert brief.subject is not None
        parts.append(
            "Write today's lesson. Choose the topic yourself: something specific (one "
            "work, person, event, idea, place, or theme) rather than a survey, and "
            "something this reader is unlikely to have studied closely."
        )
    if brief.subject is not None:
        info = subject(brief.subject)
        parts.append(f"Subject: {info.label} ({info.description}).\nGuidance: {info.guidance}")
    parts.append(
        f"Length: {low:,}–{high:,} words in `body_markdown`. Today's date is "
        f"{brief.local_date.isoformat()}; use it only if a real anniversary fits naturally."
    )
    parts.extend(
        section
        for section in (
            _titles(
                "Recent lessons in this subject; do not repeat or closely overlap them:",
                brief.recent_titles_in_subject,
            ),
            _titles("Recent lessons in other subjects; vary from them:", brief.recent_titles),
            _titles(
                "Lessons the reader liked (taste hints, not topics to repeat):", brief.liked_titles
            ),
            _titles("Lessons the reader did not enjoy:", brief.disliked_titles),
        )
        if section
    )
    return defuse_mentions("\n\n".join(parts) + "\n")


def defuse_mentions(prompt: str) -> str:
    """Make every `@` inert so the CLI cannot treat text as a file to attach."""
    return prompt.replace(AT, INERT_AT)


def _restore_mentions(value: object) -> object:
    """Undo `defuse_mentions` in the answer, in case the writer copied the space."""
    if isinstance(value, str):
        return value.replace(INERT_AT, AT)
    if isinstance(value, list):
        return [_restore_mentions(item) for item in value]
    if isinstance(value, dict):
        return {key: _restore_mentions(item) for key, item in value.items()}
    return value


def _follow_up_section(brief: LessonBrief) -> str:
    parent = brief.parent
    assert parent is not None
    ideas = "\n".join(f"- {idea}" for idea in parent.key_ideas)
    if brief.direction is not None:
        ask = (
            "The reader chose to go deeper in this direction:\n"
            f"{brief.direction.title}: {brief.direction.description}"
        )
    else:
        ask = (
            "The reader asked this question after reading it:\n"
            f"<reader_question>\n{brief.question}\n</reader_question>"
        )
    return (
        "Write a follow-up to a lesson the reader has just finished. Continue the thread: "
        "build on what it established, add a short bridge at the start, and do not "
        "re-explain what it already covered.\n\n"
        f'The earlier lesson, "{parent.title}", key ideas:\n{ideas}\n\n'
        f"Its full text:\n<earlier_lesson>\n{parent.body_markdown}\n</earlier_lesson>\n\n"
        f"{ask}"
    )


def _titles(heading: str, titles: Sequence[str]) -> str:
    if not titles:
        return ""
    return heading + "\n" + "\n".join(f"- {title}" for title in titles)


class _CliPayload(BaseModel):
    """The fields of `claude -p --output-format json` this adapter relies on."""

    model_config = ConfigDict(extra="ignore")

    is_error: bool = False
    subtype: str | None = None
    result: str | None = None
    api_error_status: int | None = None
    structured_output: dict[str, object] | None = None
    duration_ms: int | None = None
    total_cost_usd: float | None = None
    credential_expires_at: datetime | None = None
    usage: dict[str, object] = {}
    modelUsage: dict[str, dict[str, object]] = {}  # the CLI's own camelCase name


_AUTH_TEXT = re.compile(
    r"not logged in|login expired|failed to authenticate|invalid authentication|/login"
)
_LIMIT_TEXT = re.compile(r"hit your .*limit|usage limit|limit reached|limit will reset")
_NO_VALID_OUTPUT = frozenset({"error_max_turns", "error_max_structured_output_retries"})


def parse_result(result: CliResult, brief: LessonBrief) -> GeneratedLesson:
    """Turn a CLI run into validated content, or raise `GenerationError` with a code."""
    if result.timed_out:
        raise GenerationError("claude_timeout", "Claude did not finish within the time limit")
    try:
        payload = _CliPayload.model_validate(json.loads(result.stdout))
    except (json.JSONDecodeError, ValidationError):
        detail = _first_line(result.stderr) or f"exit status {result.returncode}"
        raise GenerationError("claude_error", f"The CLI returned no result ({detail})") from None
    if payload.is_error or result.returncode != 0:
        code = _classify(payload)
        answered = {"claude_auth": False, "claude_usage_limit": True, "invalid_output": True}.get(
            code
        )
        usage = _usage(payload, result.duration_ms, logged_in=answered)
        raise GenerationError(code, _first_line(payload.result or ""), usage)
    usage = _usage(payload, result.duration_ms, logged_in=True)
    if payload.structured_output is None:
        raise GenerationError(
            "invalid_output", f"No structured output ({payload.subtype or 'unknown'})", usage
        )
    try:
        content = LessonContent.model_validate(_restore_mentions(payload.structured_output))
    except ValidationError as error:
        fields = sorted({".".join(str(part) for part in e["loc"]) for e in error.errors()})
        raise GenerationError(
            "invalid_output", f"Output failed validation: {', '.join(fields)}", usage
        ) from None
    if brief.subject is not None and content.subject != brief.subject:
        raise GenerationError("invalid_output", "Output used a different subject", usage)
    return GeneratedLesson(content=content, usage=usage, prompt_version=PROMPT_VERSION)


def _classify(payload: _CliPayload) -> JobErrorCode:
    text = (payload.result or "").lower()
    if payload.api_error_status in (401, 403) or _AUTH_TEXT.search(text):
        return "claude_auth"
    if payload.api_error_status == 429 or _LIMIT_TEXT.search(text):
        return "claude_usage_limit"
    if payload.subtype in _NO_VALID_OUTPUT:
        # The writer kept producing output that failed the schema.
        return "invalid_output"
    return "claude_error"


def _usage(payload: _CliPayload, measured_ms: int, logged_in: bool | None) -> GenerationUsage:
    def count(key: str) -> int:
        value = payload.usage.get(key)
        return value if isinstance(value, int) else 0

    model = max(
        payload.modelUsage,
        key=lambda name: _int(payload.modelUsage[name].get("outputTokens")),
        default=None,
    )
    input_tokens = sum(
        count(key)
        for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )
    return GenerationUsage(
        model=model,
        duration_ms=payload.duration_ms if payload.duration_ms is not None else measured_ms,
        input_tokens=input_tokens or None,
        output_tokens=count("output_tokens") or None,
        cost_usd=payload.total_cost_usd,
        login_expires_at=payload.credential_expires_at,
        logged_in=logged_in,
    )


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _first_line(text: str) -> str:
    line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return line[:MAX_MESSAGE_CHARS]
