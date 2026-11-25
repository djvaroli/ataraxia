"""Firebase ID token verification with Google's published signing keys.

Follows Firebase's guide for third-party JWT libraries:
https://firebase.google.com/docs/auth/admin/verify-id-tokens#verify_id_tokens_using_a_third-party_jwt_library
"""

import time
from typing import Protocol

import jwt

from ataraxia.application.ports import IdentityUnavailableError, InvalidTokenError

GOOGLE_KEYS_URL = (
    "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
)
KEY_FETCH_TIMEOUT_SECONDS = 5
KEY_CACHE_SECONDS = 3600
# Tolerated clock difference between this host and Google's servers.
LEEWAY_SECONDS = 30
MAX_UID_LENGTH = 128


class SigningKeySource(Protocol):
    def signing_key(self, kid: str) -> jwt.PyJWK:
        """The public key with this ID. Raises `InvalidTokenError` for an unknown ID
        and `IdentityUnavailableError` when the keys cannot be fetched."""
        ...


class GoogleSigningKeys:
    """Google's securetoken keys, fetched over HTTPS and cached in memory."""

    def __init__(self, url: str = GOOGLE_KEYS_URL) -> None:
        self._client = jwt.PyJWKClient(
            url, lifespan=KEY_CACHE_SECONDS, timeout=KEY_FETCH_TIMEOUT_SECONDS
        )

    def signing_key(self, kid: str) -> jwt.PyJWK:
        try:
            return self._client.get_signing_key(kid)
        except jwt.PyJWKClientConnectionError as error:
            raise IdentityUnavailableError("Signing keys are unavailable") from error
        except jwt.PyJWKClientError as error:
            raise InvalidTokenError("Unknown signing key") from error


class FirebaseVerifier:
    """Implements `IdentityVerifier` for Firebase Authentication ID tokens."""

    def __init__(self, project_id: str, keys: SigningKeySource) -> None:
        self._project_id = project_id
        self._issuer = f"https://securetoken.google.com/{project_id}"
        self._keys = keys

    def verify(self, token: str | None) -> str:
        if not token:
            raise InvalidTokenError("Missing token")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as error:
            raise InvalidTokenError("Malformed token") from error
        kid = header.get("kid")
        if header.get("alg") != "RS256" or not isinstance(kid, str) or not kid:
            raise InvalidTokenError("Unexpected token header")
        key = self._keys.signing_key(kid)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self._project_id,
                issuer=self._issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "aud", "iss", "sub", "auth_time"]},
            )
        except jwt.InvalidTokenError as error:
            raise InvalidTokenError("Token rejected") from error
        auth_time = claims["auth_time"]
        if not isinstance(auth_time, int | float) or auth_time > time.time() + LEEWAY_SECONDS:
            raise InvalidTokenError("Authentication time is in the future")
        subject = claims["sub"]
        if not isinstance(subject, str) or not 0 < len(subject) <= MAX_UID_LENGTH:
            raise InvalidTokenError("Unexpected subject")
        return subject
