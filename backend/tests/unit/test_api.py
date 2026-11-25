"""HTTP flow and error mapping with the fake generator, a fixed clock, and local mode."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from support import FixedClock, ScriptedGenerator, local_settings

from ataraxia.adapters.fake_generator import NoIllustrations
from ataraxia.api.main import create_app
from ataraxia.application.worker import LessonWorker
from ataraxia.bootstrap import create_api_services, create_worker

SESSION = "00000000-0000-4000-8000-000000000001"


@dataclass
class Stack:
    client: TestClient
    worker: LessonWorker


@pytest.fixture
def stack(tmp_path: Path) -> Iterator[Stack]:
    settings = local_settings(tmp_path)
    clock = FixedClock()
    app = create_app(lambda: create_api_services(settings, clock=clock))
    worker = create_worker(
        settings, clock=clock, generator=ScriptedGenerator(), illustrations=NoIllustrations()
    ).worker
    with TestClient(app, base_url="http://localhost:8080") as client:
        yield Stack(client, worker)


def error(response_json: dict[str, object]) -> object:
    return response_json["error"]


def test_request_prepare_and_read_a_lesson(stack: Stack) -> None:
    client = stack.client
    requested = client.post("/api/v1/lessons/requests", json={"kind": "subject", "subject": "math"})
    assert requested.status_code == 202
    job = requested.json()
    assert (job["status"], job["subject"]) == ("queued", "math")

    assert stack.worker.step()
    job = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert job["status"] == "succeeded"
    lesson_id = job["lesson_id"]

    lesson = client.get(f"/api/v1/lessons/{lesson_id}").json()
    assert lesson["subject"] == "math" and "$$" in lesson["body_markdown"]
    assert [entry["id"] for entry in lesson["thread"]] == [lesson_id]

    assert client.post(f"/api/v1/lessons/{lesson_id}/opened").status_code == 200
    report = {"session_id": SESSION, "seconds": 120, "scroll": 0.6}
    assert client.post(f"/api/v1/lessons/{lesson_id}/reading", json=report).status_code == 200
    state = client.put(f"/api/v1/lessons/{lesson_id}/finished", json={"finished": True}).json()
    assert state["finished_at"] is not None and state["read_seconds"] == 120

    progress = client.get("/api/v1/progress").json()
    assert (progress["current_streak"], progress["finished_total"]) == (1, 1)
    page = client.get("/api/v1/lessons", params={"subject": "math"}).json()
    assert [item["id"] for item in page["items"]] == [lesson_id]
    assert page["next_cursor"] is None

    assert client.post("/api/v1/activity", json={"type": "app.opened"}).status_code == 204
    first = client.get("/api/v1/activity", params={"limit": 2}).json()
    rest = client.get("/api/v1/activity", params={"cursor": first["next_cursor"]}).json()
    types = [event["type"] for event in first["items"] + rest["items"]]
    assert types == [
        "lesson.requested",
        "lesson.prepared",
        "lesson.opened",
        "lesson.finished",
        "app.opened",
    ]
    exported = client.get("/api/v1/export").json()
    assert len(exported["lessons"]) == 1 and len(exported["reading_sessions"]) == 1


def test_today_and_daily_ensure(stack: Stack) -> None:
    client = stack.client
    today = client.get("/api/v1/today").json()
    assert today["daily"]["status"] == "not_scheduled"  # 15:00 UTC is past the 06:00 hour.
    assert today["allowance"] == {
        "used": 0,
        "limit": 8,
        "remaining": 8,
        "waiting": 0,
        "waiting_limit": 3,
    }
    first = client.post("/api/v1/today/lesson")
    second = client.post("/api/v1/today/lesson")
    assert first.status_code == 202 and first.json()["status"] == "queued"
    assert first.json()["job"]["id"] == second.json()["job"]["id"]
    stack.worker.step()
    daily = client.get("/api/v1/today").json()["daily"]
    assert daily["status"] == "ready" and daily["lesson"]["id"] == daily["job"]["lesson_id"]


def test_settings_round_trip(stack: Stack) -> None:
    client = stack.client
    me = client.get("/api/v1/me").json()
    assert me["auth_mode"] == "local" and len(me["catalog"]) == 11
    updated = client.patch("/api/v1/me", json={"time_zone": "Asia/Tokyo", "morning_hour": 7})
    assert updated.status_code == 200
    assert updated.json()["preferences"]["time_zone_confirmed"] is True
    bad = client.patch("/api/v1/me", json={"time_zone": "Asia/Nowhere"})
    assert bad.status_code == 422
    assert error(bad.json()) == {
        "code": "validation_failed",
        "message": "Use an IANA time zone such as Europe/Paris.",
        "fields": [
            {"field": "time_zone", "message": "Use an IANA time zone such as Europe/Paris."}
        ],
    }


def test_validation_errors_name_the_field(stack: Stack) -> None:
    response = stack.client.post("/api/v1/lessons/requests", json={"kind": "topic", "topic": "x"})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_failed"
    assert [field["field"] for field in body["fields"]] == ["topic.topic"]
    hour = stack.client.patch("/api/v1/me", json={"morning_hour": 24})
    assert hour.json()["error"]["fields"][0]["field"] == "morning_hour"


def test_missing_records_and_routes(stack: Stack) -> None:
    client = stack.client
    for response in (
        client.get("/api/v1/lessons/missing"),
        client.get("/api/v1/jobs/missing"),
        client.put("/api/v1/lessons/missing/saved", json={"saved": True}),
        client.get("/api/v1/missing"),
    ):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
    method = client.delete("/api/v1/me")
    assert method.status_code == 405 and "error" in method.json()


def test_follow_up_rules(stack: Stack) -> None:
    client = stack.client
    job = client.post("/api/v1/lessons/requests", json={"kind": "surprise"}).json()
    stack.worker.step()
    lesson_id = client.get(f"/api/v1/jobs/{job['id']}").json()["lesson_id"]
    both = client.post(
        f"/api/v1/lessons/{lesson_id}/follow-ups", json={"direction": 0, "question": "Why?"}
    )
    assert both.status_code == 422 and both.json()["error"]["fields"][0]["field"] == "direction"
    question = client.post(
        f"/api/v1/lessons/{lesson_id}/follow-ups", json={"question": "What came before?"}
    )
    assert question.status_code == 202
    assert question.json()["request_text"] == "What came before?"


def test_limits_and_conflicts(stack: Stack) -> None:
    client = stack.client
    jobs = [client.post("/api/v1/lessons/requests", json={"kind": "surprise"}) for _ in range(4)]
    assert [response.status_code for response in jobs] == [202, 202, 202, 429]
    assert jobs[-1].json()["error"]["code"] == "too_many_waiting"
    retry = client.post(f"/api/v1/jobs/{jobs[0].json()['id']}/retry")
    assert retry.status_code == 409 and retry.json()["error"]["code"] == "conflict"
    assert client.post("/api/v1/activity", json={"type": "lesson.opened"}).status_code == 422
    bad_cursor = client.get("/api/v1/lessons", params={"cursor": "%%%"})
    assert bad_cursor.status_code == 422
    for cursor in ("²", "9" * 30, "-1"):
        response = client.get("/api/v1/activity", params={"cursor": cursor})
        assert response.status_code == 422, cursor


def test_unexpected_errors_return_error_body_without_details(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    services = create_api_services(local_settings(tmp_path))

    def broken() -> None:
        raise ValueError("stored lesson text")

    app = create_app(lambda: services)
    with TestClient(app, base_url="http://localhost") as client:
        object.__setattr__(services.progress, "progress", broken)
        response = client.get("/api/v1/progress")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "unavailable"
    assert "stored lesson text" not in caplog.text
    assert "ValueError" in caplog.text
