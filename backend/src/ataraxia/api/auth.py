"""Who may call the application routes.

firebase mode: a verified Firebase ID token whose UID is the configured owner.
local mode: no sign-in, but only for requests addressed to this machine by a local
name and not forwarded by Tailscale, so another device or a DNS-rebinding page
cannot use it.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from ataraxia.api.errors import ApiError
from ataraxia.application.ports import (
    IdentityUnavailableError,
    IdentityVerifier,
    InvalidTokenError,
)
from ataraxia.config import AuthMode

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})
FORWARDED_IDENTITY_HEADERS = ("tailscale-user-login", "tailscale-user-name")


@dataclass(frozen=True)
class OwnerPolicy:
    mode: AuthMode
    verifier: IdentityVerifier
    owner_uid: str


def host_name(host: str) -> str:
    """The name part of a Host header: `localhost:8080` gives `localhost`, and
    `[::1]:8080` gives `[::1]`."""
    host = host.strip().lower()
    if host.startswith("["):
        end = host.find("]")
        return host[: end + 1] if end != -1 else host
    return host.split(":", 1)[0]


def is_local_request(headers: Mapping[str, str]) -> bool:
    if any(name in headers for name in FORWARDED_IDENTITY_HEADERS):
        return False
    return host_name(headers.get("host", "")) in LOCAL_HOSTS


def authenticate(policy: OwnerPolicy, headers: Mapping[str, str], token: str | None) -> str:
    """Return the owner's UID or raise `ApiError` (401, 403, or 503)."""
    if policy.mode == "local" and not is_local_request(headers):
        raise ApiError(403, "forbidden", "Local mode accepts requests from this machine only.")
    try:
        uid = policy.verifier.verify(token)
    except InvalidTokenError as error:
        raise ApiError(
            401,
            "unauthenticated",
            "Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except IdentityUnavailableError as error:
        raise ApiError(503, "unavailable", "Sign-in cannot be checked right now.") from error
    if uid != policy.owner_uid:
        raise ApiError(403, "forbidden", "This account cannot use this app.")
    return uid
