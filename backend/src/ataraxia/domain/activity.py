"""The activity record: event types and a new event before it is stored."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from pydantic import JsonValue

from ataraxia.domain.subjects import SubjectId

EventType = Literal[
    "app.opened",
    "lesson.requested",
    "lesson.prepared",
    "lesson.failed",
    "lesson.opened",
    "lesson.finished",
    "lesson.unfinished",
    "lesson.saved",
    "lesson.unsaved",
    "lesson.rated",
    "lesson.flagged",
    "settings.updated",
]


@dataclass(frozen=True)
class NewEvent:
    """One append-only record, written in the same transaction as the change it records.

    `data` holds IDs, codes, and small values; the only free text is the owner's own
    topic requests, questions, and flag notes.
    """

    type: EventType
    occurred_at: datetime
    local_date: date
    lesson_id: str | None = None
    subject: SubjectId | None = None
    data: Mapping[str, JsonValue] = field(default_factory=dict)
