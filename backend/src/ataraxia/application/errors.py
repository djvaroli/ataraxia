"""Failures a use case reports to its caller; the API maps each to a status code."""

from typing import Literal

LimitCode = Literal["daily_limit", "too_many_waiting"]


class NotFoundError(Exception):
    """The lesson or job does not exist."""


class ConflictError(Exception):
    """The record exists but is not in a state that allows the change."""


class LimitReachedError(Exception):
    """A new job would exceed the daily cap or the waiting-job limit."""

    def __init__(self, code: LimitCode, message: str) -> None:
        super().__init__(message)
        self.code: LimitCode = code
