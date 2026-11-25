"""Stored lessons, their mutable state, and reading sessions.

Each state change runs in one transaction with its activity event, and writes the
event only when the stored value really changes.
"""

import sqlite3
from collections.abc import Callable, Sequence
from datetime import date, datetime

from pydantic import TypeAdapter

from ataraxia.adapters.sqlite import rows
from ataraxia.adapters.sqlite.database import Database
from ataraxia.application.errors import ConflictError
from ataraxia.application.models import ParentRecord, SubjectTotals
from ataraxia.application.views import (
    Lesson,
    LessonState,
    LessonSummary,
    Rating,
    ReadingSession,
    ThreadEntry,
)
from ataraxia.domain.activity import NewEvent
from ataraxia.domain.lessons import Direction, FurtherItem, GlossaryEntry
from ataraxia.domain.subjects import SubjectId

_GLOSSARY = TypeAdapter(list[GlossaryEntry])
_DIRECTIONS = TypeAdapter(list[Direction])
_FURTHER = TypeAdapter(list[FurtherItem])

Cursor = tuple[datetime, str]
"""Position after a lesson in newest-first order: its (created_at, id)."""


class LessonRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    # Reading lessons

    def subject_of(self, lesson_id: str) -> SubjectId | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT subject FROM lessons WHERE id = ?", (lesson_id,)
            ).fetchone()
        return None if row is None else rows.subject_id(row["subject"])

    def get(self, lesson_id: str) -> Lesson | None:
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {rows.LESSON_COLUMNS} FROM {rows.LESSONS_WITH_STATE} WHERE l.id = ?",
                (lesson_id,),
            ).fetchone()
            if row is None:
                return None
            thread = connection.execute(
                """
                SELECT id, title, part, parent_id FROM lessons
                WHERE thread_root_id = ? ORDER BY created_at, part, id
                """,
                (row["thread_root_id"],),
            ).fetchall()
        return _lesson(row, [_thread_entry(entry) for entry in thread])

    def all_lessons(self) -> list[Lesson]:
        """Every lesson with its thread, oldest first, for export."""
        with self._database.connect() as connection:
            found = connection.execute(
                f"""
                SELECT {rows.LESSON_COLUMNS} FROM {rows.LESSONS_WITH_STATE}
                ORDER BY l.created_at, l.part, l.id
                """
            ).fetchall()
        threads: dict[str, list[ThreadEntry]] = {}
        for row in found:
            threads.setdefault(row["thread_root_id"], []).append(_thread_entry(row))
        return [_lesson(row, threads[row["thread_root_id"]]) for row in found]

    def page(
        self,
        *,
        saved: bool | None,
        subject: SubjectId | None,
        query: str | None,
        after: Cursor | None,
        limit: int,
    ) -> list[LessonSummary]:
        """Summaries newest first; ties on `created_at` are broken by ID."""
        conditions: list[str] = []
        params: list[str | int] = []
        if saved is not None:
            conditions.append("s.saved = ?")
            params.append(int(saved))
        if subject is not None:
            conditions.append("l.subject = ?")
            params.append(subject)
        if query:
            pattern = "%" + _escape_like(query) + "%"
            conditions.append(
                "(l.title LIKE ? ESCAPE '\\' OR l.hook LIKE ? ESCAPE '\\'"
                " OR l.tags LIKE ? ESCAPE '\\')"
            )
            params.extend([pattern, pattern, pattern])
        if after is not None:
            conditions.append("(l.created_at < ? OR (l.created_at = ? AND l.id < ?))")
            created_at = rows.timestamp(after[0])
            params.extend([created_at, created_at, after[1]])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.connect() as connection:
            found = connection.execute(
                f"""
                SELECT {rows.SUMMARY_COLUMNS} FROM {rows.LESSONS_WITH_STATE} {where}
                ORDER BY l.created_at DESC, l.id DESC LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [rows.lesson_summary(row) for row in found]

    def summaries(self, lesson_ids: Sequence[str]) -> dict[str, LessonSummary]:
        if not lesson_ids:
            return {}
        with self._database.connect() as connection:
            found = connection.execute(
                f"""
                SELECT {rows.SUMMARY_COLUMNS} FROM {rows.LESSONS_WITH_STATE}
                WHERE l.id IN ({rows.placeholders(lesson_ids)})
                """,
                tuple(lesson_ids),
            ).fetchall()
        return {row["id"]: rows.lesson_summary(row) for row in found}

    def unfinished(self, opened_since: datetime, limit: int) -> list[LessonSummary]:
        """Opened but unfinished lessons, newest first."""
        with self._database.connect() as connection:
            found = connection.execute(
                f"""
                SELECT {rows.SUMMARY_COLUMNS} FROM {rows.LESSONS_WITH_STATE}
                WHERE s.first_opened_at >= ? AND s.finished_at IS NULL
                ORDER BY l.created_at DESC, l.id DESC LIMIT ?
                """,
                (rows.timestamp(opened_since), limit),
            ).fetchall()
        return [rows.lesson_summary(row) for row in found]

    def state(self, lesson_id: str) -> LessonState | None:
        with self._database.connect() as connection:
            return _state(connection, lesson_id)

    # Changing state

    def set_saved(self, lesson_id: str, saved: bool, event: NewEvent) -> LessonState | None:
        return self._change(
            lesson_id,
            lambda row: bool(row["saved"]) != saved,
            "UPDATE lesson_state SET saved = ?, saved_at = ? WHERE lesson_id = ?",
            (int(saved), rows.timestamp(event.occurred_at) if saved else None),
            event,
        )

    def set_rating(self, lesson_id: str, rating: Rating, event: NewEvent) -> LessonState | None:
        return self._change(
            lesson_id,
            lambda row: row["rating"] != rating,
            "UPDATE lesson_state SET rating = ?, rated_at = ? WHERE lesson_id = ?",
            (rating, rows.timestamp(event.occurred_at)),
            event,
        )

    def set_finished(self, lesson_id: str, finished: bool, event: NewEvent) -> LessonState | None:
        """Finishing records the local date too, which streaks are counted from."""
        values = (
            (rows.timestamp(event.occurred_at), event.local_date.isoformat())
            if finished
            else (None, None)
        )
        return self._change(
            lesson_id,
            lambda row: (row["finished_at"] is not None) != finished,
            "UPDATE lesson_state SET finished_at = ?, finished_on = ? WHERE lesson_id = ?",
            values,
            event,
        )

    def set_flag(self, lesson_id: str, note: str, event: NewEvent) -> LessonState | None:
        return self._change(
            lesson_id,
            lambda row: row["flagged_at"] is None or row["flag_note"] != note,
            "UPDATE lesson_state SET flagged_at = ?, flag_note = ? WHERE lesson_id = ?",
            (rows.timestamp(event.occurred_at), note),
            event,
        )

    def record_open(self, lesson_id: str, event: NewEvent) -> LessonState | None:
        """Every open is recorded; only the first sets `first_opened_at`."""
        with self._database.transaction() as connection:
            if _state(connection, lesson_id) is None:
                return None
            connection.execute(
                """
                UPDATE lesson_state SET first_opened_at = coalesce(first_opened_at, ?)
                WHERE lesson_id = ?
                """,
                (rows.timestamp(event.occurred_at), lesson_id),
            )
            rows.insert_event(connection, event)
            return _state(connection, lesson_id)

    def record_reading(
        self,
        lesson_id: str,
        session_id: str,
        seconds: int,
        scroll: float,
        now: datetime,
        local_date: date,
    ) -> LessonState | None:
        """Keep the largest totals per session; the lesson's totals follow its sessions.

        Raises `ConflictError` when the session belongs to another lesson.
        """
        stamp = rows.timestamp(now)
        with self._database.transaction() as connection:
            if _state(connection, lesson_id) is None:
                return None
            existing = connection.execute(
                "SELECT lesson_id FROM reading_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if existing is not None and existing["lesson_id"] != lesson_id:
                raise ConflictError("This reading session belongs to another lesson.")
            connection.execute(
                """
                INSERT INTO reading_sessions (
                    id, lesson_id, started_at, updated_at, local_date, seconds, furthest_scroll
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    seconds = max(seconds, excluded.seconds),
                    furthest_scroll = max(furthest_scroll, excluded.furthest_scroll)
                """,
                (session_id, lesson_id, stamp, stamp, local_date.isoformat(), seconds, scroll),
            )
            connection.execute(
                """
                UPDATE lesson_state SET
                    read_seconds = (
                        SELECT coalesce(sum(seconds), 0) FROM reading_sessions
                        WHERE lesson_id = :lesson
                    ),
                    furthest_scroll = (
                        SELECT coalesce(max(furthest_scroll), 0) FROM reading_sessions
                        WHERE lesson_id = :lesson
                    )
                WHERE lesson_id = :lesson
                """,
                {"lesson": lesson_id},
            )
            return _state(connection, lesson_id)

    def _change(
        self,
        lesson_id: str,
        changes: Callable[[sqlite3.Row], bool],
        update: str,
        values: tuple[str | int | None, ...],
        event: NewEvent,
    ) -> LessonState | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM lesson_state WHERE lesson_id = ?", (lesson_id,)
            ).fetchone()
            if row is None:
                return None
            if changes(row):
                connection.execute(update, (*values, lesson_id))
                rows.insert_event(connection, event)
            return _state(connection, lesson_id)

    # Inputs for the next lesson's brief

    def recent_subjects(self, limit: int) -> list[SubjectId]:
        """Subjects of the latest lessons, newest first."""
        with self._database.connect() as connection:
            found = connection.execute(
                "SELECT subject FROM lessons ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [rows.subject_id(row["subject"]) for row in found]

    def recent_titles(self, subject: SubjectId | None, limit: int) -> list[str]:
        """Latest titles, newest first, in one subject or across all."""
        with self._database.connect() as connection:
            if subject is None:
                found = connection.execute(
                    "SELECT title FROM lessons ORDER BY created_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                found = connection.execute(
                    """
                    SELECT title FROM lessons WHERE subject = ?
                    ORDER BY created_at DESC, id DESC LIMIT ?
                    """,
                    (subject, limit),
                ).fetchall()
        return [row["title"] for row in found]

    def ratings_since(self, since: datetime) -> list[tuple[SubjectId, int]]:
        """(subject, rating) for lessons rated like or dislike since `since`."""
        with self._database.connect() as connection:
            found = connection.execute(
                f"""
                SELECT l.subject, s.rating FROM {rows.LESSONS_WITH_STATE}
                WHERE s.rating != 0 AND s.rated_at >= ?
                """,
                (rows.timestamp(since),),
            ).fetchall()
        return [(rows.subject_id(row["subject"]), int(row["rating"])) for row in found]

    def rated_titles(self, rating: Rating, since: datetime, limit: int) -> list[str]:
        """Titles rated `rating` since `since`, most recently rated first."""
        with self._database.connect() as connection:
            found = connection.execute(
                f"""
                SELECT l.title FROM {rows.LESSONS_WITH_STATE}
                WHERE s.rating = ? AND s.rated_at >= ?
                ORDER BY s.rated_at DESC LIMIT ?
                """,
                (rating, rows.timestamp(since), limit),
            ).fetchall()
        return [row["title"] for row in found]

    def parent(self, lesson_id: str) -> ParentRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, subject, body_markdown, key_ideas, go_deeper,
                    thread_root_id, part
                FROM lessons WHERE id = ?
                """,
                (lesson_id,),
            ).fetchone()
        if row is None:
            return None
        return ParentRecord(
            id=row["id"],
            title=row["title"],
            subject=rows.subject_id(row["subject"]),
            body_markdown=row["body_markdown"],
            key_ideas=rows.strings(row["key_ideas"]),
            go_deeper=_DIRECTIONS.validate_json(row["go_deeper"]),
            thread_root_id=row["thread_root_id"],
            part=row["part"],
        )

    # Progress

    def finished_dates(self) -> list[date]:
        with self._database.connect() as connection:
            found = connection.execute(
                "SELECT DISTINCT finished_on FROM lesson_state WHERE finished_on IS NOT NULL"
            ).fetchall()
        return [date.fromisoformat(row["finished_on"]) for row in found]

    def subject_totals(self) -> list[SubjectTotals]:
        with self._database.connect() as connection:
            found = connection.execute(
                f"""
                SELECT l.subject, count(*) AS lessons,
                    count(s.finished_at) AS finished,
                    sum(s.saved) AS saved,
                    sum(s.read_seconds) AS read_seconds,
                    sum(s.rating = 1) AS liked,
                    sum(s.rating = -1) AS disliked,
                    max(s.finished_on) AS last_finished_on
                FROM {rows.LESSONS_WITH_STATE} GROUP BY l.subject
                """
            ).fetchall()
        return [
            SubjectTotals(
                subject=rows.subject_id(row["subject"]),
                lessons=row["lessons"],
                finished=row["finished"],
                saved=row["saved"],
                read_seconds=row["read_seconds"],
                liked=row["liked"],
                disliked=row["disliked"],
                last_finished_on=(
                    None
                    if row["last_finished_on"] is None
                    else date.fromisoformat(row["last_finished_on"])
                ),
            )
            for row in found
        ]

    def finished_per_day(self, since: date) -> dict[date, int]:
        with self._database.connect() as connection:
            found = connection.execute(
                """
                SELECT finished_on, count(*) AS finished FROM lesson_state
                WHERE finished_on >= ? GROUP BY finished_on
                """,
                (since.isoformat(),),
            ).fetchall()
        return {date.fromisoformat(row["finished_on"]): row["finished"] for row in found}

    def read_seconds_per_day(self, since: date) -> dict[date, int]:
        with self._database.connect() as connection:
            found = connection.execute(
                """
                SELECT local_date, sum(seconds) AS seconds FROM reading_sessions
                WHERE local_date >= ? GROUP BY local_date
                """,
                (since.isoformat(),),
            ).fetchall()
        return {date.fromisoformat(row["local_date"]): row["seconds"] for row in found}

    def reading_sessions(self) -> list[ReadingSession]:
        with self._database.connect() as connection:
            found = connection.execute(
                "SELECT * FROM reading_sessions ORDER BY started_at, id"
            ).fetchall()
        return [rows.reading_session(row) for row in found]


def _state(connection: sqlite3.Connection, lesson_id: str) -> LessonState | None:
    row = connection.execute(
        "SELECT * FROM lesson_state WHERE lesson_id = ?", (lesson_id,)
    ).fetchone()
    return None if row is None else rows.lesson_state(row)


def _thread_entry(row: sqlite3.Row) -> ThreadEntry:
    return ThreadEntry(
        id=row["id"], title=row["title"], part=row["part"], parent_id=row["parent_id"]
    )


def _lesson(row: sqlite3.Row, thread: list[ThreadEntry]) -> Lesson:
    summary = rows.lesson_summary(row)
    return Lesson(
        **dict(summary),
        request_text=row["request_text"],
        body_markdown=row["body_markdown"],
        key_ideas=rows.strings(row["key_ideas"]),
        glossary=_GLOSSARY.validate_json(row["glossary"]),
        go_deeper=_DIRECTIONS.validate_json(row["go_deeper"]),
        further=_FURTHER.validate_json(row["further"]),
        illustrations=rows.illustrations(row["illustrations"]),
        thread=thread,
    )


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
