"""The worker's single status row: heartbeat, latest error, and Claude login state."""

from dataclasses import dataclass
from datetime import datetime

from ataraxia.adapters.sqlite import rows
from ataraxia.adapters.sqlite.database import Database
from ataraxia.application.ports import GenerationUsage, LoginStatus
from ataraxia.domain.jobs import JobErrorCode


@dataclass(frozen=True)
class WorkerStatusRecord:
    heartbeat_at: datetime | None
    last_error_code: JobErrorCode | None
    last_error_at: datetime | None
    login_expires_at: datetime | None
    logged_in: bool | None = None


class WorkerStatusRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def heartbeat(self, now: datetime) -> None:
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO worker_status (id, heartbeat_at) VALUES (1, ?)
                ON CONFLICT (id) DO UPDATE SET heartbeat_at = excluded.heartbeat_at
                """,
                (rows.timestamp(now),),
            )

    def record_call(
        self, now: datetime, error: JobErrorCode | None, usage: GenerationUsage
    ) -> None:
        """Remember the latest error (if any) and what the call showed about the login."""
        stamp = rows.timestamp(now)
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO worker_status (id, heartbeat_at) VALUES (1, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                (stamp,),
            )
            if error is not None:
                connection.execute(
                    "UPDATE worker_status SET last_error_code = ?, last_error_at = ? WHERE id = 1",
                    (error, stamp),
                )
            if usage.logged_in is not None:
                connection.execute(
                    "UPDATE worker_status SET claude_logged_in = ? WHERE id = 1",
                    (int(usage.logged_in),),
                )
            if usage.login_expires_at is not None:
                connection.execute(
                    "UPDATE worker_status SET login_expires_at = ? WHERE id = 1",
                    (rows.timestamp(usage.login_expires_at),),
                )

    def record_login(self, now: datetime, status: LoginStatus, *, confirm: bool) -> None:
        """Store a login check made without generating anything.

        "No credential" always wins. "Has a credential" only replaces a refusal seen
        by a real call when `confirm` is set (the worker just started, for example
        after a new token) or the login's expiry changed (a fresh `auth login`);
        otherwise a revoked token would look signed in again.
        """
        expires = rows.timestamp(status.expires_at) if status.expires_at else None
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO worker_status (id, heartbeat_at) VALUES (1, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                (rows.timestamp(now),),
            )
            row = connection.execute(
                "SELECT claude_logged_in, login_expires_at FROM worker_status WHERE id = 1"
            ).fetchone()
            refused = row["claude_logged_in"] == 0
            renewed = expires is not None and expires != row["login_expires_at"]
            if status.logged_in and refused and not (confirm or renewed):
                return
            connection.execute(
                """
                UPDATE worker_status SET claude_logged_in = ?, login_expires_at = ? WHERE id = 1
                """,
                (int(status.logged_in), expires),
            )

    def get(self) -> WorkerStatusRecord:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM worker_status WHERE id = 1").fetchone()
        if row is None:
            return WorkerStatusRecord(None, None, None, None)
        return WorkerStatusRecord(
            heartbeat_at=rows.parse_timestamp(row["heartbeat_at"]),
            last_error_code=rows.error_code(row["last_error_code"]),
            last_error_at=rows.parse_optional_timestamp(row["last_error_at"]),
            login_expires_at=rows.parse_optional_timestamp(row["login_expires_at"]),
            logged_in=None if row["claude_logged_in"] is None else bool(row["claude_logged_in"]),
        )
