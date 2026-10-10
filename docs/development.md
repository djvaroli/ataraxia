# Local development

A01 provides a runnable shell and service boundaries. It does not yet store habits, authenticate an owner, or generate discoveries. The worker is an idle, sequential process that checks Redis connectivity; scheduling starts in A05. No Firebase, GCP, or provider configuration is needed.

## Start and stop

Run from the repository root with Docker Engine and Compose v2.20 or newer:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build --detach --wait
```

Open `http://localhost:8080`. Only nginx publishes a port, bound to `127.0.0.1`. The API, frontend, worker, and Redis communicate through this project's private Compose network. Local HTTP is sufficient for A01; HTTPS and remote access belong to deployment in A09.

The development override mounts frontend source and the HTML entry point into Vite, proxies its websocket through nginx, and mounts backend source into the API with reload enabled. The worker uses that source too; after worker edits run `docker compose restart worker`. Rebuild after dependency or configuration changes.

To check the compiled frontend and the backend runtime image instead:

```sh
docker compose up --build --detach --wait
```

Both modes use the same local Redis volume. Useful commands:

```sh
docker compose ps
docker compose logs --tail 100 api worker redis
curl --fail http://localhost:8080/api/health/live
curl --fail http://localhost:8080/api/health/ready
docker compose exec redis redis-cli INFO persistence
docker compose down
```

`down` preserves history in the named `redis-data` volume. `down --volumes` deletes that project's data; use it only for a deliberate local reset. Do not scale the worker beyond one instance.

## Configuration and health

Copy the root `.env.example` to `.env` only if you need different defaults. Compose reads this file for interpolation; the Python application reads explicit environment variables. Environment files are ignored by Git and excluded from image build contexts.

| Setting | Default and use |
| --- | --- |
| `ATARAXIA_HTTP_PORT` | `8080`, nginx's loopback port. Use `0` for a random available port in disposable checks. |
| `ATARAXIA_REDIS_URL` | `redis://localhost:6379/0` for a directly run Python process. Compose explicitly sets `redis://redis:6379/0` for API and worker; it never uses an ambient Redis URL. |

The Compose stack requires no host-installed Node, Python tooling, Redis, or credentials. The host Python 3 standard library is sufficient for `scripts/smoke.py`. For editor support or direct commands, backend tooling lives in `backend/pyproject.toml` and `backend/uv.lock`; frontend scripts live in `frontend/package.json` and `frontend/package-lock.json`.

Container runtime versions are Python 3.12.15, uv 0.11.16, Node 24.21.0, nginx 1.30.5, and Redis 8.10.2. All direct dependencies are exact versions and transitive dependencies are locked. TypeScript 5.9.3 satisfies both the API type generator and linter's peer requirements. Update manifests and lockfiles together, then run the checks below.

Infrastructure routes intentionally need no authentication:

| Endpoint | Result |
| --- | --- |
| `/api/health/live` | 200 while the API can serve requests, independent of Redis |
| `/api/health/ready` | 200 after a bounded Redis ping, or 503 with a generic status |

There are no `/api/v1` application routes yet. A02 will require verified owner identity for those routes. Health responses do not expose connection details, data, or credentials; API docs/schema are exported during development rather than publicly served.

Each service has a Compose healthcheck. The worker is ready when its loop has contacted Redis within 20 seconds; failed probes clear its heartbeat and stale heartbeats fail the check. SIGTERM stops the loop and closes its client. API/worker Redis probes have a three-second deadline and reconnect on subsequent attempts. nginx refreshes upstream DNS so container recreation does not require restarting the edge.

Redis has AOF persistence with `appendfsync everysec`, periodic RDB snapshots, a named volume, and a 256 MiB data limit with `noeviction`. The limit applies to Redis data, not total container memory. Capacity exhaustion fails writes instead of removing history. All services have bounded logs and restart policies. Local persistence does not cover host loss; off-host backup/restore remains A09 work before regular personal use.

## Checks and generated types

Run the same commands as CI:

```sh
bash scripts/check
python3 scripts/smoke.py
```

`scripts/check` uses the check profile in `compose.check.yaml`, a unique Compose project, and the development build stages. It runs Ruff format/lint, mypy, pytest, Prettier, ESLint, Vitest, TypeScript, and Vite. It also verifies that the committed OpenAPI snapshot and generated TypeScript types match the backend. No Redis connection is required for these unit checks.

`scripts/smoke.py` creates a different unique project, random edge port, and disposable Redis volume. It builds the runtime images, checks the frontend and API through nginx, verifies that internal service ports are not published, and checks Redis configuration. It then writes a test sentinel, stops Redis to check liveness versus readiness, recreates Redis to verify durability/reconnection, and recreates the HTTP upstreams to check nginx recovery. Cleanup runs on success or failure. It never addresses the normal `ataraxia` project's volume.

Use `python3 scripts/smoke.py --dev` to run the same checks with the development override and verify that nginx serves Vite's client and source modules. CI checks the compiled runtime; run this variant when changing the development setup.

To regenerate the frontend API contract after an endpoint/model change:

```sh
docker compose -f compose.yaml -f compose.check.yaml --profile check run --build --rm --no-deps backend-check python -m ataraxia.api.export_schema > frontend/openapi.json
docker compose -f compose.yaml -f compose.check.yaml --profile check run --build --rm --no-deps frontend-check sh -ec 'npx openapi-typescript openapi.json -o /tmp/api.generated.ts >&2; cat /tmp/api.generated.ts' > frontend/src/lib/api.generated.ts
```

Commit both contract files with the endpoint change. Domain/application directories and repository protocols will be added with their first real use cases in A02–A05; A01 avoids empty abstraction scaffolding. Product behavior and upcoming scope remain in [Delivery and operations](delivery.md) and [Architecture and data](architecture.md).
