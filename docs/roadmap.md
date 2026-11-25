# Ataraxia roadmap

The goal is a private, mobile-first learning app: one Claude-written lesson a day,
with follow-ups, a Library, and a complete activity record. Product rules live in
[product](product.md); acceptance lives in [delivery](delivery.md). This file tracks
outcomes.

On 24 November 2026 the owner moved lessons ahead of habits. Habit items A02–A09 are
superseded by the L-series below; the habit design remains in Git history for later.

Status, 25 November 2026: L01–L05 are merged (stacks #16 and #19). The app runs
locally in Docker with real Claude lessons once the worker is logged in. Next: the
owner tries it and gives feedback; then L06 (VM, Tailscale, Firebase, backups).

| Item | Outcome | Depends on | State |
| --- | --- | --- | --- |
| A01 | App shell, API, worker, and storage run locally in Docker | — | Done: [#9](https://github.com/djvaroli/ataraxia/pull/9) |
| Workflow | Repo standards and the review/fix delivery loop | A01 | Done: [#11](https://github.com/djvaroli/ataraxia/pull/11), [#12](https://github.com/djvaroli/ataraxia/pull/12) |
| L01 | Lessons-first product, architecture, and deployment plan | — | Done: [#14](https://github.com/djvaroli/ataraxia/pull/14) |
| L02 | SQLite storage replaces Redis; migrations; health and smoke checks updated | L01 | Done: [#15](https://github.com/djvaroli/ataraxia/pull/15) |
| L03 | Owner sign-in (Firebase and local modes), settings, lessons API, activity record, progress, export and backup tools, worker loop with a fake generator | L02 | Done: [#17](https://github.com/djvaroli/ataraxia/pull/17) |
| L04 | Lessons written through the Claude CLI (prompts, error mapping, pinned CLI in the worker image, login) and Wikipedia images | L03 | Done: [#18](https://github.com/djvaroli/ataraxia/pull/18); real lessons verified |
| L05 | Reading-room frontend: Today, reader, follow-ups, Library, Progress, Settings, sign-in | L03 (contract) | Done: [#20](https://github.com/djvaroli/ataraxia/pull/20); browser flow verified on the real stack |
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
