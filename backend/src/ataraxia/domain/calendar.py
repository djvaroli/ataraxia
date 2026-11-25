"""Converting UTC instants into the owner's local calendar."""

from datetime import date, datetime
from functools import cache
from importlib import resources
from zoneinfo import ZoneInfo


@cache
def time_zone_names() -> frozenset[str]:
    """IANA zone names from the pinned `tzdata` package.

    The system list is not used: it can include host aliases such as `localtime`.
    `Factory` is a placeholder zone, not a place.
    """
    listed = resources.files("tzdata").joinpath("zones").read_text(encoding="utf-8")
    return frozenset(name.strip() for name in listed.splitlines() if name.strip()) - {"Factory"}


def is_time_zone(name: str) -> bool:
    return name in time_zone_names()


def local_time(moment: datetime, time_zone: str) -> datetime:
    """`moment` (timezone-aware) as wall-clock time in `time_zone`."""
    return moment.astimezone(ZoneInfo(time_zone))


def local_date(moment: datetime, time_zone: str) -> date:
    return local_time(moment, time_zone).date()
