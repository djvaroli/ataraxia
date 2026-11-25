"""Errors raised by domain rules."""


class InvalidInputError(ValueError):
    """Well-formed input that breaks a rule, e.g. an unknown time zone."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
