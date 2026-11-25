"""Request bodies, errors, and API-only responses.

Read models shared with the tools live in `ataraxia.application.views`; together
they are the HTTP contract the frontend types are generated from.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ataraxia.application.views import Rating
from ataraxia.domain.lessons import LessonLength
from ataraxia.domain.preferences import Preferences
from ataraxia.domain.subjects import SubjectId

AuthMode = Literal["firebase", "local"]
ClientEventType = Literal["app.opened"]
ErrorCode = Literal[
    "unauthenticated",
    "forbidden",
    "not_found",
    "validation_failed",
    "conflict",
    "daily_limit",
    "too_many_waiting",
    "unavailable",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Errors


class FieldError(_Model):
    field: str
    message: str


class ErrorDetail(_Model):
    code: ErrorCode
    message: str
    fields: list[FieldError] = []


class ErrorBody(_Model):
    """Every 4xx/5xx application error has this shape."""

    error: ErrorDetail


# Configuration and preferences


class FirebaseWebConfig(_Model):
    """Public Firebase web app configuration; not a secret."""

    api_key: str
    auth_domain: str
    project_id: str
    app_id: str


class ClientConfig(_Model):
    auth_mode: AuthMode
    firebase: FirebaseWebConfig | None


class SubjectInfo(_Model):
    id: SubjectId
    label: str
    description: str


class PreferencesUpdate(_Model):
    """Fields left out stay unchanged. The time zone must be an IANA name."""

    time_zone: Annotated[str, StringConstraints(min_length=1, max_length=64)] | None = None
    subjects: Annotated[list[SubjectId], Field(min_length=1, max_length=20)] | None = None
    lesson_length: LessonLength | None = None
    morning_lesson: bool | None = None
    morning_hour: Annotated[int, Field(ge=0, le=23)] | None = None


class Me(_Model):
    auth_mode: AuthMode
    preferences: Preferences
    catalog: list[SubjectInfo]
    lessons_per_day: int


# Lesson requests


class SurpriseRequest(_Model):
    kind: Literal["surprise"]


class SubjectRequest(_Model):
    kind: Literal["subject"]
    subject: SubjectId


class TopicRequest(_Model):
    kind: Literal["topic"]
    topic: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=300)]


LessonRequest = Annotated[
    SurpriseRequest | SubjectRequest | TopicRequest, Field(discriminator="kind")
]


class FollowUpRequest(_Model):
    """Exactly one of a suggested direction (by index into `go_deeper`) or a question."""

    direction: Annotated[int, Field(ge=0, le=2)] | None = None
    question: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]
        | None
    ) = None


# Reading and state changes


class SavedUpdate(_Model):
    saved: bool


class RatingUpdate(_Model):
    rating: Rating


class FinishedUpdate(_Model):
    finished: bool


class FlagUpdate(_Model):
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class ReadingReport(_Model):
    """Cumulative totals for one reader visit, sent every 30 s while visible and on hide.

    The server keeps the largest values seen per session, so repeats and late
    arrivals are harmless.
    """

    session_id: Annotated[str, StringConstraints(pattern=r"^[0-9a-f-]{36}$")]
    seconds: Annotated[int, Field(ge=0, le=14400)]
    scroll: Annotated[float, Field(ge=0, le=1)]


class ClientEvent(_Model):
    type: ClientEventType
