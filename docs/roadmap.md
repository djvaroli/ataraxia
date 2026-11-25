# Ataraxia roadmap

The goal is a private, mobile-first learning app: one Claude-written lesson a day,
with follow-ups, a Library, and a complete activity record. Product rules live in
[product](product.md); acceptance lives in [delivery](delivery.md). This file tracks
outcomes.

On 24 November 2026 the owner moved lessons ahead of habits. A01 (runnable shell) and
the agent workflow (#11, #12) are merged. Habit items A02–A09 are superseded by the
L-series below; the habit design remains in Git history for later.

| Item | Outcome | Depends on | State |
| --- | --- | --- | --- |
| A01 | App shell, API, worker, and storage run locally in Docker | — | Done: [#9](https://github.com/djvaroli/ataraxia/pull/9) |
| Workflow | Repo standards and the review/fix delivery loop | A01 | Done: [#11](https://github.com/djvaroli/ataraxia/pull/11), [#12](https://github.com/djvaroli/ataraxia/pull/12) |
| L01 | Lessons-first product, architecture, and deployment plan | — | In progress |
| L02 | SQLite storage replaces Redis; migrations; health and smoke checks updated | L01 | Planned |
| L03 | Owner sign-in (Firebase and local modes), settings, lessons API, activity record, progress, export | L02 | Planned |
| L04 | Worker prepares lessons through the Claude CLI, with schedule, limits, recovery, and Wikipedia images | L03 | Planned |
| L05 | Reading-room frontend: Today, reader, follow-ups, Library, Progress, Settings, sign-in | L03 (contract) | Planned |
| L06 | Private phone access on a VM over Tailscale, Claude login, daily off-host backup with a tested restore | L04, L05 | Planned; needs the owner's VM and Firebase project |

Later, after a few weeks of use: quizzes and spaced review, recaps from the activity
record, habit tracking, retrieval-backed lessons. See [product](product.md#later).

## Working agreement

The owner has authorized agents to commit, open PRs, and merge reviewed PRs whose
checks pass. Deploying, provisioning cloud resources, and paid provider use still need
the owner. The owner reviews by using the running app and giving feedback.

L05 can be built in parallel with L03/L04 once the API contract (OpenAPI schema and
generated types) is merged. An open PR is in review, not done; record the merged PR
before marking an item done.
