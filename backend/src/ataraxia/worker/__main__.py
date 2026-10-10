"""Idle foundation worker with bounded probes and graceful process shutdown."""

import asyncio
import logging
import signal
from pathlib import Path

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ataraxia.bootstrap import create_redis
from ataraxia.config import Settings
from ataraxia.worker.healthcheck import HEARTBEAT

logger = logging.getLogger(__name__)


async def probe_storage(redis: Redis, heartbeat: Path) -> bool:
    """Publish readiness only after Redis responds; clear it on connection failure."""
    try:
        async with asyncio.timeout(3):
            await redis.ping()
    except (RedisError, TimeoutError):
        await asyncio.to_thread(heartbeat.unlink, missing_ok=True)
        return False
    await asyncio.to_thread(heartbeat.touch)
    return True


async def main() -> None:
    """Run one idle loop until SIGINT/SIGTERM, reconnecting after storage failures."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    HEARTBEAT.unlink(missing_ok=True)
    previous: bool | None = None
    logger.info("Worker started; discovery scheduling is not implemented yet")
    try:
        async with create_redis(Settings()) as redis:
            while not stop.is_set():
                ready = await probe_storage(redis, HEARTBEAT)
                if ready != previous:
                    logger.info("Worker storage %s", "ready" if ready else "unavailable")
                    previous = ready
                try:
                    await asyncio.wait_for(stop.wait(), timeout=5)
                except TimeoutError:
                    pass
    finally:
        HEARTBEAT.unlink(missing_ok=True)
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
