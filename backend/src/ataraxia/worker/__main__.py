"""The lesson worker process: a heartbeat thread and a sequential job loop.

The heartbeat runs on its own thread so a long Claude call does not make the
container look unhealthy. Only one worker may run against a database.
"""

import logging
import signal
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.migrations import migrate
from ataraxia.adapters.sqlite.status import WorkerStatusRepository
from ataraxia.application.worker import LessonWorker
from ataraxia.bootstrap import create_worker
from ataraxia.config import Settings
from ataraxia.worker.healthcheck import HEARTBEAT

logger = logging.getLogger(__name__)
LOOP_SECONDS = 2
HEARTBEAT_SECONDS = 5


def record_heartbeat(database: Database, heartbeat: Path, now: datetime) -> bool:
    """Record contact in the database and the health file; clear the file on failure."""
    try:
        WorkerStatusRepository(database).heartbeat(now)
    except sqlite3.Error:
        heartbeat.unlink(missing_ok=True)
        return False
    heartbeat.touch()
    return True


def beat_until(stop: threading.Event, database: Database, heartbeat: Path) -> None:
    previous: bool | None = None
    while not stop.is_set():
        ready = record_heartbeat(database, heartbeat, datetime.now(UTC))
        if ready != previous:
            logger.info("Worker storage %s", "ready" if ready else "unavailable")
            previous = ready
        stop.wait(HEARTBEAT_SECONDS)


def run_jobs(stop: threading.Event, worker: LessonWorker) -> None:
    """Loop until `stop`: recover once, schedule the morning lesson, take one job.

    After an unexpected error the next pass recovers again, which is safe because
    this is the only worker and it is not inside a job at that point.
    """
    recover = True
    while not stop.is_set():
        busy = False
        try:
            if recover:
                recovered = worker.recover()
                if recovered:
                    logger.info("Recovered %d interrupted jobs", recovered)
                recover = False
            worker.ensure_morning_lesson()
            busy = worker.step()
        except Exception as error:
            # The type only: messages can contain lesson text.
            logger.error("Worker loop failed with %s; retrying", type(error).__name__)
            recover = True
        if not busy:
            stop.wait(LOOP_SECONDS)


def main() -> None:
    """Run until SIGINT/SIGTERM, recovering after database failures."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop = threading.Event()

    def request_stop(_signal: int, _frame: FrameType | None) -> None:
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, request_stop)

    HEARTBEAT.unlink(missing_ok=True)
    services = create_worker(Settings())
    migrate(services.database)
    logger.info("Worker started")
    beats = threading.Thread(
        target=beat_until, args=(stop, services.database, HEARTBEAT), daemon=True
    )
    beats.start()
    try:
        run_jobs(stop, services.worker)
    finally:
        stop.set()
        beats.join(timeout=HEARTBEAT_SECONDS)
        HEARTBEAT.unlink(missing_ok=True)
        logger.info("Worker stopped")


if __name__ == "__main__":
    main()
