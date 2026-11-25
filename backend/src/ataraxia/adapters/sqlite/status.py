"""The worker's single status row: heartbeat, latest error, and Claude login state."""

from dataclasses import dataclass
from datetime import datetime

from ataraxia.adapters.sqlite import rows
from ataraxia.adapters.sqlite.database import Database
from ataraxia.application.ports import LoginStatus
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
        self, now: datetime, error: JobErrorCode | None, login_expires_at: datetime | None
    ) -> None:
        """Remember the latest error (if any) and the login expiry the CLI reported."""
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
            # A refused login shows the login is missing; a lesson, a limit message, or
            # malformed output all came from a signed-in account.
            if error == "claude_auth":
                connection.execute("UPDATE worker_status SET claude_logged_in = 0 WHERE id = 1")
            elif error in (None, "invalid_output", "claude_usage_limit"):
                connection.execute("UPDATE worker_status SET claude_logged_in = 1 WHERE id = 1")
            if login_expires_at is not None:
                connection.execute(
                    "UPDATE worker_status SET login_expires_at = ? WHERE id = 1",
                    (rows.timestamp(login_expires_at),),
                )

    def record_login(self, now: datetime, status: LoginStatus) -> None:
        """Store the result of a login check made without generating anything."""
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO worker_status (id, heartbeat_at) VALUES (1, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                (rows.timestamp(now),),
            )
            connection.execute(
                """
                UPDATE worker_status SET claude_logged_in = ?, login_expires_at = ? WHERE id = 1
                """,
                (
                    int(status.logged_in),
                    rows.timestamp(status.expires_at) if status.expires_at else None,
                ),
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
