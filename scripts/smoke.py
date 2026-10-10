"""Exercise the real stack in a unique disposable project and Redis volume."""

import argparse
import json
import os
import subprocess
import time
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
        for service in ("frontend", "api", "worker", "redis"):
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

        for setting, expected in (
            ("appendonly", "yes"),
            ("appendfsync", "everysec"),
            ("maxmemory-policy", "noeviction"),
        ):
            assert compose(
                "exec", "-T", "redis", "redis-cli", "--raw", "CONFIG", "GET", setting
            ).splitlines() == [setting, expected]
        assert (
            compose(
                "exec", "-T", "redis", "redis-cli", "SET", "ataraxia:smoke", "survives"
            )
            == "OK"
        )
        print(
            "Routing, private ports, and persistence configuration passed", flush=True
        )

        compose("stop", "redis")
        assert request(base, "/api/health/ready")[0] == 503
        assert request(base, "/api/health/live")[0] == 200
        assert request(base, "/")[0] == 200
        compose("up", "--detach", "--no-deps", "--force-recreate", "redis")
        wait_ready(base)
        assert (
            compose("exec", "-T", "redis", "redis-cli", "GET", "ataraxia:smoke")
            == "survives"
        )
        compose("up", "--detach", "--wait", "--wait-timeout", "60")
        print("Redis recreation, persistence, and health recovery passed", flush=True)

        compose("up", "--detach", "--no-deps", "--force-recreate", "api", "frontend")
        wait_ready(base)
        assert request(base, "/")[0] == 200
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
