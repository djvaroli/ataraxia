"""Streaks over the local dates on which lessons were finished."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


@dataclass(frozen=True)
class Streaks:
    current: int
    longest: int


def streaks(finished_on: Iterable[date], today: date) -> Streaks:
    """Count consecutive days with a finished lesson.

    The current streak ends today, or yesterday when nothing is finished yet today,
    so a streak is not lost before the day is over.
    """
    days = set(finished_on)
    longest = 0
    for day in days:
        if day - ONE_DAY in days:
            continue
        length = 1
        while day + length * ONE_DAY in days:
            length += 1
        longest = max(longest, length)
    end = today if today in days else today - ONE_DAY
    current = 0
    while end - current * ONE_DAY in days:
        current += 1
    return Streaks(current=current, longest=longest)
