"""Exercise the real stack in a unique disposable project and data volume."""

import argparse
import json
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
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
ENV = {**os.environ, "ATARAXIA_HTTP_PORT": "0"}


def compose(*args: str) -> str:
    result = subprocess.run(
        COMPOSE + list(args), env=ENV, check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def request(base: str, path: str) -> tuple[int, str]:
    try:
        with urlopen(base + path, timeout=5) as response:
            return response.status, response.read().decode()
    except HTTPError as error:
        return error.code, error.read().decode()


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

        assert sql("PRAGMA journal_mode") == "wal"
        wait_for(lambda: sql("SELECT COUNT(*) FROM worker_status") == "1", "worker heartbeat")
        sql("CREATE TABLE smoke_sentinel (value TEXT)")
        sql("INSERT INTO smoke_sentinel VALUES ('survives')")
        compose("up", "--detach", "--no-deps", "--force-recreate", "api", "worker")
        compose("up", "--detach", "--wait", "--wait-timeout", "60")
        wait_ready(base)
        assert sql("SELECT value FROM smoke_sentinel") == "survives"
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
