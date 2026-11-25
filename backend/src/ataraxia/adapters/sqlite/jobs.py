"""Lesson preparation jobs and the Claude calls made for them.

Limits are checked inside the same immediate transaction as the insert, so two
requests arriving together cannot both pass a nearly full cap.
"""

import sqlite3
from collections.abc import Callable
from datetime import date, datetime

from ataraxia.adapters.sqlite import rows
from ataraxia.adapters.sqlite.database import Database
from ataraxia.application.errors import ConflictError, LimitReachedError, NotFoundError
from ataraxia.application.models import DailyCap, NewJob, PendingJob, Publication, Usage
from ataraxia.application.ports import GenerationUsage
from ataraxia.application.views import GenerationCall, Job
from ataraxia.domain.activity import NewEvent
from ataraxia.domain.jobs import (
    MAX_ATTEMPTS,
    UNCOUNTED_OUTCOMES,
    WAITING_LIMIT,
    FailureDecision,
    JobErrorCode,
    Requeue,
)

_UNCOUNTED = tuple(sorted(UNCOUNTED_OUTCOMES))


class JobRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    # Reading

    def get(self, job_id: str) -> Job | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM generation_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return None if row is None else rows.job(row)

    def daily_job(self, local_date: date) -> Job | None:
        with self._database.connect() as connection:
            row = _daily_row(connection, local_date.isoformat())
        return None if row is None else rows.job(row)

    def jobs_on(self, local_date: date) -> list[Job]:
        """Jobs requested on a local date, newest first."""
        with self._database.connect() as connection:
            found = connection.execute(
                """
                SELECT * FROM generation_jobs WHERE local_date = ?
                ORDER BY created_at DESC, id DESC
                """,
                (local_date.isoformat(),),
            ).fetchall()
        return [rows.job(row) for row in found]

    def usage(self, local_date: date) -> Usage:
        with self._database.connect() as connection:
            return _usage(connection, local_date.isoformat())

    def all_jobs(self) -> list[Job]:
        with self._database.connect() as connection:
            found = connection.execute(
                "SELECT * FROM generation_jobs ORDER BY created_at, id"
            ).fetchall()
        return [rows.job(row) for row in found]

    def all_calls(self) -> list[GenerationCall]:
        with self._database.connect() as connection:
            found = connection.execute(
                "SELECT * FROM generation_calls ORDER BY started_at, id"
            ).fetchall()
        return [rows.generation_call(row) for row in found]

    # Requests from the owner

    def create(self, job: NewJob, event: NewEvent, cap: DailyCap | None) -> Job:
        """Insert a job and its `lesson.requested` event.

        A daily job for a date that already has one returns the existing job and
        writes nothing. With `cap`, raises `LimitReachedError` instead of inserting.
        """
        created = rows.timestamp(job.created_at)
        with self._database.transaction() as connection:
            if job.kind == "daily":
                existing = _daily_row(connection, job.local_date.isoformat())
                if existing is not None:
                    return rows.job(existing)
            if cap is not None:
                _check_limits(connection, cap)
            connection.execute(
                """
                INSERT INTO generation_jobs (
                    id, kind, status, local_date, subject, request_text, parent_lesson_id,
                    direction_index, created_at, queued_at, next_attempt_at
                ) VALUES (?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.kind,
                    job.local_date.isoformat(),
                    job.subject,
                    job.request_text,
                    job.parent_lesson_id,
                    job.direction_index,
                    created,
                    created,
                    created,
                ),
            )
            rows.insert_event(connection, event)
            return _job(connection, job.id)

    def retry(self, job_id: str, event: NewEvent, cap: DailyCap) -> Job:
        """Queue a failed job again with fresh attempts.

        Raises `NotFoundError`, `ConflictError` unless the job failed, or
        `LimitReachedError`.
        """
        now = rows.timestamp(event.occurred_at)
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT status FROM generation_jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError("No such job.")
            if row["status"] != "failed":
                raise ConflictError("Only a failed job can be retried.")
            _check_limits(connection, cap)
            connection.execute(
                """
                UPDATE generation_jobs SET status = 'queued', attempts = 0, error_code = NULL,
                    queued_at = ?, next_attempt_at = ?, started_at = NULL, finished_at = NULL
                WHERE id = ?
                """,
                (now, now, job_id),
            )
            rows.insert_event(connection, event)
            return _job(connection, job_id)

    # The worker

    def recover(self, now: datetime, failed_event: Callable[[str], NewEvent]) -> int:
        """Return jobs left running by a stopped worker to the queue, or fail them when
        no attempt remains. Calls without an outcome are marked interrupted."""
        stamp = rows.timestamp(now)
        with self._database.transaction() as connection:
            running = connection.execute(
                "SELECT id, attempts FROM generation_jobs WHERE status = 'running'"
            ).fetchall()
            connection.execute(
                """
                UPDATE generation_calls SET outcome = 'interrupted', finished_at = ?
                WHERE outcome IS NULL
                """,
                (stamp,),
            )
            for row in running:
                if row["attempts"] < MAX_ATTEMPTS:
                    connection.execute(
                        """
                        UPDATE generation_jobs SET status = 'queued', error_code = 'interrupted',
                            next_attempt_at = ?
                        WHERE id = ?
                        """,
                        (stamp, row["id"]),
                    )
                else:
                    _fail(connection, row["id"], "interrupted", stamp)
                    rows.insert_event(connection, failed_event(row["id"]))
            return len(running)

    def next_ready(self, now: datetime) -> PendingJob | None:
        """The oldest queued job whose next attempt time has passed."""
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM generation_jobs
                WHERE status = 'queued' AND next_attempt_at <= ?
                ORDER BY created_at, id LIMIT 1
                """,
                (rows.timestamp(now),),
            ).fetchone()
        if row is None:
            return None
        return PendingJob(
            id=row["id"],
            kind=rows.job_kind(row["kind"]),
            subject=rows.optional_subject_id(row["subject"]),
            request_text=row["request_text"],
            parent_lesson_id=row["parent_lesson_id"],
            direction_index=row["direction_index"],
            attempts=row["attempts"],
            queued_at=rows.parse_timestamp(row["queued_at"]),
        )

    def start(
        self, job: PendingJob, call_id: str, now: datetime, cap: DailyCap, refused: NewEvent
    ) -> bool:
        """Begin an attempt: check the cap, mark the job running, and record the call.

        Returns False, after failing the job with `daily_limit` and writing `refused`,
        when today's counted calls have reached the cap. No call row is written then.
        """
        stamp = rows.timestamp(now)
        with self._database.transaction() as connection:
            if _usage(connection, cap.local_date.isoformat()).used >= cap.limit:
                _fail(connection, job.id, "daily_limit", stamp)
                rows.insert_event(connection, refused)
                return False
            connection.execute(
                """
                UPDATE generation_jobs SET status = 'running', attempts = attempts + 1,
                    error_code = NULL, started_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (stamp, job.id),
            )
            connection.execute(
                """
                INSERT INTO generation_calls (id, job_id, local_date, started_at)
                VALUES (?, ?, ?, ?)
                """,
                (call_id, job.id, cap.local_date.isoformat(), stamp),
            )
            return True

    def publish(self, publication: Publication, usage: GenerationUsage, event: NewEvent) -> None:
        """Store the lesson, its state, the job's result, the call's usage, and the
        `lesson.prepared` event in one transaction."""
        content = publication.content
        parent = publication.parent
        stamp = rows.timestamp(publication.created_at)
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO lessons (
                    id, created_at, local_date, subject, origin, request_text, parent_id,
                    thread_root_id, part, title, hook, reading_minutes, body_markdown,
                    key_ideas, glossary, go_deeper, further, illustrations, tags, model,
                    prompt_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    publication.lesson_id,
                    stamp,
                    publication.local_date.isoformat(),
                    content.subject,
                    publication.job.kind,
                    publication.job.request_text,
                    None if parent is None else parent.id,
                    publication.lesson_id if parent is None else parent.thread_root_id,
                    1 if parent is None else parent.part + 1,
                    content.title,
                    content.hook,
                    content.reading_minutes,
                    content.body_markdown,
                    rows.to_json(list(content.key_ideas)),
                    rows.models_json(content.glossary),
                    rows.models_json(content.go_deeper),
                    rows.models_json(content.further),
                    rows.models_json(publication.illustrations),
                    rows.to_json(list(content.tags)),
                    publication.model,
                    publication.prompt_version,
                ),
            )
            connection.execute(
                "INSERT INTO lesson_state (lesson_id) VALUES (?)", (publication.lesson_id,)
            )
            connection.execute(
                """
                UPDATE generation_jobs SET status = 'succeeded', lesson_id = ?, subject = ?,
                    error_code = NULL, next_attempt_at = NULL, finished_at = ?
                WHERE id = ?
                """,
                (publication.lesson_id, content.subject, stamp, publication.job.id),
            )
            _finish_call(connection, publication.call_id, "succeeded", usage, stamp)
            rows.insert_event(connection, event)

    def record_failure(
        self,
        job: PendingJob,
        call_id: str,
        code: JobErrorCode,
        usage: GenerationUsage,
        decision: FailureDecision,
        now: datetime,
        failed: NewEvent,
    ) -> None:
        """Record the call's outcome and requeue or fail the job; `failed` is written
        only when the job fails for good."""
        stamp = rows.timestamp(now)
        with self._database.transaction() as connection:
            _finish_call(connection, call_id, code, usage, stamp)
            if isinstance(decision, Requeue):
                connection.execute(
                    """
                    UPDATE generation_jobs SET status = 'queued', error_code = ?,
                        next_attempt_at = ?, attempts = attempts - ?
                    WHERE id = ?
                    """,
                    (code, rows.timestamp(decision.at), int(decision.refund), job.id),
                )
            else:
                _fail(connection, job.id, code, stamp)
                rows.insert_event(connection, failed)


def _job(connection: sqlite3.Connection, job_id: str) -> Job:
    row = connection.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone()
    return rows.job(row)


def _daily_row(connection: sqlite3.Connection, local_date: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = connection.execute(
        "SELECT * FROM generation_jobs WHERE kind = 'daily' AND local_date = ?", (local_date,)
    ).fetchone()
    return row


def _usage(connection: sqlite3.Connection, local_date: str) -> Usage:
    used = connection.execute(
        f"""
        SELECT count(*) FROM generation_calls
        WHERE local_date = ?
            AND (outcome IS NULL OR outcome NOT IN ({rows.placeholders(_UNCOUNTED)}))
        """,
        (local_date, *_UNCOUNTED),
    ).fetchone()[0]
    waiting = connection.execute(
        """
        SELECT sum(status = 'queued') AS queued, sum(status = 'running') AS running
        FROM generation_jobs WHERE status IN ('queued', 'running')
        """
    ).fetchone()
    return Usage(used=used, queued=waiting["queued"] or 0, running=waiting["running"] or 0)


def _check_limits(connection: sqlite3.Connection, cap: DailyCap) -> None:
    """Refuse a new job when today's calls plus the queued jobs (each of which will make
    at least one more call) reach the cap, or when enough jobs are already waiting.
    A running job's call is already counted in `used`."""
    usage = _usage(connection, cap.local_date.isoformat())
    if usage.used + usage.queued >= cap.limit:
        raise LimitReachedError("daily_limit", f"Today's limit of {cap.limit} lessons is reached.")
    if usage.queued + usage.running >= WAITING_LIMIT:
        raise LimitReachedError(
            "too_many_waiting",
            f"{WAITING_LIMIT} lessons are already being prepared. Wait for one to finish.",
        )


def _fail(connection: sqlite3.Connection, job_id: str, code: JobErrorCode, stamp: str) -> None:
    connection.execute(
        """
        UPDATE generation_jobs SET status = 'failed', error_code = ?, next_attempt_at = NULL,
            finished_at = ?
        WHERE id = ?
        """,
        (code, stamp, job_id),
    )


def _finish_call(
    connection: sqlite3.Connection,
    call_id: str,
    outcome: str,
    usage: GenerationUsage,
    stamp: str,
) -> None:
    connection.execute(
        """
        UPDATE generation_calls SET finished_at = ?, outcome = ?, model = ?, duration_ms = ?,
            input_tokens = ?, output_tokens = ?, cost_usd = ?
        WHERE id = ?
        """,
        (
            stamp,
            outcome,
            usage.model,
            usage.duration_ms,
            usage.input_tokens,
            usage.output_tokens,
            usage.cost_usd,
            call_id,
        ),
    )
