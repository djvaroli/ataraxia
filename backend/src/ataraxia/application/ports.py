"""Boundaries between use cases and the outside world.

The worker hands a `LessonBrief` to a `LessonGenerator` and gets validated content
back or a `GenerationError` with a job error code. Implementations: the Claude CLI
adapter and a deterministic fake. The API turns a bearer token into a user ID with an
`IdentityVerifier`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol

from ataraxia.domain.jobs import JobErrorCode, JobKind
from ataraxia.domain.lessons import (
    Direction,
    Illustration,
    IllustrationRequest,
    LessonContent,
    LessonLength,
)
from ataraxia.domain.subjects import SubjectId


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, timezone-aware UTC."""
        ...


class InvalidTokenError(Exception):
    """The token is missing, malformed, expired, or not signed by the issuer."""


class IdentityUnavailableError(Exception):
    """The token could not be checked now, for example the signing keys are unreachable."""


class IdentityVerifier(Protocol):
    def verify(self, token: str | None) -> str:
        """Return the verified user ID for a bearer token.

        Raises `InvalidTokenError` or `IdentityUnavailableError`. The caller checks
        whether the user is the owner.
        """
        ...


@dataclass(frozen=True)
class ParentLesson:
    """The lesson a follow-up continues from."""

    title: str
    subject: SubjectId
    body_markdown: str
    key_ideas: Sequence[str]


@dataclass(frozen=True)
class LessonBrief:
    """Everything the writer needs for one lesson; nothing else personal is sent.

    `subject` is None only for a topic request, where the writer picks a subject.
    A follow-up has `parent` and exactly one of `direction` or `question`.
    """

    kind: JobKind
    local_date: date
    length: LessonLength
    subject: SubjectId | None
    topic: str | None = None
    parent: ParentLesson | None = None
    direction: Direction | None = None
    question: str | None = None
    recent_titles_in_subject: Sequence[str] = field(default_factory=tuple)
    recent_titles: Sequence[str] = field(default_factory=tuple)
    liked_titles: Sequence[str] = field(default_factory=tuple)
    disliked_titles: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class GenerationUsage:
    """What one generator call reported; every field may be missing."""

    model: str | None = None
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    login_expires_at: datetime | None = None


@dataclass(frozen=True)
class GeneratedLesson:
    content: LessonContent
    usage: GenerationUsage
    prompt_version: str


class GenerationError(Exception):
    """A failed call. `code` decides whether the job retries (see domain.jobs)."""

    def __init__(
        self, code: JobErrorCode, message: str, usage: GenerationUsage | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.usage = usage or GenerationUsage()


class LessonGenerator(Protocol):
    def generate(self, brief: LessonBrief) -> GeneratedLesson:
        """Write one lesson. Raises `GenerationError`; never returns invalid content.

        For non-topic briefs the content's subject equals `brief.subject`.
        """
        ...


class IllustrationResolver(Protocol):
    def resolve(self, requests: Sequence[IllustrationRequest]) -> list[Illustration]:
        """Look up images for the requested articles, in order, dropping any that fail.

        Never raises; bounded to a few seconds in total.
        """
        ...


@dataclass(frozen=True)
class LoginStatus:
    """Whether the generator's account is signed in, and until when if known."""

    logged_in: bool
    expires_at: datetime | None = None


class LoginProbe(Protocol):
    def status(self) -> LoginStatus | None:
        """Check the login without generating anything; None when it cannot tell."""
        ...
