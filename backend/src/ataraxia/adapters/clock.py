"""The real clock."""

from datetime import UTC, datetime


class SystemClock:
    """Implements `Clock` with the host's time."""

    def now(self) -> datetime:
        return datetime.now(UTC)
