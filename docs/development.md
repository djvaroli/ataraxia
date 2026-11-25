# Local development

The stack runs nginx, the frontend, the API, and the worker. The API and worker share one SQLite database on the `ataraxia-data` volume. The API serves the lessons API under `/api/v1`; the worker writes lessons with the Claude Code CLI (or a deterministic fake writer), and the reading-room frontend arrives in L05. The development override runs without sign-in (local mode), so no Firebase or GCP configuration is needed. Lessons need the worker to be logged in to Claude once; see below.

## Start and stop

Run from the repository root with Docker Engine and Compose v2.20 or newer:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build --detach --wait
```

Open `http://localhost:8080`. Only nginx publishes a port, bound to `127.0.0.1`. Try the API with `curl`:

```sh
curl -X POST -H 'Content-Type: application/json' -d '{"kind": "surprise"}' http://localhost:8080/api/v1/lessons/requests
curl http://localhost:8080/api/v1/today
```

### Log the worker in to Claude

The worker image contains a pinned Claude Code CLI; the login is stored on the `claude-config` volume and survives rebuilds. Once, after the first start:

```sh
docker compose exec -it worker claude auth login
```

Open the printed URL in your browser, sign in with your Claude account, and paste the code back into the terminal. `docker compose exec worker claude auth status` shows the result. This login lasts about a month; the app warns before it ends. Alternatively run `claude setup-token` on your own computer (it prints a one-year token), put it in `.env` as `CLAUDE_CODE_OAUTH_TOKEN=…`, and recreate the worker with `docker compose up -d worker`.

To try the app without Claude, start it with `ATARAXIA_GENERATOR=fake` to get sample lessons.

### Local mode

Local mode answers only requests addressed to `localhost`, `127.0.0.1`, or `[::1]` that no other proxy relayed (no Tailscale headers, one `X-Forwarded-For` entry from nginx); anything else gets 403. It relies on nginx listening on loopback, so never use it on a reachable host. The other services communicate through this project's private Compose network. Local HTTP is fine on your own machine; remote access is described in [deployment](deployment.md).

The development override mounts frontend source and the HTML entry point into Vite, proxies its websocket through nginx, and mounts backend source into the API with reload enabled. The worker uses that source too; after worker edits run `docker compose restart worker`. Rebuild after dependency or configuration changes.

To check the compiled frontend and the backend runtime image instead:

```sh
ATARAXIA_AUTH_MODE=local docker compose up --build --detach --wait
```

The runtime stack defaults to Firebase sign-in; without `ATARAXIA_AUTH_MODE=local` or the Firebase settings below, the API refuses to start and says which variables are missing.

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
| `ATARAXIA_AUTH_MODE` | `firebase` (default) or `local`. Only the development override sets `local`; never use it on the VM. |
| `ATARAXIA_OWNER_UID` | Firebase mode: the one account allowed in. Other valid accounts get 403. |
| `ATARAXIA_FIREBASE_PROJECT_ID`, `_API_KEY`, `_AUTH_DOMAIN`, `_APP_ID` | Firebase mode: the project and web app. The API verifies tokens against the project ID and serves all four to the browser through `/api/v1/client-config`; they are public by design. |
| `ATARAXIA_DEFAULT_TIME_ZONE` | `UTC`. The owner's zone until it is set in Settings; any IANA name. |
| `ATARAXIA_MAX_LESSONS_PER_DAY` | `8`. Daily cap on prepared lessons; see [lessons](lessons.md#requests-and-jobs). |
| `ATARAXIA_GENERATOR` | `claude` (worker). Writes lessons with the Claude Code CLI; `fake` writes sample lessons without Claude. |
| `ATARAXIA_CLAUDE_MODEL` | `opus`. Any model name or alias the CLI accepts. |
| `ATARAXIA_CLAUDE_TIMEOUT_SECONDS` | `600`. How long one lesson call may run before the worker stops it (30–1800). |
| `CLAUDE_CODE_OAUTH_TOKEN` | Optional one-year token from `claude setup-token`; without it the worker uses the login on the `claude-config` volume. Never use an API key: the worker strips them so lessons always use the subscription. |

The Compose stack requires no host-installed Node, Python tooling, or credentials. The host Python 3 standard library is sufficient for `scripts/smoke.py`. For editor support or direct commands, backend tooling lives in `backend/pyproject.toml` and `backend/uv.lock`; frontend scripts live in `frontend/package.json` and `frontend/package-lock.json`.

Container runtime versions are Python 3.12.15 (with its bundled SQLite), uv 0.11.16, Node 24.21.0, and nginx 1.30.5. All direct dependencies are exact versions and transitive dependencies are locked. TypeScript 5.9.3 satisfies both the API type generator and linter's peer requirements. Update manifests and lockfiles together, then run the checks below.

Infrastructure routes intentionally need no authentication:

| Endpoint | Result |
| --- | --- |
| `/api/health/live` | 200 while the API can serve requests, independent of storage |
| `/api/health/ready` | 200 when the database opens at the expected schema version, or 503 with a generic status |

Every `/api/v1` route except `client-config` requires the owner: a Firebase ID token for `ATARAXIA_OWNER_UID` in firebase mode, or a local request in local mode. Errors share one JSON shape (`error.code`, `error.message`, `error.fields`). Health responses do not expose connection details, data, or credentials; API docs/schema are exported during development rather than publicly served.

Each service has a Compose healthcheck. The worker is ready when its heartbeat thread has written the heartbeat row within 20 seconds; a failed write clears its heartbeat file and stale heartbeats fail the check. The heartbeat runs beside the job loop so a long Claude call does not mark the worker unhealthy. The job loop checks for work every 2 seconds; SIGTERM stops it, and a job interrupted mid-call is requeued (or failed) when the worker starts again. nginx refreshes upstream DNS so container recreation does not require restarting the edge.

SQLite runs in WAL mode with foreign keys and a five-second busy timeout; each operation opens a short-lived connection. Migrations are numbered, append-only, and tracked with `PRAGMA user_version`; the API and worker both apply them at startup inside one write transaction, and refuse a database newer than they understand. All services have bounded logs and restart policies. Local persistence does not cover host loss; off-host backup and restore are L06 work before regular personal use.

## Data tools

The API image includes a small command-line tool for the database named by `ATARAXIA_DATABASE_PATH`. Each subcommand has `--help`, exits 1 with a one-line message on failure, and never creates or migrates a database:

```sh
docker compose exec api python -m ataraxia.tools export --output /data/export.json   # default: stdout
docker compose exec api python -m ataraxia.tools stats
docker compose exec api python -m ataraxia.tools backup /data/backups/2026-11-24.db   # refuses to overwrite
```

`backup` uses SQLite's online backup, so it is safe while the app runs, and writes a single self-contained file.

## Checks and generated types

Run the same commands as CI:

```sh
bash scripts/check
python3 scripts/smoke.py
```

`scripts/check` uses the check profile in `compose.check.yaml`, a unique Compose project, and the development build stages. It runs Ruff format/lint, mypy, pytest, Prettier, ESLint, Vitest, TypeScript, and Vite. It also verifies that the committed OpenAPI snapshot and generated TypeScript types match the backend. Unit tests use temporary SQLite files.

`scripts/smoke.py` creates a different unique project, random edge port, and disposable data volume, and runs in local mode with the fake generator. It builds the runtime images, checks the frontend and API through nginx, requests a lesson and waits for the worker to prepare it, reads it back, confirms that a request with a non-local `Host` gets 403, verifies that internal service ports are not published, and checks WAL mode and the worker heartbeat. It then writes a test sentinel, recreates the API and worker to verify durability, and recreates the HTTP upstreams to check nginx recovery. Cleanup runs on success or failure. It never addresses the normal `ataraxia` project's volume.

Use `python3 scripts/smoke.py --dev` to run the same checks with the development override and verify that nginx serves Vite's client and source modules. CI checks the compiled runtime; run this variant when changing the development setup.

To regenerate the frontend API contract after an endpoint/model change, build each image before redirecting its output (`run --build` can print build logs to standard output), and build the frontend image after the new snapshot exists, because the image copies it:

```sh
docker compose -f compose.yaml -f compose.check.yaml --profile check build backend-check
docker compose -f compose.yaml -f compose.check.yaml --profile check run --rm --no-deps backend-check python -m ataraxia.api.export_schema > frontend/openapi.json
docker compose -f compose.yaml -f compose.check.yaml --profile check build frontend-check
docker compose -f compose.yaml -f compose.check.yaml --profile check run --rm --no-deps frontend-check sh -ec 'npx openapi-typescript openapi.json -o /tmp/api.generated.ts >&2; cat /tmp/api.generated.ts' > frontend/src/lib/api.generated.ts
```

Commit both contract files with the endpoint change. Product behavior and upcoming scope remain in [delivery](delivery.md) and [architecture](architecture.md).
