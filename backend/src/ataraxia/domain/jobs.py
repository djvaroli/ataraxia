"""Kinds, states, and failure codes of lesson preparation jobs."""

from typing import Literal

JobKind = Literal["daily", "surprise", "subject", "topic", "follow_up"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]
JobErrorCode = Literal[
    "claude_auth",
    "claude_usage_limit",
    "claude_timeout",
    "invalid_output",
    "claude_error",
    "daily_limit",
    "interrupted",
]

# Errors that another immediate attempt cannot fix; the owner must act or wait.
FINAL_ERRORS: frozenset[JobErrorCode] = frozenset(
    {"claude_auth", "claude_usage_limit", "daily_limit"}
)
MAX_ATTEMPTS = 2
