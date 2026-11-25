"""The worker's single status row: heartbeat, latest error, and Claude login expiry."""

from dataclasses import dataclass
from datetime import datetime

from ataraxia.adapters.sqlite import rows
from ataraxia.adapters.sqlite.database import Database
from ataraxia.domain.jobs import JobErrorCode


@dataclass(frozen=True)
class WorkerStatusRecord:
    heartbeat_at: datetime | None
    last_error_code: JobErrorCode | None
    last_error_at: datetime | None
    login_expires_at: datetime | None


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
            if login_expires_at is not None:
                connection.execute(
                    "UPDATE worker_status SET login_expires_at = ? WHERE id = 1",
                    (rows.timestamp(login_expires_at),),
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
        )
