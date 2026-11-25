"""The single settings row."""

import sqlite3
from collections.abc import Callable
from datetime import datetime

from pydantic import TypeAdapter

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.rows import insert_event, timestamp, to_json
from ataraxia.domain.activity import NewEvent
from ataraxia.domain.preferences import Preferences
from ataraxia.domain.subjects import SubjectId

_SUBJECTS = TypeAdapter(list[SubjectId])

Change = tuple[Preferences, NewEvent]
"""New settings and the `settings.updated` event recording them."""


class ProfileRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self) -> Preferences | None:
        """The saved settings, or None before the owner first changes anything."""
        with self._database.connect() as connection:
            return _read(connection)

    def updated_at(self) -> datetime | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT updated_at FROM profile WHERE id = 1").fetchone()
        return None if row is None else datetime.fromisoformat(row["updated_at"])

    def update(
        self, defaults: Preferences, change: Callable[[Preferences], Change | None]
    ) -> Preferences:
        """Read, change, and store the settings in one write transaction, so two
        concurrent updates cannot overwrite each other. `change` returns None when
        nothing changes; then nothing is written."""
        with self._database.transaction() as connection:
            current = _read(connection) or defaults
            result = change(current)
            if result is None:
                return current
            preferences, event = result
            _write(connection, preferences, event)
            return preferences


def _write(connection: sqlite3.Connection, preferences: Preferences, event: NewEvent) -> None:
    now = timestamp(event.occurred_at)
    connection.execute(
        """
        INSERT INTO profile (
            id, time_zone, time_zone_confirmed, subjects, lesson_length,
            morning_lesson, morning_hour, created_at, updated_at
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            time_zone = excluded.time_zone,
            time_zone_confirmed = excluded.time_zone_confirmed,
            subjects = excluded.subjects,
            lesson_length = excluded.lesson_length,
            morning_lesson = excluded.morning_lesson,
            morning_hour = excluded.morning_hour,
            updated_at = excluded.updated_at
        """,
        (
            preferences.time_zone,
            int(preferences.time_zone_confirmed),
            to_json(list(preferences.subjects)),
            preferences.lesson_length,
            int(preferences.morning_lesson),
            preferences.morning_hour,
            now,
            now,
        ),
    )
    insert_event(connection, event)


def _read(connection: sqlite3.Connection) -> Preferences | None:
    row = connection.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    if row is None:
        return None
    return Preferences(
        time_zone=row["time_zone"],
        time_zone_confirmed=bool(row["time_zone_confirmed"]),
        subjects=_SUBJECTS.validate_json(row["subjects"]),
        lesson_length=row["lesson_length"],
        morning_lesson=bool(row["morning_lesson"]),
        morning_hour=row["morning_hour"],
    )
