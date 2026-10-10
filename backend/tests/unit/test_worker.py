"""A worker reports stale or interrupted storage connectivity as unhealthy."""

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock

from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from ataraxia.worker.__main__ import probe_storage
from ataraxia.worker.healthcheck import MAX_AGE_SECONDS, is_healthy


async def test_heartbeat_recovers_after_storage_failure(tmp_path: Path) -> None:
    heartbeat = tmp_path / "heartbeat"
    redis = AsyncMock(spec=Redis)
    redis.ping = AsyncMock(side_effect=[True, ConnectionError(), True])
    assert not is_healthy(heartbeat)
    assert await probe_storage(redis, heartbeat)
    assert is_healthy(heartbeat)
    assert not await probe_storage(redis, heartbeat)
    assert not is_healthy(heartbeat)
    assert await probe_storage(redis, heartbeat)
    assert is_healthy(heartbeat)


def test_stale_heartbeat_is_unhealthy(tmp_path: Path) -> None:
    heartbeat = tmp_path / "heartbeat"
    heartbeat.touch()
    stale = time.time() - MAX_AGE_SECONDS - 1
    os.utime(heartbeat, (stale, stale))
    assert not is_healthy(heartbeat)
