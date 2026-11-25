"""Kinds, states, and failure codes of lesson preparation jobs, and what follows a failure."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, get_args

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
JOB_KINDS: tuple[JobKind, ...] = get_args(JobKind)
JOB_STATUSES: tuple[JobStatus, ...] = get_args(JobStatus)
JOB_ERROR_CODES: tuple[JobErrorCode, ...] = get_args(JobErrorCode)

# Errors that another immediate attempt cannot fix; the owner must act or wait.
FINAL_ERRORS: frozenset[JobErrorCode] = frozenset(
    {"claude_auth", "claude_usage_limit", "daily_limit"}
)
# Calls refused for these reasons did no work, so they do not count toward the daily cap.
UNCOUNTED_OUTCOMES: frozenset[JobErrorCode] = frozenset({"claude_auth", "claude_usage_limit"})
MAX_ATTEMPTS = 2
WAITING_LIMIT = 3
RETRY_DELAY = timedelta(seconds=30)
USAGE_LIMIT_DELAY = timedelta(minutes=30)
USAGE_LIMIT_GIVE_UP = timedelta(hours=24)

ERROR_MESSAGES: dict[JobErrorCode, str] = {
    "claude_auth": (
        "Claude is not signed in on the server. On the host, run "
        "`docker compose exec -it worker claude auth login`, then retry."
    ),
    "claude_usage_limit": (
        "Claude's usage limit was reached. The lesson tries again every half hour for up to a day."
    ),
    "claude_timeout": "Claude took too long to write the lesson.",
    "invalid_output": "Claude's lesson came back incomplete or in the wrong form.",
    "claude_error": "Claude could not write the lesson.",
    "daily_limit": "Today's lesson limit was reached. Ask again tomorrow.",
    "interrupted": "The worker stopped while it was preparing this lesson.",
}


@dataclass(frozen=True)
class Requeue:
    """Try again at `at`. `refund` returns the attempt just used (usage limits)."""

    at: datetime
    refund: bool = False


@dataclass(frozen=True)
class Fail:
    """Stop trying; the owner can retry from the UI."""


FailureDecision = Requeue | Fail


def after_failure(
    code: JobErrorCode, attempts: int, queued_at: datetime, now: datetime
) -> FailureDecision:
    """Decide what happens to a job whose attempt number `attempts` failed with `code`.

    `queued_at` is when the job was requested or last retried.
    """
    if code == "claude_usage_limit":
        next_attempt = now + USAGE_LIMIT_DELAY
        if next_attempt - queued_at > USAGE_LIMIT_GIVE_UP:
            return Fail()
        return Requeue(next_attempt, refund=True)
    if code in FINAL_ERRORS or attempts >= MAX_ATTEMPTS:
        return Fail()
    return Requeue(now + RETRY_DELAY)
