"""Owner identity: Firebase token checks with local keys, local-mode limits, startup config."""

import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from support import local_settings

from ataraxia.adapters.firebase import FirebaseVerifier
from ataraxia.api.auth import host_name, is_local_request
from ataraxia.api.main import create_app
from ataraxia.application.ports import IdentityUnavailableError, InvalidTokenError
from ataraxia.bootstrap import ConfigurationError, create_api_services
from ataraxia.config import Settings

PROJECT = "ataraxia-test"
OWNER = "owner-uid"
KID = "test-key"
FIREBASE = {
    "auth_mode": "firebase",
    "owner_uid": OWNER,
    "firebase_project_id": PROJECT,
    "firebase_api_key": "public-api-key",
    "firebase_auth_domain": "ataraxia-test.firebaseapp.com",
    "firebase_app_id": "1:2:web:3",
}

SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeKeys:
    """A key source holding one locally generated public key."""

    def __init__(self, unavailable: bool = False) -> None:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(SIGNING_KEY.public_key()))
        self._keys = {KID: jwt.PyJWK.from_dict({**jwk, "kid": KID, "alg": "RS256"})}
        self._unavailable = unavailable

    def signing_key(self, kid: str) -> jwt.PyJWK:
        if self._unavailable:
            raise IdentityUnavailableError("offline")
        if kid not in self._keys:
            raise InvalidTokenError("unknown key")
        return self._keys[kid]


def token(
    *,
    key: rsa.RSAPrivateKey = SIGNING_KEY,
    kid: str | None = KID,
    algorithm: str = "RS256",
    **claims: object,
) -> str:
    now = int(time.time())
    payload: dict[str, object] = {
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "aud": PROJECT,
        "sub": OWNER,
        "iat": now - 10,
        "exp": now + 3600,
        "auth_time": now - 60,
    }
    payload.update(claims)
    payload = {name: value for name, value in payload.items() if value is not None}
    headers = {"kid": kid} if kid is not None else {}
    signing_key: rsa.RSAPrivateKey | str = (
        key if algorithm == "RS256" else "a-shared-secret-of-at-least-32-bytes"
    )
    return jwt.encode(payload, signing_key, algorithm=algorithm, headers=headers)


class TestFirebaseVerifier:
    verifier = FirebaseVerifier(PROJECT, FakeKeys())

    def test_valid_token_gives_the_uid(self) -> None:
        assert self.verifier.verify(token()) == OWNER

    @pytest.mark.parametrize(
        "bad",
        [
            pytest.param(lambda: None, id="missing"),
            pytest.param(lambda: "not.a.token", id="malformed"),
            pytest.param(lambda: token(exp=int(time.time()) - 120), id="expired"),
            pytest.param(lambda: token(iat=int(time.time()) + 600), id="issued-later"),
            pytest.param(lambda: token(auth_time=int(time.time()) + 600), id="auth-later"),
            pytest.param(lambda: token(auth_time=None), id="no-auth-time"),
            pytest.param(lambda: token(aud="another-project"), id="audience"),
            pytest.param(lambda: token(iss="https://example.com/x"), id="issuer"),
            pytest.param(lambda: token(sub=""), id="empty-subject"),
            pytest.param(lambda: token(sub="x" * 129), id="long-subject"),
            pytest.param(lambda: token(kid=None), id="no-kid"),
            pytest.param(lambda: token(kid="other"), id="unknown-kid"),
            pytest.param(lambda: token(key=OTHER_KEY), id="wrong-signature"),
            pytest.param(lambda: token(algorithm="HS256"), id="hs256"),
        ],
    )
    def test_invalid_tokens_are_rejected(self, bad: Callable[[], str | None]) -> None:
        with pytest.raises(InvalidTokenError):
            self.verifier.verify(bad())

    def test_unreachable_keys(self) -> None:
        with pytest.raises(IdentityUnavailableError):
            FirebaseVerifier(PROJECT, FakeKeys(unavailable=True)).verify(token())


@pytest.fixture
def firebase_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = local_settings(tmp_path, **FIREBASE)
    app = create_app(lambda: create_api_services(settings, keys=FakeKeys()))
    with TestClient(app) as client:
        yield client


class TestFirebaseApi:
    def test_owner_token_is_accepted(self, firebase_client: TestClient) -> None:
        response = firebase_client.get("/api/v1/me", headers={"Authorization": f"Bearer {token()}"})
        assert response.status_code == 200
        assert response.json()["auth_mode"] == "firebase"

    def test_missing_or_invalid_token_is_401(self, firebase_client: TestClient) -> None:
        missing = firebase_client.get("/api/v1/me")
        assert missing.status_code == 401
        assert missing.json()["error"]["code"] == "unauthenticated"
        assert missing.headers["www-authenticate"] == "Bearer"
        expired = token(exp=int(time.time()) - 120)
        response = firebase_client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})
        assert response.status_code == 401

    def test_another_account_is_403(self, firebase_client: TestClient) -> None:
        other = token(sub="someone-else")
        response = firebase_client.get("/api/v1/me", headers={"Authorization": f"Bearer {other}"})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_client_config_is_public(self, firebase_client: TestClient) -> None:
        config = firebase_client.get("/api/v1/client-config").json()
        assert config == {
            "auth_mode": "firebase",
            "firebase": {
                "api_key": "public-api-key",
                "auth_domain": "ataraxia-test.firebaseapp.com",
                "project_id": PROJECT,
                "app_id": "1:2:web:3",
            },
        }

    def test_firebase_mode_refuses_local_shortcuts(self, firebase_client: TestClient) -> None:
        assert firebase_client.get("/api/v1/me", headers={"Host": "localhost"}).status_code == 401


class TestStartup:
    def test_missing_firebase_settings_stop_the_api(self, tmp_path: Path) -> None:
        settings = local_settings(tmp_path, **{**FIREBASE, "owner_uid": ""})
        with pytest.raises(ConfigurationError, match="ATARAXIA_OWNER_UID"):
            create_api_services(settings)
        app = create_app(lambda: create_api_services(settings))
        with pytest.raises(ConfigurationError), TestClient(app):
            pass

    def test_firebase_is_the_default_mode(self) -> None:
        assert Settings.model_fields["auth_mode"].default == "firebase"

    def test_app_and_schema_build_without_configuration(self) -> None:
        schema = create_app().openapi()
        assert "HTTPBearer" in schema["components"]["securitySchemes"]

    def test_unknown_default_time_zone(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError):
            create_api_services(local_settings(tmp_path, default_time_zone="Mars/Base"))


class TestLocalMode:
    @pytest.mark.parametrize(
        "host", ["localhost", "localhost:8080", "127.0.0.1:49152", "[::1]:8080", "LOCALHOST"]
    )
    def test_local_hosts_are_accepted(self, host: str) -> None:
        assert is_local_request({"host": host})

    @pytest.mark.parametrize(
        "host",
        ["example.com", "localhost.example.com", "127.0.0.2", "10.0.0.5:8080", "[::2]", ""],
    )
    def test_other_hosts_are_refused(self, host: str) -> None:
        assert not is_local_request({"host": host})

    def test_tailscale_identity_headers_are_refused(self) -> None:
        assert not is_local_request({"host": "localhost", "tailscale-user-login": "a@b.c"})
        assert not is_local_request({"host": "localhost", "tailscale-user-name": "A"})

    def test_host_name(self) -> None:
        assert host_name("[::1]:80") == "[::1]"
        assert host_name("LocalHost:1") == "localhost"

    def test_api_refuses_forwarded_requests(self, tmp_path: Path) -> None:
        app = create_app(lambda: create_api_services(local_settings(tmp_path)))
        with TestClient(app, base_url="http://localhost:8080") as client:
            assert client.get("/api/v1/me").status_code == 200
            assert client.get("/api/v1/me", headers={"Host": "evil.example"}).status_code == 403
            forwarded = client.get("/api/v1/me", headers={"Tailscale-User-Login": "x@y.z"})
            assert forwarded.status_code == 403
            assert forwarded.json()["error"]["code"] == "forbidden"
            assert client.get("/api/v1/client-config").json() == {
                "auth_mode": "local",
                "firebase": None,
            }
