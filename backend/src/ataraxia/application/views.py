"""Read models returned by the use cases and served by the API as JSON.

Times are timezone-aware UTC; `local_date` fields are `YYYY-MM-DD` in the owner's
time zone. Lesson content parts are reused from the domain so the stored shape and
the served shape cannot drift.
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ataraxia.domain.jobs import JobErrorCode, JobKind, JobStatus
from ataraxia.domain.lessons import Direction, FurtherItem, GlossaryEntry, Illustration
from ataraxia.domain.preferences import Preferences
from ataraxia.domain.subjects import SubjectId

Rating = Literal[-1, 0, 1]
DailySlotStatus = Literal["not_scheduled", "waiting", "queued", "running", "ready", "failed"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


# Jobs


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
    next_attempt_at: datetime | None = Field(
        description="When a queued job will next be tried, e.g. after a usage limit."
    )
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


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
    claude_logged_in: bool | None = Field(
        description="Whether the worker's Claude login works; null until first checked."
    )


class DailySlot(_Model):
    """Today's daily lesson. `waiting` means the morning hour has not arrived yet;
    `not_scheduled` means the morning lesson is off and none was requested."""

    status: DailySlotStatus
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


class ReadingSession(_Model):
    id: str
    lesson_id: str
    started_at: datetime
    updated_at: datetime
    local_date: date
    seconds: int
    furthest_scroll: float


class ExportedLesson(Lesson):
    """A lesson with every stored field, including those the reader does not need."""

    model: str | None
    prompt_version: str
    rated_at: datetime | None
    finished_on: date | None = Field(description="Local date the lesson was finished.")
    flagged_at: datetime | None
    flag_note: str | None


class ExportedJob(Job):
    """A job with every stored field."""

    direction_index: int | None = Field(description="Chosen go-deeper direction, if any.")
    queued_at: datetime = Field(description="When the job was requested or last retried.")


class ExportDocument(_Model):
    """Everything durable, for analysis and backup. `schema_version` is the database's."""

    schema_version: int
    exported_at: datetime
    preferences: Preferences
    preferences_updated_at: datetime | None = Field(
        description="When the owner last changed settings; null while on defaults."
    )
    lessons: list[ExportedLesson]
    jobs: list[ExportedJob]
    calls: list[GenerationCall]
    events: list[ActivityEvent]
    reading_sessions: list[ReadingSession]
