"""The Claude CLI adapter: command, environment, prompt, and result classification."""

import json
import stat
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from ataraxia.adapters.claude_cli import (
    ClaudeCliConfig,
    ClaudeCliGenerator,
    ClaudeCliLogin,
    CliResult,
    SubprocessCliRunner,
    build_prompt,
    command,
    environment,
    lesson_schema,
    parse_result,
)
from ataraxia.application.ports import GenerationError, LessonBrief, ParentLesson
from ataraxia.domain.lessons import Direction

FIXTURES = Path(__file__).parents[1] / "fixtures" / "claude"
CONFIG = ClaudeCliConfig(
    executable="/usr/local/bin/claude",
    model="opus",
    timeout_seconds=600,
    home="/home/app",
    config_dir="/home/app/.claude",
)
ART = LessonBrief(
    kind="daily",
    local_date=date(2026, 11, 24),
    length="standard",
    subject="art",
    recent_titles_in_subject=("The Night Watch Was Never Night",),
    liked_titles=("How Bridges Stay Up",),
)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def ok(stdout: str) -> CliResult:
    return CliResult(returncode=0, stdout=stdout, stderr="", timed_out=False, duration_ms=5)


class RecordingRunner:
    def __init__(self, result: CliResult) -> None:
        self.result = result
        self.calls: list[tuple[list[str], str, dict[str, str], float]] = []

    def run(
        self, args: Sequence[str], stdin: str, env: Mapping[str, str], timeout: float
    ) -> CliResult:
        self.calls.append((list(args), stdin, dict(env), timeout))
        return self.result


def test_generates_a_lesson_from_a_real_cli_result() -> None:
    runner = RecordingRunner(ok(fixture("success.json")))
    lesson = ClaudeCliGenerator(CONFIG, runner).generate(ART)

    assert lesson.content.subject == "art"
    assert lesson.content.title.startswith("Fog on Paper")
    assert lesson.usage.model == "claude-opus-5-5"
    assert lesson.usage.output_tokens and lesson.usage.output_tokens > 1000
    assert lesson.usage.login_expires_at == datetime(2026, 12, 22, 20, 14, 18, 992000, UTC)
    args, stdin, _env, timeout = runner.calls[0]
    assert timeout == 600
    assert "The Night Watch Was Never Night" in stdin
    assert "How Bridges Stay Up" in stdin


def test_command_disables_tools_customizations_and_persistence() -> None:
    args = command(CONFIG, ART)
    assert args[0] == "/usr/local/bin/claude"
    for flag in ("--print", "--safe-mode", "--strict-mcp-config", "--no-session-persistence"):
        assert flag in args
    assert args[args.index("--tools") + 1] == ""
    assert args[args.index("--output-format") + 1] == "json"
    assert args[args.index("--model") + 1] == "opus"
    assert not any(arg.startswith("--dangerously") for arg in args)


def test_environment_is_explicit_and_never_carries_api_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "should-not-leak")
    env = environment(CONFIG)
    assert set(env) == {
        "PATH",
        "HOME",
        "LANG",
        "DISABLE_UPDATES",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
        "CLAUDE_CONFIG_DIR",
    }
    with_token = environment(
        ClaudeCliConfig("claude", "opus", 600, "/home/app", oauth_token="oat-token")
    )
    assert with_token["CLAUDE_CODE_OAUTH_TOKEN"] == "oat-token"
    empty_token = environment(ClaudeCliConfig("claude", "opus", 600, "/home/app", oauth_token=""))
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in empty_token


def test_schema_keeps_title_fields_and_pins_the_subject() -> None:
    schema = lesson_schema(ART)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert "title" in properties and "title" in schema["required"]  # type: ignore[operator]
    assert properties["subject"] == {"type": "string", "enum": ["art"]}
    assert "$defs" not in json.dumps(schema) and "$ref" not in json.dumps(schema)
    go_deeper = json.dumps(properties["go_deeper"])
    assert '"title"' in go_deeper and '"description"' in go_deeper

    topic = LessonBrief(
        kind="topic", local_date=date(2026, 11, 24), length="short", subject=None, topic="tides"
    )
    topic_subjects = lesson_schema(topic)["properties"]
    assert isinstance(topic_subjects, dict)
    assert len(topic_subjects["subject"]["enum"]) == 11


def test_prompts_fence_owner_text_and_include_the_parent_lesson() -> None:
    topic = LessonBrief(
        kind="topic",
        local_date=date(2026, 11, 24),
        length="short",
        subject=None,
        topic="why the sky is blue",
    )
    prompt = build_prompt(topic)
    assert "<reader_request>\nwhy the sky is blue\n</reader_request>" in prompt
    assert "1,000–1,300 words" in prompt
    assert "- science: Science" in prompt

    follow_up = LessonBrief(
        kind="follow_up",
        local_date=date(2026, 11, 24),
        length="standard",
        subject="art",
        parent=ParentLesson(
            title="Fog on Paper",
            subject="art",
            body_markdown="## Ink\nThe pines lean out of the haze.",
            key_ideas=("Blank paper reads as fog.",),
        ),
        direction=Direction(title="The Draft Question", description="Was it ever finished?"),
    )
    prompt = build_prompt(follow_up)
    assert "<earlier_lesson>\n## Ink\nThe pines lean out of the haze.\n</earlier_lesson>" in prompt
    assert "The Draft Question: Was it ever finished?" in prompt
    assert "2,300–3,200 words" in prompt


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (fixture("not_logged_in.json"), "claude_auth"),
        (
            json.dumps({"is_error": True, "result": "Failed to authenticate", "usage": {}}),
            "claude_auth",
        ),
        (json.dumps({"is_error": True, "api_error_status": 401}), "claude_auth"),
        (
            json.dumps({"is_error": True, "result": "You've hit your session limit · resets 3pm"}),
            "claude_usage_limit",
        ),
        (
            json.dumps({"is_error": True, "result": "You've hit your weekly limit · resets Mon"}),
            "claude_usage_limit",
        ),
        (json.dumps({"is_error": True, "api_error_status": 429}), "claude_usage_limit"),
        (json.dumps({"is_error": True, "result": "API Error: 500 overloaded"}), "claude_error"),
        (json.dumps({"subtype": "error_max_turns", "is_error": True}), "invalid_output"),
        (json.dumps({"subtype": "success", "result": "I could not comply"}), "invalid_output"),
        (json.dumps({"structured_output": {"subject": "art"}}), "invalid_output"),
        ("not json at all", "claude_error"),
    ],
)
def test_failures_map_to_job_error_codes(payload: str, code: str) -> None:
    returncode = 1 if '"is_error": true' in payload.lower() else 0
    result = CliResult(returncode, payload, "", False, 5)
    with pytest.raises(GenerationError) as raised:
        parse_result(result, ART)
    assert raised.value.code == code


def test_timeout_and_subject_drift_are_reported() -> None:
    with pytest.raises(GenerationError) as raised:
        parse_result(CliResult(None, "", "", True, 600_000), ART)
    assert raised.value.code == "claude_timeout"

    history = LessonBrief(
        kind="subject", local_date=date(2026, 11, 24), length="standard", subject="history"
    )
    with pytest.raises(GenerationError) as raised:
        parse_result(ok(fixture("success.json")), history)
    assert raised.value.code == "invalid_output"
    assert raised.value.usage.model == "claude-opus-5-5"


def _script(tmp_path: Path, body: str) -> str:
    path = tmp_path / "fake-claude"
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


def test_runner_uses_an_empty_directory_and_exactly_the_given_environment(
    tmp_path: Path,
) -> None:
    executable = _script(
        tmp_path,
        "import json, os, sys\n"
        "print(json.dumps({'cwd_files': os.listdir('.'), 'env': sorted(os.environ),"
        " 'stdin': sys.stdin.read()}))\n",
    )
    result = SubprocessCliRunner().run([executable], "the prompt", {"HOME": "/x"}, timeout=10)
    seen = json.loads(result.stdout)
    assert result.returncode == 0 and not result.timed_out
    assert seen["cwd_files"] == []
    assert seen["stdin"] == "the prompt"
    assert set(seen["env"]) <= {"HOME", "LC_CTYPE", "__CF_USER_TEXT_ENCODING"}


def test_runner_stops_the_process_group_on_timeout(tmp_path: Path) -> None:
    executable = _script(tmp_path, "import time\ntime.sleep(30)\n")
    result = SubprocessCliRunner().run([executable], "", {}, timeout=0.2)
    assert result.timed_out
    assert result.duration_ms < 10_000


def test_runner_reports_a_missing_executable(tmp_path: Path) -> None:
    result = SubprocessCliRunner().run([str(tmp_path / "missing")], "", {}, timeout=1)
    assert result.returncode is None and result.stderr
    with pytest.raises(GenerationError) as raised:
        parse_result(result, ART)
    assert raised.value.code == "claude_error"


def test_login_probe_reads_auth_status() -> None:
    signed_out = RecordingRunner(
        ok(json.dumps({"loggedIn": False, "authMethod": "none", "loginExpiresAt": None}))
    )
    status = ClaudeCliLogin(CONFIG, signed_out).status()
    assert status is not None and not status.logged_in
    assert signed_out.calls[0][0] == ["/usr/local/bin/claude", "auth", "status"]

    signed_in = RecordingRunner(
        CliResult(0, '{"loggedIn": true, "loginExpiresAt": "2026-12-22T20:14:18Z"}', "", False, 1)
    )
    status = ClaudeCliLogin(CONFIG, signed_in).status()
    assert status is not None and status.logged_in
    assert status.expires_at == datetime(2026, 12, 22, 20, 14, 18, tzinfo=UTC)

    assert ClaudeCliLogin(CONFIG, RecordingRunner(CliResult(1, "", "", True, 1))).status() is None
    assert ClaudeCliLogin(CONFIG, RecordingRunner(ok("garbage"))).status() is None
