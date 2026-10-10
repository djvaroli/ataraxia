# Design and session skills history

Recorded 8 October 2026. Repository paths in this record are relative to the
Ataraxia worktree root.

## User requirements and design

The user requested a personal development application independent of Osmy, initially
for one person. Habits are the priority: record whether the intended behavior was
achieved and show completion circles in a calendar. Daily learning comprises a word
with useful sentence examples, an artwork with context, a historical event, an
insight about the mind, and an interesting ML paper with a summary/full-paper link.
All categories retain browsable history. The UI must work well on mobile.

This session was explicitly for design, followed by repository skills, not app
implementation. The user wanted modular code, composition and protocols, concise
documentation, simple unit tests, and a few Docker integration checks. They proposed
Redis, nginx, FastAPI, a separate frontend, and Docker Compose. Backups should go to
a dedicated GCP project, be added later, and be ready before regular personal use.
They stressed that this is a side project and routine choices do not need repeated
approval.

The final design is in [README](README.md), [product](docs/product.md),
[architecture](docs/architecture.md), [discoveries](docs/discoveries.md), and
[delivery](docs/delivery.md). These maintained documents take precedence over this
historical summary when they change. Ataraxia is the working name from the repository.

## Review and accepted simplifications

The user explicitly requested a sub-agent design review and clarified that Firebase
should use a manually provisioned account with no sign-up. The initial Google
sign-in proposal was replaced with Firebase email/password, disabled end-user
registration, SDK-managed sessions, and backend verification of one configured UID.
The OAuth redirect/auth-helper routing is no longer part of the design.

The review also led to these changes:

- ML paper limitations are included only when the source supports them; an abstract
  alone may not provide one. Artwork cards can be shorter when only factual metadata
  is available.
- One sequential worker checks today's five slots. Durable attempts and call counts,
  timeouts, and transactional publication remain; job indexes, claims, and leases
  were removed.
- Daily call/token caps and usage logs replaced monetary reservation accounting.
- Daily GCP snapshots with 30-day retention and an initial restore drill replaced
  multiple retention classes and separate operator roles.

The sub-agent's focused follow-up found no remaining must-fix contradiction.
That review covered the design, not runtime software or the later skill definitions.
Source-backed selection, preserved history, sensible failure states, and local Redis
persistence remain part of the design. No providers or cloud resources were set up.

## Pull requests and merge history

The initial repository was empty. An empty bootstrap commit established main, then
the five documents were published in separate dependent PRs:

1. [Overview PR 1](https://github.com/djvaroli/ataraxia/pull/1)
2. [Product PR 2](https://github.com/djvaroli/ataraxia/pull/2)
3. [Architecture PR 3](https://github.com/djvaroli/ataraxia/pull/3)
4. [Discoveries PR 4](https://github.com/djvaroli/ataraxia/pull/4)
5. [Delivery PR 5](https://github.com/djvaroli/ataraxia/pull/5)

Review fixes were propagated by merge commits while keeping each PR's diff to one
document. The user created a native stack they referred to as #6 and merged it;
GitHub reported PRs 1–5 merged. Do not treat that stack ID as a PR number. The remote
main design merge was `69ef077`; stack metadata itself was not queried.

The user then requested Ataraxia versions of the handoff/resume skills in `../osmy/`
and explicitly asked not to run them yet. The Osmy skill definitions, shared
continuity document, and helper were read only. They were adapted into two smaller,
instruction-only skills with local history, actual worktree/PR verification, and
Ataraxia-specific scope. Mandatory size gates, reviewer skills, hooks, and executable
helpers were omitted. README discovery links, UI metadata, shared continuity
guidance, and ignore rules were added in seven files.

[Skills PR 7](https://github.com/djvaroli/ataraxia/pull/7) was created from main with
head `ea775cb8ac914a2a09b69f6331575ce2c460f2a4`. GitHub now reports it merged at
2026-10-08T17:45:54Z into main commit
`c4660254ca8b74c8b5c6ea92292a4743576ca8e6`. PR reviews, discussion comments, and inline
comments were empty when checked for this handoff.

The latest user message explicitly invoked `.agents/skills/ataraxia-handoff`.
That authorizes this local checkpoint; the earlier no-run request applied while
creating the skills. The resume skill has not been invoked.

## Verification evidence

Before publishing the design, local Markdown references, code fences, whitespace,
stack ancestry, and each PR's one-document diff were checked. The design revision
ended at `43b4495` before the user's merge. No app tests could run because the app
does not exist yet.

At skills revision `ea775cb`, both skills passed the bundled skill-creator
`quick_validate.py` check. UI metadata, 16 local links across the four relevant
Markdown files, whitespace, and ignore rules for `.HANDOFF`/`.handoff/` passed.
The skill workflows were not executed during creation, and no checkpoint/history
existed before this handoff. These checks are existing evidence; they were not
rerun merely to write this record. This handoff's own file/reference checks are
performed as part of saving it.

The repository remains documentation and skills only. A01–A09 are local draft
backlog IDs in the delivery document. GitHub's issue list was empty on this handoff
check; no implementation issues have been published. Temporary drafting files are
not required to continue. No application services or test containers were started.
