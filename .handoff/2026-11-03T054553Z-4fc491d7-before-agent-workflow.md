# Ataraxia handoff

## Objective

Build the independent personal habit/discovery app described in the design docs.
A01 is merged. This change tracks the current checkpoint and its history in the
repository so a new clone can resume the workstream. The user authorized a PR for
this change. A02 remains the next implementation increment.

## Checkpoint

- Observed: 2026-10-10 06:35 UTC.
- Repository: [djvaroli/ataraxia](https://github.com/djvaroli/ataraxia).
  Paths in this record are relative to the checkout root.
- Branch: `chore/track-handoff-records`, based on fetched `origin/main` at
  `1cfbc3839510615767ab44b3dd14292901b25aaf`.
  This checkpoint accompanies the handoff-tracking change; verify its current
  commit and PR status on resume.
- [PR #9 — Establish the runnable Ataraxia foundation](https://github.com/djvaroli/ataraxia/pull/9)
  merged into `main` at that base on 2026-10-10. [Issue #8 — A01](https://github.com/djvaroli/ataraxia/issues/8)
  is closed. Earlier checkpoints describing PR #9 as open are superseded.
- The current change includes `.HANDOFF`, the existing `.handoff/` history, and
  the updated ignore rules, README, session guidance, and handoff/resume skills.
  The previous brief was archived unchanged before this replacement.
- The prior session stopped the app. This change has not started services or
  changed application code. No merge, deployment, or cloud setup is part of it.

## Progress and evidence

A01 provides the React/TypeScript/Vite shell, FastAPI health endpoints, one idle
sequential worker, shared Redis configuration, nginx, persistent Redis, pinned
dependencies, generated API contracts, development/compiled Compose modes, tests,
CI, and setup documentation. Authentication, habits, and discovery scheduling
remain unimplemented.

At A01 revision `a54216322a52b4a5f082f90cd02fac736aebbd09`, the previous session
recorded passing `bash scripts/check` (including 5 pytest tests and 1 Vitest test),
compiled and development Compose smoke tests, and [PR CI](https://github.com/djvaroli/ataraxia/actions/runs/38022387542).
Those are historical application checks, not new runs for this documentation
change. No browser/phone trial, live Firebase sign-in, or provider calls were
verified. The user's laptop trial outcome is not recorded.

For the handoff-tracking change, both skills passed the skill-creator validator.
Ignore checks confirmed that records and supporting notes can be tracked while
temporary drafts and existing local configuration stay ignored. All 69 local
Markdown references passed, original records were verified byte-for-byte, and
whitespace checks passed. Application tests were not rerun for these record and
documentation changes.

## Decisions and constraints

- `.HANDOFF` and completed files in `.handoff/` belong in Git. Committed records
  travel with their branch; new edits remain local until committed. Temporary
  `.handoff/**/*.tmp` drafts are ignored. Historical records retain their original
  wording; current [session guidance](docs/session-continuity.md) supersedes old
  statements that handoffs must remain local or untracked.
- Keep Ataraxia independent of Osmy, including credentials and cloud resources.
  Preserve the small personal-app scope, modular code, focused unit tests, and a
  few Docker integration checks.
- Firebase email/password sign-in uses one manually provisioned owner account,
  disabled end-user sign-up, verified bearer tokens, and an explicit allowed UID
  that fails closed when unset. A02 must protect future `/api/v1` application
  routes; `/api/health/live` and `/api/health/ready` remain public.
- One sequential worker, bounded attempts/calls, and stable source-backed
  discoveries remain the design. Habits retain selected weekdays, dated
  completion/undo/backfill, historical schedules, and calendar circles.
- Redis persistence is implemented. Daily GCP backups with 30-day retention and
  a successful restore remain required before regular personal use, in A09.
- Owner UID/time zone, dedicated Firebase/GCP project, provider/model and budget,
  and host/domain remain setup choices. Fakes can support implementation before
  live credentials are available; no resource provisioning is authorized here.

## Next increment

Check the handoff-tracking PR's current status and any laptop feedback. Address
reported foundation issues when requested. Reuse applicable passing checks unless
new changes or evidence justify rerunning them.

On a request to continue implementation, fetch and verify the branch base, then
implement **A02: owner authentication and preferences** from
[Delivery and operations](docs/delivery.md): sign-in/sign-out, verified tokens and
allowed UID, persistent preferences, and validated time zone, with a fake verifier
for focused tests. Dedicated live Firebase setup remains a separate step. Keep
habits and content generation in their later increments.

## References

- [README](README.md) and [Local development](docs/development.md): startup,
  configuration, health behavior, persistence, checks, and teardown.
- [Delivery and operations](docs/delivery.md): A01 issue #8 and next A02 scope.
- [Architecture and data](docs/architecture.md) and
  [Product and experience](docs/product.md): technical and product decisions.
- [Previous checkpoint](.handoff/2026-10-10T063555Z-7abb768f-before-repo-tracking.md):
  original post-publication brief, preserved unchanged.
- [A01 implementation evidence](.handoff/2026-10-10T040003Z-52f38bd8-before-publication.md)
  and [design/skills history](.handoff/2026-10-08T174720Z-design-and-skills.md):
  earlier evidence and decisions, to read when needed to resolve a discrepancy.
- [Session continuity](docs/session-continuity.md): current checkpoint/history rules.

Use `$ataraxia-resume` from a checkout containing this checkpoint. Committed handoff
records are included in clones and worktrees of the branch containing them.
