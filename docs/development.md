# Local development

The stack runs nginx, the frontend, the API, and the worker. The API and worker share one SQLite database on the `ataraxia-data` volume. Lessons, sign-in, and the Claude CLI arrive in L03–L05; until then the worker only records a heartbeat. No Firebase, GCP, or Claude configuration is needed yet.

## Start and stop

Run from the repository root with Docker Engine and Compose v2.20 or newer:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build --detach --wait
```

Open `http://localhost:8080`. Only nginx publishes a port, bound to `127.0.0.1`. The other services communicate through this project's private Compose network. Local HTTP is fine on your own machine; remote access is described in [deployment](deployment.md).

The development override mounts frontend source and the HTML entry point into Vite, proxies its websocket through nginx, and mounts backend source into the API with reload enabled. The worker uses that source too; after worker edits run `docker compose restart worker`. Rebuild after dependency or configuration changes.

To check the compiled frontend and the backend runtime image instead:

```sh
docker compose up --build --detach --wait
```

Both modes use the same data volume. Useful commands:

```sh
docker compose ps
docker compose logs --tail 100 api worker
curl --fail http://localhost:8080/api/health/live
curl --fail http://localhost:8080/api/health/ready
docker compose exec api python -m sqlite3 /data/ataraxia.db "PRAGMA user_version"
docker compose down
```

`down` preserves the database in the named `ataraxia-data` volume. `down --volumes` deletes it; use that only for a deliberate local reset. Do not scale the worker beyond one instance.

## Configuration and health

Copy the root `.env.example` to `.env` only if you need different defaults. Compose reads this file for interpolation; the Python application reads explicit environment variables. Environment files are ignored by Git and excluded from image build contexts.

| Setting | Default and use |
| --- | --- |
| `ATARAXIA_HTTP_PORT` | `8080`, nginx's loopback port. Use `0` for a random available port in disposable checks. |
| `ATARAXIA_DATABASE_PATH` | `data/ataraxia.db` for a directly run Python process. Compose sets `/data/ataraxia.db` on the `ataraxia-data` volume. |

The Compose stack requires no host-installed Node, Python tooling, or credentials. The host Python 3 standard library is sufficient for `scripts/smoke.py`. For editor support or direct commands, backend tooling lives in `backend/pyproject.toml` and `backend/uv.lock`; frontend scripts live in `frontend/package.json` and `frontend/package-lock.json`.

Container runtime versions are Python 3.12.15 (with its bundled SQLite), uv 0.11.16, Node 24.21.0, and nginx 1.30.5. All direct dependencies are exact versions and transitive dependencies are locked. TypeScript 5.9.3 satisfies both the API type generator and linter's peer requirements. Update manifests and lockfiles together, then run the checks below.

Infrastructure routes intentionally need no authentication:

| Endpoint | Result |
| --- | --- |
| `/api/health/live` | 200 while the API can serve requests, independent of storage |
| `/api/health/ready` | 200 when the database opens at the expected schema version, or 503 with a generic status |

There are no `/api/v1` application routes yet; L03 adds them behind owner identity. Health responses do not expose connection details, data, or credentials; API docs/schema are exported during development rather than publicly served.

Each service has a Compose healthcheck. The worker is ready when its loop has written its heartbeat row within 20 seconds; a failed write clears its heartbeat file and stale heartbeats fail the check. SIGTERM stops the loop. nginx refreshes upstream DNS so container recreation does not require restarting the edge.

SQLite runs in WAL mode with foreign keys and a five-second busy timeout; each operation opens a short-lived connection. Migrations are numbered, append-only, and tracked with `PRAGMA user_version`; the API and worker both apply them at startup inside one write transaction, and refuse a database newer than they understand. All services have bounded logs and restart policies. Local persistence does not cover host loss; off-host backup and restore are L06 work before regular personal use.

## Checks and generated types

Run the same commands as CI:

```sh
bash scripts/check
python3 scripts/smoke.py
```

`scripts/check` uses the check profile in `compose.check.yaml`, a unique Compose project, and the development build stages. It runs Ruff format/lint, mypy, pytest, Prettier, ESLint, Vitest, TypeScript, and Vite. It also verifies that the committed OpenAPI snapshot and generated TypeScript types match the backend. Unit tests use temporary SQLite files.

`scripts/smoke.py` creates a different unique project, random edge port, and disposable data volume. It builds the runtime images, checks the frontend and API through nginx, verifies that internal service ports are not published, and checks WAL mode and the worker heartbeat. It then writes a test sentinel, recreates the API and worker to verify durability, and recreates the HTTP upstreams to check nginx recovery. Cleanup runs on success or failure. It never addresses the normal `ataraxia` project's volume.

Use `python3 scripts/smoke.py --dev` to run the same checks with the development override and verify that nginx serves Vite's client and source modules. CI checks the compiled runtime; run this variant when changing the development setup.

To regenerate the frontend API contract after an endpoint/model change:

```sh
docker compose -f compose.yaml -f compose.check.yaml --profile check run --build --rm --no-deps backend-check python -m ataraxia.api.export_schema > frontend/openapi.json
docker compose -f compose.yaml -f compose.check.yaml --profile check run --build --rm --no-deps frontend-check sh -ec 'npx openapi-typescript openapi.json -o /tmp/api.generated.ts >&2; cat /tmp/api.generated.ts' > frontend/src/lib/api.generated.ts
```

Commit both contract files with the endpoint change. Product behavior and upcoming scope remain in [delivery](delivery.md) and [architecture](architecture.md).
