"""Conversions between SQLite values and application types.

Timestamps are stored as UTC ISO 8601 with microseconds so that text order is time
order; dates as `YYYY-MM-DD`; lists and objects as JSON text.
"""

import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import get_args

from pydantic import BaseModel, JsonValue, TypeAdapter

from ataraxia.application.views import (
    ActivityEvent,
    GenerationCall,
    Job,
    LessonState,
    LessonSummary,
    Rating,
    ReadingSession,
)
from ataraxia.domain.activity import NewEvent
from ataraxia.domain.jobs import (
    ERROR_MESSAGES,
    JOB_ERROR_CODES,
    JOB_KINDS,
    JOB_STATUSES,
    JobErrorCode,
    JobKind,
    JobStatus,
)
from ataraxia.domain.lessons import Illustration
from ataraxia.domain.subjects import SUBJECT_IDS, SubjectId

_ILLUSTRATIONS = TypeAdapter(list[Illustration])
_STRINGS = TypeAdapter(list[str])
_OBJECT = TypeAdapter(dict[str, JsonValue])
_RATINGS: tuple[Rating, ...] = get_args(Rating)


def timestamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="microseconds")


def optional_timestamp(moment: datetime | None) -> str | None:
    return None if moment is None else timestamp(moment)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def parse_optional_timestamp(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def to_json(value: JsonValue) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def models_json(items: Sequence[BaseModel]) -> str:
    return to_json([item.model_dump(mode="json") for item in items])


def strings(value: str) -> list[str]:
    return _STRINGS.validate_json(value)


def illustrations(value: str) -> list[Illustration]:
    return _ILLUSTRATIONS.validate_json(value)


def _literal[T: str](value: str, options: tuple[T, ...]) -> T:
    for known in options:
        if known == value:
            return known
    raise ValueError(f"Unexpected value in storage: {value!r}")


def subject_id(value: str) -> SubjectId:
    return _literal(value, SUBJECT_IDS)


def optional_subject_id(value: str | None) -> SubjectId | None:
    return None if value is None else subject_id(value)


def job_kind(value: str) -> JobKind:
    return _literal(value, JOB_KINDS)


def job_status(value: str) -> JobStatus:
    return _literal(value, JOB_STATUSES)


def error_code(value: str | None) -> JobErrorCode | None:
    return None if value is None else _literal(value, JOB_ERROR_CODES)


def rating(value: int) -> Rating:
    for known in _RATINGS:
        if known == value:
            return known
    raise ValueError(f"Unexpected rating in storage: {value!r}")


# Column lists shared by queries that build lesson summaries.
SUMMARY_COLUMNS = """
    l.id, l.created_at, l.local_date, l.subject, l.origin, l.title, l.hook,
    l.reading_minutes, l.tags, l.illustrations, l.parent_id, l.thread_root_id, l.part,
    s.saved, s.saved_at, s.rating, s.first_opened_at, s.finished_at, s.read_seconds,
    s.furthest_scroll, s.flagged_at
"""
LESSON_COLUMNS = (
    SUMMARY_COLUMNS
    + """,
    l.request_text, l.body_markdown, l.key_ideas, l.glossary, l.go_deeper, l.further
"""
)
LESSONS_WITH_STATE = "lessons AS l JOIN lesson_state AS s ON s.lesson_id = l.id"


def lesson_state(row: sqlite3.Row) -> LessonState:
    return LessonState(
        saved=bool(row["saved"]),
        saved_at=parse_optional_timestamp(row["saved_at"]),
        rating=rating(row["rating"]),
        first_opened_at=parse_optional_timestamp(row["first_opened_at"]),
        finished_at=parse_optional_timestamp(row["finished_at"]),
        read_seconds=row["read_seconds"],
        furthest_scroll=row["furthest_scroll"],
        flagged=row["flagged_at"] is not None,
    )


def lesson_summary(row: sqlite3.Row) -> LessonSummary:
    images = illustrations(row["illustrations"])
    return LessonSummary(
        id=row["id"],
        created_at=parse_timestamp(row["created_at"]),
        local_date=date.fromisoformat(row["local_date"]),
        subject=subject_id(row["subject"]),
        origin=job_kind(row["origin"]),
        title=row["title"],
        hook=row["hook"],
        reading_minutes=row["reading_minutes"],
        tags=strings(row["tags"]),
        cover=images[0] if images else None,
        parent_id=row["parent_id"],
        thread_root_id=row["thread_root_id"],
        part=row["part"],
        state=lesson_state(row),
    )


def job(row: sqlite3.Row) -> Job:
    code = error_code(row["error_code"])
    status = job_status(row["status"])
    return Job(
        id=row["id"],
        kind=job_kind(row["kind"]),
        status=status,
        local_date=date.fromisoformat(row["local_date"]),
        subject=optional_subject_id(row["subject"]),
        request_text=row["request_text"],
        parent_lesson_id=row["parent_lesson_id"],
        attempts=row["attempts"],
        error_code=code,
        error_message=None if code is None else ERROR_MESSAGES[code],
        lesson_id=row["lesson_id"],
        can_retry=status == "failed",
        next_attempt_at=(
            parse_optional_timestamp(row["next_attempt_at"]) if status == "queued" else None
        ),
        created_at=parse_timestamp(row["created_at"]),
        started_at=parse_optional_timestamp(row["started_at"]),
        finished_at=parse_optional_timestamp(row["finished_at"]),
    )


def generation_call(row: sqlite3.Row) -> GenerationCall:
    return GenerationCall(
        id=row["id"],
        job_id=row["job_id"],
        local_date=date.fromisoformat(row["local_date"]),
        started_at=parse_timestamp(row["started_at"]),
        finished_at=parse_optional_timestamp(row["finished_at"]),
        outcome=row["outcome"],
        model=row["model"],
        duration_ms=row["duration_ms"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        cost_usd=row["cost_usd"],
    )


def reading_session(row: sqlite3.Row) -> ReadingSession:
    return ReadingSession(
        id=row["id"],
        lesson_id=row["lesson_id"],
        started_at=parse_timestamp(row["started_at"]),
        updated_at=parse_timestamp(row["updated_at"]),
        local_date=date.fromisoformat(row["local_date"]),
        seconds=row["seconds"],
        furthest_scroll=row["furthest_scroll"],
    )


def activity_event(row: sqlite3.Row) -> ActivityEvent:
    return ActivityEvent(
        id=row["id"],
        occurred_at=parse_timestamp(row["occurred_at"]),
        local_date=date.fromisoformat(row["local_date"]),
        type=row["type"],
        lesson_id=row["lesson_id"],
        subject=optional_subject_id(row["subject"]),
        data=_OBJECT.validate_json(row["data"]),
    )


def insert_event(connection: sqlite3.Connection, event: NewEvent) -> None:
    """Append to the activity record inside the caller's transaction."""
    connection.execute(
        """
        INSERT INTO activity_events (occurred_at, local_date, type, lesson_id, subject, data)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp(event.occurred_at),
            event.local_date.isoformat(),
            event.type,
            event.lesson_id,
            event.subject,
            to_json(dict(event.data)),
        ),
    )


def placeholders(values: Sequence[object]) -> str:
    return ", ".join("?" for _ in values)
