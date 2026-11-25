"""Exercise the real stack in a unique disposable project and data volume."""

import argparse
import json
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
PROJECT = f"ataraxia-smoke-{uuid4().hex[:12]}"
COMPOSE = [
    "docker",
    "compose",
    "--project-name",
    PROJECT,
    "-f",
    str(ROOT / "compose.yaml"),
]
# Local mode and the fake generator, so a lesson is prepared without Firebase or Claude.
ENV = {
    **os.environ,
    "ATARAXIA_HTTP_PORT": "0",
    "ATARAXIA_AUTH_MODE": "local",
    "ATARAXIA_GENERATOR": "fake",
}


def compose(*args: str) -> str:
    result = subprocess.run(
        COMPOSE + list(args), env=ENV, check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def request(
    base: str,
    path: str,
    *,
    method: str = "GET",
    body: object = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, str]:
    data = None if body is None else json.dumps(body).encode()
    sent = Request(base + path, data=data, method=method, headers=headers or {})
    if data is not None:
        sent.add_header("Content-Type", "application/json")
    try:
        with urlopen(sent, timeout=5) as response:
            return response.status, response.read().decode()
    except HTTPError as error:
        return error.code, error.read().decode()


def api(base: str, path: str, *, method: str = "GET", body: object = None) -> object:
    """Call the API with the Host a local browser sends; nginx passes it through."""
    host = "localhost:" + base.rsplit(":", 1)[1]
    code, text = request(base, path, method=method, body=body, headers={"Host": host})
    assert code in (200, 202), f"{method} {path} returned {code}: {text}"
    return json.loads(text)


def check_lesson_flow(base: str) -> str:
    """Request a lesson, wait for the worker to prepare it, and read it."""
    config = api(base, "/api/v1/client-config")
    assert config == {"auth_mode": "local", "firebase": None}, config
    job = api(base, "/api/v1/lessons/requests", method="POST", body={"kind": "surprise"})
    assert isinstance(job, dict) and job["status"] == "queued", job
    prepared: dict[str, object] = {}

    def ready() -> bool:
        current = api(base, f"/api/v1/jobs/{job['id']}")
        assert isinstance(current, dict) and current["status"] != "failed", current
        prepared.update(current)
        return current["status"] == "succeeded"

    wait_for(ready, "the lesson to be prepared")
    lesson = api(base, f"/api/v1/lessons/{prepared['lesson_id']}")
    assert isinstance(lesson, dict) and lesson["body_markdown"].startswith("## "), lesson
    forged = request(base, "/api/v1/me", headers={"Host": "attacker.example"})
    assert forged[0] == 403, forged
    return str(lesson["id"])


def status(base: str, path: str) -> int:
    try:
        return request(base, path)[0]
    except (URLError, TimeoutError):
        return 0


def sql(statement: str) -> str:
    """Run SQL in the API container against the stack's own database volume."""
    return compose(
        "exec", "-T", "api", "python", "-m", "sqlite3", "/data/ataraxia.db", statement
    ).strip("()', \n")


def wait_for(check: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(1)
    raise AssertionError(f"Timed out waiting for {what}")


def wait_ready(base: str) -> None:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            if request(base, "/api/health/ready") == (200, '{"status":"ok"}'):
                return
        except (URLError, TimeoutError):
            pass
        time.sleep(1)
    raise AssertionError("Readiness did not recover")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dev", action="store_true", help="also use the development override"
    )
    args = parser.parse_args()
    if args.dev:
        COMPOSE.extend(["-f", str(ROOT / "compose.dev.yaml")])
    print(f"Checking isolated project {PROJECT}", flush=True)
    try:
        subprocess.run(
            COMPOSE + ["up", "--build", "--detach", "--wait", "--wait-timeout", "120"],
            env=ENV,
            check=True,
        )
        base = "http://" + compose("port", "nginx", "80")
        assert "Ataraxia" in request(base, "/")[1]
        if args.dev:
            assert request(base, "/@vite/client")[0] == 200
            assert request(base, "/src/main.tsx")[0] == 200
            print("Vite development modules are served through nginx", flush=True)
        assert request(base, "/api/health/live") == (200, '{"status":"ok"}')
        wait_ready(base)
        assert request(base, "/api/v1/missing")[0] == 404
        lesson_id = check_lesson_flow(base)
        print("Lesson prepared and read through nginx; forged Host refused", flush=True)
        for service in ("frontend", "api", "worker"):
            container = compose("ps", "--quiet", service)
            ports = subprocess.check_output(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{json .HostConfig.PortBindings}}",
                    container,
                ],
                text=True,
            )
            assert not json.loads(ports), f"Unexpected published ports: {service}"
        print("Routing and private ports passed", flush=True)

        # Only the worker carries the Claude CLI; the API never does.
        assert "Claude Code" in compose("exec", "-T", "worker", "claude", "--version")
        api_cli = subprocess.run(
            COMPOSE + ["exec", "-T", "api", "sh", "-c", "command -v claude"],
            env=ENV,
            capture_output=True,
            text=True,
        )
        assert api_cli.returncode != 0, "The API image must not contain the Claude CLI"
        print("Claude CLI present only in the worker", flush=True)

        assert sql("PRAGMA journal_mode") == "wal"
        wait_for(lambda: sql("SELECT COUNT(*) FROM worker_status") == "1", "worker heartbeat")
        sql("CREATE TABLE smoke_sentinel (value TEXT)")
        sql("INSERT INTO smoke_sentinel VALUES ('survives')")
        compose("up", "--detach", "--no-deps", "--force-recreate", "api", "worker")
        compose("up", "--detach", "--wait", "--wait-timeout", "60")
        wait_ready(base)
        assert sql("SELECT value FROM smoke_sentinel") == "survives"
        assert api(base, f"/api/v1/lessons/{lesson_id}")
        print("Database persistence across container recreation passed", flush=True)

        compose("up", "--detach", "--no-deps", "--force-recreate", "api", "frontend")
        wait_ready(base)
        # nginx re-resolves upstream addresses every few seconds.
        wait_for(lambda: status(base, "/") == 200, "frontend through nginx")
        print("nginx recovered after upstream recreation", flush=True)
    except BaseException:
        subprocess.run(
            COMPOSE + ["logs", "--no-color", "--tail", "60"], env=ENV, check=False
        )
        raise
    finally:
        subprocess.run(
            COMPOSE + ["down", "--volumes", "--remove-orphans"], env=ENV, check=True
        )


if __name__ == "__main__":
    main()
