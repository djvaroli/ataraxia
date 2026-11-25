"""Request and response models: the HTTP contract the frontend types are generated from.

Times are timezone-aware UTC; `local_date` fields are `YYYY-MM-DD` in the owner's
time zone. Lesson content parts are reused from the domain so the stored shape and
the served shape cannot drift.
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

from ataraxia.domain.jobs import JobErrorCode, JobKind, JobStatus
from ataraxia.domain.lessons import (
    Direction,
    FurtherItem,
    GlossaryEntry,
    Illustration,
    LessonLength,
)
from ataraxia.domain.subjects import SubjectId

AuthMode = Literal["firebase", "local"]
Rating = Literal[-1, 0, 1]
ClientEventType = Literal["app.opened"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Errors


class FieldError(_Model):
    field: str
    message: str


class ErrorDetail(_Model):
    code: Literal[
        "unauthenticated",
        "forbidden",
        "not_found",
        "validation_failed",
        "conflict",
        "daily_limit",
        "too_many_waiting",
        "unavailable",
    ]
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


class Preferences(_Model):
    time_zone: str
    time_zone_confirmed: bool = Field(
        description="False until the owner or the browser has set the time zone."
    )
    subjects: list[SubjectId] = Field(description="Enabled subjects, in catalog order.")
    lesson_length: LessonLength
    morning_lesson: bool
    morning_hour: Annotated[int, Field(ge=0, le=23)]


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


# Lessons


class LessonState(_Model):
    saved: bool
    saved_at: datetime | None
    rating: Rating
    first_opened_at: datetime | None
    finished_at: datetime | None
    read_seconds: int
    furthest_scroll: Annotated[float, Field(ge=0, le=1)]
    flagged: bool


class ThreadEntry(_Model):
    id: str
    title: str
    part: int = Field(description="1 for the first lesson, 2 for its follow-ups, and so on.")
    parent_id: str | None


class LessonSummary(_Model):
    id: str
    created_at: datetime
    local_date: date
    subject: SubjectId
    origin: JobKind
    title: str
    hook: str
    reading_minutes: int
    tags: list[str]
    cover: Illustration | None = Field(description="First illustration, if any.")
    parent_id: str | None
    thread_root_id: str
    part: int
    state: LessonState


class Lesson(LessonSummary):
    request_text: str | None = Field(description="The owner's topic or question, if any.")
    body_markdown: str
    key_ideas: list[str]
    glossary: list[GlossaryEntry]
    go_deeper: list[Direction]
    further: list[FurtherItem]
    illustrations: list[Illustration]
    thread: list[ThreadEntry] = Field(
        description="Every lesson in this thread, oldest first, including this one."
    )


class LessonPage(_Model):
    items: list[LessonSummary]
    next_cursor: str | None


# Jobs and requests


class Job(_Model):
    id: str
    kind: JobKind
    status: JobStatus
    local_date: date
    subject: SubjectId | None
    request_text: str | None
    parent_lesson_id: str | None
    attempts: int
    error_code: JobErrorCode | None
    error_message: str | None = Field(description="Plain-language explanation of a failure.")
    lesson_id: str | None
    can_retry: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


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


# Today


class Allowance(_Model):
    used: int
    limit: int
    remaining: int
    waiting: int = Field(description="Jobs currently queued or running.")
    waiting_limit: int


class WorkerStatus(_Model):
    online: bool = Field(description="A heartbeat arrived in the last 30 seconds.")
    heartbeat_at: datetime | None
    login_expires_at: datetime | None = Field(
        description="When the worker's Claude login ends, if the CLI reported it."
    )


class DailySlot(_Model):
    """Today's daily lesson. `waiting` means the morning hour has not arrived yet;
    `not_scheduled` means the morning lesson is off and none was requested."""

    status: Literal["not_scheduled", "waiting", "queued", "running", "ready", "failed"]
    lesson: LessonSummary | None
    job: Job | None
    morning_hour: int | None


class Today(_Model):
    local_date: date
    daily: DailySlot
    jobs: list[Job] = Field(
        description="Today's other jobs that are queued, running, or failed, newest first."
    )
    unfinished: list[LessonSummary] = Field(
        description="Opened but unfinished lessons from the last 14 days, newest first, max 5."
    )
    allowance: Allowance
    worker: WorkerStatus


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
    """One reading interval, sent when the reader is left or hidden."""

    seconds: Annotated[int, Field(ge=1, le=1800)]
    scroll: Annotated[float, Field(ge=0, le=1)]


class ClientEvent(_Model):
    type: ClientEventType


# Progress and activity


class SubjectProgress(_Model):
    subject: SubjectId
    lessons: int
    finished: int
    read_minutes: int
    liked: int
    disliked: int
    last_finished_on: date | None


class DayActivity(_Model):
    date: date
    finished: int
    read_minutes: int


class Progress(_Model):
    current_streak: int = Field(
        description="Consecutive days with a finished lesson, ending today or yesterday."
    )
    longest_streak: int
    lessons_total: int
    finished_total: int
    saved_total: int
    read_minutes_total: int
    subjects: list[SubjectProgress] = Field(description="Every catalog subject, catalog order.")
    days: list[DayActivity] = Field(description="The last 84 local days, oldest first.")


class ActivityEvent(_Model):
    id: int
    occurred_at: datetime
    local_date: date
    type: str
    lesson_id: str | None
    subject: SubjectId | None
    data: dict[str, JsonValue]


class ActivityPage(_Model):
    items: list[ActivityEvent]
    next_cursor: str | None


class GenerationCall(_Model):
    id: str
    job_id: str
    local_date: date
    started_at: datetime
    finished_at: datetime | None
    outcome: str | None
    model: str | None
    duration_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None


class ExportDocument(_Model):
    """Everything durable, for analysis and backup. `schema_version` is the database's."""

    schema_version: int
    exported_at: datetime
    preferences: Preferences
    lessons: list[Lesson]
    jobs: list[Job]
    calls: list[GenerationCall]
    events: list[ActivityEvent]
