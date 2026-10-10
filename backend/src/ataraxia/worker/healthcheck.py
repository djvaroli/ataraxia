"""Readiness reflects recent successful work-loop contact with Redis."""

import time
from pathlib import Path

HEARTBEAT = Path("/tmp/ataraxia-worker-heartbeat")
MAX_AGE_SECONDS = 20


def is_healthy(path: Path = HEARTBEAT) -> bool:
    """A missing or stale heartbeat marks the worker unavailable."""
    try:
        return 0 <= time.time() - path.stat().st_mtime < MAX_AGE_SECONDS
    except FileNotFoundError:
        return False


if __name__ == "__main__":
    raise SystemExit(0 if is_healthy() else 1)
