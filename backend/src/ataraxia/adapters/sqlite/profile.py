"""The single settings row."""

from pydantic import TypeAdapter

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.rows import insert_event, timestamp, to_json
from ataraxia.domain.activity import NewEvent
from ataraxia.domain.preferences import Preferences
from ataraxia.domain.subjects import SubjectId

_SUBJECTS = TypeAdapter(list[SubjectId])


class ProfileRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self) -> Preferences | None:
        """The saved settings, or None before the owner first changes anything."""
        with self._database.connect() as connection:
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

    def save(self, preferences: Preferences, event: NewEvent) -> None:
        """Store the settings and the event recording the change together."""
        now = timestamp(event.occurred_at)
        with self._database.transaction() as connection:
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
