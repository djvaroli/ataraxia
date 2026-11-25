"""The worker reports stale or interrupted database contact as unhealthy."""

import os
import time
from datetime import UTC, datetime
from pathlib import Path

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.migrations import migrate
from ataraxia.worker.__main__ import record_heartbeat
from ataraxia.worker.healthcheck import MAX_AGE_SECONDS, is_healthy

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


def test_heartbeat_recovers_after_storage_failure(tmp_path: Path) -> None:
    heartbeat = tmp_path / "heartbeat"
    database = Database(tmp_path / "app.db")
    migrate(database)
    assert not is_healthy(heartbeat)
    assert record_heartbeat(database, heartbeat, NOW)
    assert is_healthy(heartbeat)
    with database.connect() as connection:
        stored = connection.execute("SELECT heartbeat_at FROM worker_status").fetchone()
    assert stored["heartbeat_at"] == NOW.isoformat()

    database.path = tmp_path / "missing-directory" / "app.db"
    assert not record_heartbeat(database, heartbeat, NOW)
    assert not is_healthy(heartbeat)


def test_stale_heartbeat_is_unhealthy(tmp_path: Path) -> None:
    heartbeat = tmp_path / "heartbeat"
    heartbeat.touch()
    stale = time.time() - MAX_AGE_SECONDS - 1
    os.utime(heartbeat, (stale, stale))
    assert not is_healthy(heartbeat)
