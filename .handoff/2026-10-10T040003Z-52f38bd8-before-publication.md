# Ataraxia handoff

## Objective

Build an independent, personal development app with habit tracking and five daily
discoveries (word, artwork, history, mind insight, ML paper), automatically saved
for later review. Prioritize mobile usability and maintainable, small software.

This resume completed **A01: establish the runnable project** locally. The stopping
point is a verified foundation ready for review. Authentication, habits, and content
generation remain later increments; no cloud setup was performed.

## Checkpoint

- Observed: 2026-10-10 02:07 UTC.
- Worktree: `/home/danielvaroli/ataraxia`; repository:
  [djvaroli/ataraxia](https://github.com/djvaroli/ataraxia).
- Branch: `feat/a01-runnable-foundation`, created from fetched `origin/main` at
  `c4660254ca8b74c8b5c6ea92292a4743576ca8e6`. HEAD remains that commit; A01 is
  **uncommitted working-tree work**, not merged or published.
- Four tracked files changed: `.gitignore`, `README.md`, `docs/architecture.md`,
  and `docs/delivery.md`. New files are under `backend/`, `frontend/`, `infra/`,
  `scripts/`, `.github/`, plus the three root Compose files, `.env.example`, and
  `docs/development.md`. Preserve all of these edits.
- One worktree. The branch currently tracks `origin/main`; local `main` is stale.
  Do not switch to local main as a new base without updating/verifying it.
- [Skills PR 7](https://github.com/djvaroli/ataraxia/pull/7) was verified merged into
  main, without reviews/comments. GitHub main matched the fetched base above.
  The issue list was empty. A01/A02 are backlog IDs, not GitHub issue numbers.
- No implementation commit, issue, PR, push, deployment, or cloud resource was
  created. Resume authorized local implementation; publication was not requested.
- No application/test containers or temporary Redis volumes remain. Build images
  and dependency caches remain available. No technical blocker is known.

## Progress and evidence

A01 now contains:

- React/TypeScript/Vite app shell with CSS modules/tokens, light/dark styling,
  same-origin readiness status, and a working retry control. TanStack Query owns
  the request state. No fictional habit records or sign-in flow were added.
- FastAPI process entry point and separate sequential worker entry point sharing
  configuration/Redis construction. Public health endpoints distinguish liveness
  from Redis readiness. The worker is idle until A05, with a heartbeat, bounded
  probes, reconnects, and graceful shutdown.
- nginx/frontend/API/worker/Redis Compose services; only loopback nginx is
  published. Redis has a named volume, AOF every second, RDB snapshots, a 256 MiB
  data limit, and no eviction. Healthchecks, restart policies, bounded logs, and
  nginx upstream DNS refresh are configured.
- Separate compiled-runtime and source-mounted development modes; Python/npm
  lockfiles and exact direct dependencies. Images pin Python 3.12.15, uv 0.11.16,
  Node 24.21.0, nginx 1.30.5, and Redis 8.10.2. TypeScript 5.9.3 satisfies the
  linter/type-generator peer constraints; ESLint is on supported major 10.
- A generated OpenAPI snapshot and frontend types, checked for drift. Generated
  files are excluded from Prettier so Python and JS formatting do not conflict.
- Local setup/runbook and GitHub Actions workflow using the same check commands.

Verification on this A01 working tree (2026-10-10, before this checkpoint):

- `bash scripts/check`: **passed**, exit 0. Container-based Ruff formatting/lint,
  mypy, **5 pytest tests**, Prettier, ESLint, **1 Vitest interaction test**, TypeScript,
  Vite build, and both generated API contract comparisons.
- `python3 scripts/smoke.py`: **passed**, exit 0. Real compiled frontend and API
  through nginx, private service ports, Redis persistence settings, a sentinel
  surviving Redis container recreation, readiness failure/recovery with independent
  API liveness, and HTTP upstream recreation recovery.
- `python3 scripts/smoke.py --dev`: **passed**, exit 0. The same real-stack checks
  with the development override, plus Vite client/source module routing.
- Base/development Compose configuration, shell/Python script syntax, documentation
  links, tracked/new-file whitespace, and ignore rules passed.
- Verified that temporary check/smoke containers and volumes were removed.
- GitHub-hosted CI has not run because this branch is unpublished. No real-phone
  or browser visual inspection, Firebase sign-in, or provider calls were attempted.

Useful environment findings: the sandbox made Starlette's in-process HTTP test
client hang; its temporary process was stopped and all tests passed in Docker.
The installed host uv could not download the newer pinned Python patch release;
Docker supplies it successfully. Prefer the documented container commands rather
than relying on this host's older Python/Node. No remaining workaround is required.

## Decisions and constraints

- Keep the app independent of Osmy: no configuration, credentials, cloud project,
  or external services were borrowed. Use modular code and actual dependency
  boundaries; add domain/application directories with their first real use cases.
- Firebase email/password sign-in remains settled: one account manually created
  by the owner, end-user sign-up disabled, backend token verification plus explicit
  owner UID. An unset UID must fail closed. No Google redirect/auth-helper work.
- `/api/health/live` and `/api/health/ready` are public infrastructure endpoints.
  There are no `/api/v1` application routes yet; A02 must protect those routes.
- The worker must remain a single sequential process. Bounded attempts/calls and
  publication belong to A05, live source/LLM integration to A06. No job framework,
  distributed leases, or budget ledger is needed.
- Preserve selected-weekday habits, dated completion/undo/backfill, historical
  schedules, calendar circles, consistency, and small supportive milestones.
- Daily discoveries enter stable history automatically; favorites are separate.
  Explanations must stay source-backed, with conditional paper limitations.
- Local Redis persistence is implemented. Daily GCP backups with 30-day retention
  and a successful restore remain required before regular personal use, in A09.
- Owner UID/time zone, dedicated Firebase/GCP project, provider/model and budget,
  and host/domain remain setup choices. Fakes can support A02/A05 implementation
  before live credentials are available. No resource provisioning is authorized.

## Next increment

The next implementation increment is **A02: owner authentication and preferences**
in [Delivery and operations](docs/delivery.md). First inspect and preserve the
uncommitted A01 foundation. Before choosing a new branch/base, verify whether the
user has since committed, published, or merged A01; do not lose these edits or
rebuild on the old merged skills branch. Use the latest user request for review,
publication, or continued implementation; this checkpoint adds no publication or
cloud authorization.

A02 should implement sign-in/sign-out, verified bearer tokens and an explicit
allowlisted UID, persistent owner preferences and validated time zone, with a fake
identity verifier for focused tests. Keep habits and generation separate. Live
Firebase setup and manual sign-in verification will require the dedicated project
and owner account; do not silently use ambient credentials.

## References

- [README](README.md): working startup and validation commands.
- [Local development](docs/development.md): runtime configuration, health semantics,
  persistence, generated types, compiled/development checks, and teardown.
- [Delivery and operations](docs/delivery.md): A02 scope and dependency order.
- [Architecture and data](docs/architecture.md): authentication, profile/API and
  storage boundaries; [Product and experience](docs/product.md): first-use behavior.
- [API](backend/src/ataraxia/api/main.py),
  [worker](backend/src/ataraxia/worker/__main__.py),
  [frontend shell](frontend/src/app/App.tsx), and [Compose](compose.yaml).
- [Prior checkpoint](.handoff/2026-10-10T020722Z-d8121a4d-before-a01.md) preserves the pre-A01 brief unchanged.
  [Earlier design/skills history](.handoff/2026-10-08T174720Z-design-and-skills.md)
  contains supporting decisions; read only when a discrepancy requires it.
- [Session continuity](docs/session-continuity.md): checkpoint format and history.

Use `$ataraxia-resume` from this worktree to resume. `.HANDOFF` and `.handoff/`
are local and ignored; they are not included in a clone or another worktree.
