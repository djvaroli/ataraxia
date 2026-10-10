# Ataraxia handoff

## Objective

Build the independent personal habit/discovery app described in the design docs.
A01 is complete and published for review. The user requested PRs and will clone
and try the foundation on their laptop. Keep the app stopped in this worktree;
do not start A02 or merge the PR as part of publication.

## Checkpoint

- Observed: 2026-10-10 04:00 UTC.
- Worktree: `/home/danielvaroli/ataraxia`, one worktree.
- Branch: `feat/a01-runnable-foundation`, tracking its same-named origin branch.
- Commit: `a54216322a52b4a5f082f90cd02fac736aebbd09` (`feat: establish runnable Ataraxia foundation`).
  Working tree is clean; the commit is pushed.
- [PR #9 — Establish the runnable Ataraxia foundation](https://github.com/djvaroli/ataraxia/pull/9)
  is open, ready for review (not a draft), and based on `main`. It closes
  [issue #8 — A01](https://github.com/djvaroli/ataraxia/issues/8).
- Base was verified/fetched at `c4660254ca8b74c8b5c6ea92292a4743576ca8e6`.
  Local `main` is stale; fetch before choosing another branch base. A01 is not merged.
- Publication and stopping the local app were explicitly authorized by the user.
  No merge, deployment, or cloud provisioning was requested or performed.
- Ran this repository's Compose `down` without volume deletion and verified no
  normal app containers remain. Earlier temporary test projects/volumes were also
  removed. No app is running here. Build/dependency caches remain.
- No blocker. The user will perform their laptop trial; await their feedback or
  next implementation request.

## Progress and evidence

A01 includes the React/TypeScript/Vite app shell, FastAPI health endpoints, an idle
sequential worker, shared Redis construction/configuration, nginx, persistent
Redis, exact dependencies/lockfiles, generated API contracts, development and
compiled Compose modes, focused tests, CI, and setup documentation.

Only nginx publishes a loopback port. Redis uses a named volume, AOF every second,
RDB snapshots, a 256 MiB data limit, and no eviction. API readiness handles storage
failure separately from liveness; worker heartbeat and graceful shutdown are
implemented. Authentication, habits, and discovery scheduling are not implemented.

Checks on the published implementation:

- `bash scripts/check`: passed locally, including Ruff format/lint, mypy,
  5 pytest tests, Prettier, ESLint, 1 Vitest interaction test, TypeScript, Vite build,
  and generated OpenAPI/TypeScript drift checks.
- `python3 scripts/smoke.py` and `python3 scripts/smoke.py --dev`: passed locally.
  These exercised real nginx routes, private service ports, persistence settings,
  a sentinel surviving Redis recreation, readiness/liveness failure and recovery,
  HTTP upstream recreation, and Vite client/source routing for development.
- Documentation links and whitespace checks passed. This publication turn changed
  only README/delivery publication wording and linked issue #8 after those local
  checks; application code was unchanged.
- [PR CI run](https://github.com/djvaroli/ataraxia/actions/runs/38022387542)
  passed all checks, including the compiled Compose smoke test, on PR #9.
- No actual-phone/browser visual inspection, Firebase sign-in, or provider calls
  were attempted. The user is taking over the laptop trial.

Container runtimes: Python 3.12.15, uv 0.11.16, Node 24.21.0, nginx 1.30.5,
Redis 8.10.2. TypeScript 5.9.3 satisfies the current API generator/linter peers.
Use container commands: host uv could not download the pinned Python patch,
and host HTTP tests hung in the sandbox; the temporary process was stopped and
container tests passed. CI currently passes with checkout@v4; GitHub notes its
Node 20 deprecation and runs it on Node 24 (a nonblocking maintenance follow-up).

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

First check PR #9's actual merge/review state and any laptop feedback. Address any
reported foundation issue within this PR while it is open. Do not repeat already
passing checks unless changes or new evidence justify it.

On a request to continue implementation, A02 adds owner authentication and
preferences as specified in [Delivery and operations](docs/delivery.md). Verify
whether A01 has merged before choosing the next base, preserving the dependency.
Implement Firebase sign-in/sign-out, verified bearer tokens, the explicit allowed
owner UID, persistent preferences, and validated time zone, with a fake verifier
for automated tests. Dedicated live Firebase setup remains a separate setup step;
never import ambient credentials. Keep habits and generation in later increments.

## References

- [README](README.md) and [Local development](docs/development.md): laptop startup,
  configuration, health behavior, persistence, check commands, and teardown.
- [Delivery and operations](docs/delivery.md): A01 issue #8 and next A02 scope.
- [Architecture and data](docs/architecture.md) and
  [Product and experience](docs/product.md): authoritative technical/product rules.
- [Prior local checkpoint](.handoff/2026-10-10T040003Z-52f38bd8-before-publication.md): detailed A01 implementation evidence.
- [Design/skills history](.handoff/2026-10-08T174720Z-design-and-skills.md): earlier
  settled decisions; read only if needed to resolve a discrepancy.
- [Session continuity](docs/session-continuity.md): checkpoint/history procedure.

The PR body includes the branch-specific clone command. With this branch checked
out, start locally using `docker compose -f compose.yaml -f compose.dev.yaml up
--build --detach --wait`, then open `http://localhost:8080`. No cloud credentials
are needed. `docker compose down` stops it while retaining Redis data.

Use `$ataraxia-resume` from this worktree for a fresh session. This `.HANDOFF` and
its `.handoff/` history remain local and are not included in the user's clone.
