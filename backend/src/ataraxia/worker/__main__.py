"""Worker loop with database heartbeats and graceful shutdown."""

import logging
import signal
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.migrations import migrate
from ataraxia.bootstrap import create_database
from ataraxia.config import Settings
from ataraxia.worker.healthcheck import HEARTBEAT

logger = logging.getLogger(__name__)
LOOP_SECONDS = 5


def record_heartbeat(database: Database, heartbeat: Path, now: datetime) -> bool:
    """Record contact in the database and the health file; clear the file on failure."""
    try:
        with database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO worker_status (id, heartbeat_at) VALUES (1, ?)
                ON CONFLICT (id) DO UPDATE SET heartbeat_at = excluded.heartbeat_at
                """,
                (now.isoformat(),),
            )
    except sqlite3.Error:
        heartbeat.unlink(missing_ok=True)
        return False
    heartbeat.touch()
    return True


def main() -> None:
    """Run until SIGINT/SIGTERM, recovering after database failures."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop = threading.Event()

    def request_stop(_signal: int, _frame: FrameType | None) -> None:
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, request_stop)

    HEARTBEAT.unlink(missing_ok=True)
    database = create_database(Settings())
    migrate(database)
    logger.info("Worker started")
    previous: bool | None = None
    try:
        while not stop.is_set():
            ready = record_heartbeat(database, HEARTBEAT, datetime.now(UTC))
            if ready != previous:
                logger.info("Worker storage %s", "ready" if ready else "unavailable")
                previous = ready
            stop.wait(LOOP_SECONDS)
    finally:
        HEARTBEAT.unlink(missing_ok=True)
        logger.info("Worker stopped")


if __name__ == "__main__":
    main()
