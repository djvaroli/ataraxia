"""Who may call the application routes.

firebase mode: a verified Firebase ID token whose UID is the configured owner.
local mode: no sign-in, but only for requests addressed to this machine by a local
name and not relayed by Tailscale or another proxy, so a DNS-rebinding page or a
forwarded request cannot use it. Local mode must never run on a reachable host.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from ataraxia.api.errors import ApiError
from ataraxia.application.ports import (
    IdentityUnavailableError,
    IdentityVerifier,
    InvalidTokenError,
)
from ataraxia.config import AuthMode

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})
FORWARDED_IDENTITY_HEADERS = (
    "tailscale-user-login",
    "tailscale-user-name",
    "tailscale-funnel-request",
)


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
    """A request sent to this machine by a local name and not relayed by another proxy.

    The Host check stops DNS-rebinding pages, not a client that writes its own Host.
    nginx adds one `X-Forwarded-For` entry; a second means another proxy (for example
    `tailscale serve`) relayed the request. Tailscale's own headers mark it too.
    """
    if any(name in headers for name in FORWARDED_IDENTITY_HEADERS):
        return False
    if "," in headers.get("x-forwarded-for", ""):
        return False
    # A page on another site can send simple cross-site requests to localhost.
    if headers.get("sec-fetch-site", "").lower() == "cross-site":
        return False
    origin = headers.get("origin")
    if origin is not None and host_name(urlsplit(origin).netloc) not in LOCAL_HOSTS:
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
