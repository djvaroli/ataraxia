"""Health endpoints distinguish process availability from storage readiness."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from ataraxia.api.main import create_app, get_redis


def test_liveness_does_not_require_storage() -> None:
    app = create_app()
    redis = AsyncMock(spec=Redis)
    redis.ping = AsyncMock(side_effect=ConnectionError("private connection detail"))
    app.dependency_overrides[get_redis] = lambda: redis
    with TestClient(app) as client:
        response = client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    redis.ping.assert_not_called()


@pytest.mark.parametrize("error", [ConnectionError("private detail"), TimeoutError()])
def test_readiness_recovers_without_exposing_connection_details(error: Exception) -> None:
    app = create_app()
    redis = AsyncMock(spec=Redis)
    redis.ping = AsyncMock(side_effect=[error, True])
    app.dependency_overrides[get_redis] = lambda: redis
    with TestClient(app) as client:
        failed = client.get("/api/health/ready")
        recovered = client.get("/api/health/ready")
    assert failed.status_code == 503
    assert failed.json() == {"status": "unavailable"}
    assert recovered.status_code == 200
    assert recovered.json() == {"status": "ok"}
