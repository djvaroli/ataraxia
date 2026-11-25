"""Records passed between use cases and storage that the API never serves."""

from dataclasses import dataclass
from datetime import date, datetime

from ataraxia.domain.jobs import JobKind
from ataraxia.domain.lessons import Direction, Illustration, LessonContent
from ataraxia.domain.subjects import SubjectId


@dataclass(frozen=True)
class NewJob:
    """A job to insert. A follow-up has `parent_lesson_id` and either a direction index
    (with its title as `request_text`) or the owner's question as `request_text`."""

    id: str
    kind: JobKind
    local_date: date
    created_at: datetime
    subject: SubjectId | None = None
    request_text: str | None = None
    parent_lesson_id: str | None = None
    direction_index: int | None = None


@dataclass(frozen=True)
class DailyCap:
    """The day the cap applies to and how many counted calls it allows."""

    local_date: date
    limit: int


@dataclass(frozen=True)
class Usage:
    """Today's counted calls and the jobs that have not finished yet."""

    used: int
    queued: int
    running: int


@dataclass(frozen=True)
class PendingJob:
    """A queued job the worker is about to attempt."""

    id: str
    kind: JobKind
    subject: SubjectId | None
    request_text: str | None
    parent_lesson_id: str | None
    direction_index: int | None
    attempts: int
    queued_at: datetime


@dataclass(frozen=True)
class ParentRecord:
    """What a follow-up needs from the lesson it continues."""

    id: str
    title: str
    subject: SubjectId
    body_markdown: str
    key_ideas: list[str]
    go_deeper: list[Direction]
    thread_root_id: str
    part: int


@dataclass(frozen=True)
class Publication:
    """A prepared lesson ready to store with its job's result."""

    lesson_id: str
    job: PendingJob
    call_id: str
    content: LessonContent
    illustrations: list[Illustration]
    local_date: date
    created_at: datetime
    model: str | None
    prompt_version: str
    parent: ParentRecord | None


@dataclass(frozen=True)
class SubjectTotals:
    """Per-subject counts over every stored lesson."""

    subject: SubjectId
    lessons: int
    finished: int
    saved: int
    read_seconds: int
    liked: int
    disliked: int
    last_finished_on: date | None
