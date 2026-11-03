# Ataraxia agent guide

Build a reliable personal app. Favor readable code, short docs, and small complete
increments. [README](README.md) describes what runs; [roadmap](docs/roadmap.md) owns
status; [delivery](docs/delivery.md) defines acceptance. Read only the design needed
for the current task. Verify Git/PR state before trusting a handoff.

## Code

- Use composition and small modules with explicit responsibilities. Keep domain
  rules separate from HTTP, Redis, Firebase, and LLM adapters.
- Inject side-effecting dependencies at the composition root. Define narrow Python
  protocols/TypeScript interfaces where behavior crosses a boundary; implement them
  with real adapters and simple fakes. Avoid service locators and global mutable state.
- Keep type signatures precise. Validate external inputs; avoid `Any`, broad casts,
  nullable catch-all models, and suppression comments that hide a design problem.
- Prefer clear names and direct control flow. Reuse an existing mechanism before
  adding one. Introduce abstractions for actual responsibilities, not hypothetical
  providers or a class/interface pair for every function.
- Make writes atomic and retries idempotent where required. Keep external calls
  bounded, failures explicit, and logs free of credentials and personal content.
- Reusable operations belong in small tools humans and agents can both run: typed
  functions plus a thin CLI, `--help`, explicit inputs/outputs, useful exit codes,
  and safe defaults. Add dry-run only for tools with meaningful mutations.

## Tests and documentation

- Unit tests are fast and deterministic: no network, Docker, real Redis/Firebase,
  provider calls, or wall-clock sleeps. Use fakes at I/O boundaries and test observable
  rules, failure paths, and important invariants. Keep a few separate integration checks.
- Use `bash scripts/check` for formatting, lint, strict types, unit tests, build,
  and API contract drift. Use `python3 scripts/smoke.py` for runtime/routing/storage
  changes; add `--dev` when the development setup changes.
- Update schema snapshots and generated clients with API changes. Keep dependency
  manifests and locks together. Never weaken checks to make a PR pass.
- Update the existing doc when behavior or a material decision changes. Explain
  non-obvious contracts and reasons; avoid restating code, status essays, and routine ADRs.

## Delivery and review

- Use `codex/` branches and isolated worktrees when work overlaps. Keep each PR
  runnable and coherent, with its actual stack base, checks, and a short test recipe.
- Follow [the agent delivery loop](docs/agent-workflow.md). Run independent code
  review for implementation changes, security review for trust/data/execution changes,
  and design review for consequential design decisions. Use the shared review skills
  and delegate reviewers with fresh context when available; disclose a fallback.
- Reassess findings, then fix justified in-scope recommendations without asking the
  user to adjudicate each one. Validate the result. File actionable deferred work as
  GitHub issues with evidence and a trigger; search for duplicates first. Explain
  refuted or accepted findings briefly. Do not quietly defer security vulnerabilities.
- Optimize for the owner's use: correctness, security, clear design, and usable mobile
  flows. Dedicated screen-reader audits/polish, compliance work, broad compatibility,
  and production-scale infrastructure are outside automatic remediation. Preserve
  simple semantic controls and keyboard usability without expanding the task.
- Stop at the finished PR stack for the user's review, merge, and application trial.
  Do not merge, deploy, spend on providers, or provision cloud resources without the
  corresponding authorization. Keep Ataraxia resources separate from other projects.
- Use `ataraxia-handoff` / `ataraxia-resume` for this repo's `.HANDOFF.md` and
  `.handoff/` format. The global workstream skills remain available for other projects.
