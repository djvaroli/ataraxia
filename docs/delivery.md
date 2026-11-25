# Ataraxia delivery

Acceptance for each roadmap item, the test strategy, and decisions left for setup.
Status lives in the [roadmap](roadmap.md); the delivery loop in
[agent workflow](agent-workflow.md).

## Acceptance

### L01 Lessons-first plan

The product, lessons, architecture, deployment, and roadmap documents describe the
lesson loop, the activity record, SQLite storage, the Claude CLI worker, and the
security model. Superseded habit and discovery designs are removed from current docs
(Git history keeps them).

### L02 SQLite storage foundation

Redis is removed. The API and worker open one SQLite file on the `ataraxia-data`
volume with WAL mode, foreign keys, and a busy timeout. Numbered migrations run at
startup under a lock, and the app refuses a newer schema. Readiness checks a bounded
query; the worker heartbeat reflects database contact. The smoke check proves the
database survives container recreation and that only nginx publishes a port.

### L03 Owner identity, settings, lessons API, activity

- `firebase` mode: missing/invalid/expired tokens get 401, a valid non-owner token 403,
  and missing configuration stops the API. Verified with locally signed test tokens
  and a fake key source; no network in unit tests.
- `local` mode works only when set explicitly; the runtime Compose file defaults to
  `firebase`.
- Settings validate the time zone (IANA), subjects (catalog IDs), length, and hour.
- Lesson requests and follow-ups create jobs and enforce the daily cap and waiting
  limit; the daily ensure is idempotent.
- Saved, rating, finished, flag, opened, and reading endpoints are idempotent, write
  exactly one event per real change, and bound their inputs.
- Library pagination is stable across lessons created in the same second; filters
  and search work.
- Progress returns correct streaks across time-zone day boundaries, totals, and the
  per-subject breakdown.
- Export contains every durable table; `python -m ataraxia.tools export` and `stats`
  work with `--help` and useful exit codes.
- With the fake generator selected, a requested lesson goes from queued to ready.

### L04 Claude CLI lesson generation

- The worker image installs a pinned Claude Code version; the API image does not
  contain it; only the worker mounts the login volume.
- The subprocess gets the documented flags, an empty working directory, an explicit
  environment without API-key variables, and a hard timeout.
- Errors map to the codes in [lessons](lessons.md#attempts-and-errors); attempts and
  the daily cap survive restarts; interrupted jobs recover.
- The morning lesson is created once per local day after the configured hour.
- Validation rejects out-of-range output; illustrations keep only
  `upload.wikimedia.org` images and never block publication.
- Unit tests use a fake CLI runner and fake Wikipedia client. A manual check generates
  a real lesson with the owner's login before merge and records the result.

### L05 Reading-room frontend

- Sign-in (firebase mode), local-mode notice, sign-out.
- Today shows the daily lesson in each state (none yet, waiting, preparing, ready,
  failed with a reason) and polls only while work is waiting or running.
- The reader renders Markdown, math, code, tables, and illustrations; records open,
  reading time, and scroll; offers save, rating, finish, flag, and follow-ups.
- Library filters and search; Progress streaks, totals, subjects, recent weeks;
  Settings saves and reports errors.
- Works at 360 px wide, in light and dark themes, with keyboard use and reduced
  motion. Screenshots at phone width are part of the PR.
- The runtime frontend sends a Content Security Policy and basic security headers.

### L06 Private phone access and backups

The app runs on the owner's VM, reachable only over Tailscale with HTTPS; SSH accepts
keys only; Firebase sign-in works on the phone; the worker is logged in to Claude.
A daily SQLite backup leaves the host, and a restore into an empty volume shows the
same lessons and events. See [deployment](deployment.md).

## Test strategy

| Layer | What it covers |
| --- | --- |
| Domain unit tests | Subject weighting with a seeded random generator, streaks and statistics with fixed dates and time zones, lesson content validation |
| Application unit tests | Job creation limits, worker job processing with a fake generator and fixed clock, retries and recovery, publication, event recording |
| Adapter unit tests | SQLite repositories against a temporary file; token verification with test keys; CLI result classification from recorded JSON samples; Wikipedia response parsing |
| API tests | Auth policy, validation and error mapping, a full request → worker step → read flow with fakes |
| Frontend tests | Today states, reader actions, Library filters, settings form, with a fake API |
| Smoke check | Real Compose stack with the fake generator: routing, private ports, persistence across recreation, a lesson prepared end to end |

No unit test touches the network, Docker, Firebase, or Claude. CI runs `scripts/check`
and `scripts/smoke.py`; neither needs credentials.

## Decisions left for setup

| Decision | Default | Needed by |
| --- | --- | --- |
| Firebase project and owner account | Dedicated project, email/password only, sign-up disabled | Phone use (L06); local mode works without it |
| VM provider and size | Any small Linux VM with 1–2 GB RAM | L06 |
| Private network | Tailscale with HTTPS | L06 |
| Backup destination | A private bucket or a second machine reachable over Tailscale | L06, before regular use |
| Claude model | `opus` | Can change any time in `.env` |
