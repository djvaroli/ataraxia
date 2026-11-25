"""Health endpoints distinguish process availability from storage readiness."""

from pathlib import Path

from fastapi.testclient import TestClient
from support import local_settings

from ataraxia.api.main import create_app
from ataraxia.bootstrap import create_api_services


def test_liveness_and_readiness_with_a_migrated_database(tmp_path: Path) -> None:
    app = create_app(lambda: create_api_services(local_settings(tmp_path)))
    with TestClient(app) as client:
        assert client.get("/api/health/live").json() == {"status": "ok"}
        ready = client.get("/api/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok"}


def test_readiness_fails_without_exposing_details(tmp_path: Path) -> None:
    services = create_api_services(local_settings(tmp_path))
    with TestClient(create_app(lambda: services)) as client:
        services.database.path = tmp_path / "missing-directory" / "app.db"
        failed = client.get("/api/health/ready")
        live = client.get("/api/health/live")
    assert failed.status_code == 503
    assert failed.json() == {"status": "unavailable"}
    assert live.status_code == 200
