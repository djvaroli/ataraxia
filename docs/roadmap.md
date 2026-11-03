# Ataraxia roadmap

The goal is a private, mobile-first habit tracker with a daily learning ritual and
durable history. Acceptance lives in [delivery](delivery.md); product rules live
in [product](product.md). This file tracks outcomes without copying those specs.

Status verified on 2 November 2026: A01 is merged; A02–A09 have no implementation.
The open stack is [#11](https://github.com/djvaroli/ataraxia/pull/11), the handoff
filename fix, followed by [#12](https://github.com/djvaroli/ataraxia/pull/12), the
agent workflow setup. Merge in that order; neither is part of `main` yet.

| Item | Outcome | Depends on | State |
| --- | --- | --- | --- |
| A01 | Start the app shell, API, worker, and durable Redis locally | — | Done: [#9](https://github.com/djvaroli/ataraxia/pull/9) |
| Workflow setup | Shared skills, repo standards, and a review/fix delivery loop | A01 | In review: [#12](https://github.com/djvaroli/ataraxia/pull/12) |
| A02 | Owner signs in and saves preferences | A01 | Next; implementation not started |
| A03 | Habit rules and storage preserve completion/schedule history | A02 | Planned |
| A04 | Track habits from Today and a mobile calendar | A03 | Planned |
| A05 | Stable daily discoveries and restart-safe worker using fixtures | A02 | Planned |
| A06 | Source-backed content from one bounded LLM provider | A05 | Planned; provider/budget decision needed |
| A07 | Read discoveries and revisit them in the Library | A04, A05; A06 for live acceptance | Planned |
| A08 | Export durable history and verify the whole personal workflow | A03, A07 | Planned |
| A09 | Use the app over HTTPS with tested off-host backup/restore | A08 | Planned; dedicated cloud/host setup needed |

## Next implementation increment

A02 should deliver verified owner identity, sign-in/sign-out, persistent preferences,
and time-zone validation. Implement with a fake verifier in cheap unit tests; live
Firebase setup is separate. Missing configuration must fail closed. Keep the public
health routes working. Do not add habits or content generation to this increment.

An implementation session chooses the smallest coherent PR split and runs the
[delivery loop](agent-workflow.md). Routine splits and review fixes are agent-owned;
the user reviews the resulting stack. An open PR is in review, not done. Record
the merged PR and acceptance evidence before advancing an item to done.

## Order and boundaries

Habits come first. A05 can follow A04 in one sequential workstream; splitting it
out only helps once contracts and file ownership are clear. Keep one active stack
initially so review and merging remain easy.

Backups are unnecessary during fixture-based development and required before
trusting the app with personal history. Provider choice/spending, dedicated
Firebase/GCP resources, and host/domain remain owner decisions. Dedicated
screen-reader work and production-scale infrastructure are deferred; core security,
data integrity, and readable modular code are part of every increment.
