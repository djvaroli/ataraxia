---
name: ataraxia-build
description: Implement an authorized Ataraxia roadmap increment through checks, independent review, automatic fixes, deferred issues, and a finished PR stack. Use when asked to build or continue an increment; not for status-only requests.
---

# Ataraxia build

Read the repository's `AGENTS.md`, `docs/roadmap.md`, `docs/agent-workflow.md`, and
the relevant acceptance in `docs/delivery.md`. Confirm the repository/worktree and
read its `.HANDOFF.md` if present. Verify facts against current files and GitHub.
Use paths relative to the selected repository, not the installed skill directory.

Implement the increment the user requested. If they asked to continue without
naming one, finish the active stack before taking the next roadmap increment.
If the stack is ready and awaiting the owner's merge, report that boundary; do not
start unrelated work. An unattended run must have explicitly configured roadmap
scope. No invocation is authority to merge, deploy, provision, or spend on providers.

Follow the delivery loop through implementation, checks, independent review,
reassessment, and fixes. Dispatch fresh reviewers under the shared `code-review`,
`design-review`, and `security-review` skills where applicable. If a shared skill
or independent reviewer is unavailable, use the repo criteria for a direct review
and disclose the limitation. Do not invent a passed independent review.

Apply justified recommendations within the increment without per-finding approval.
File actionable deferrals as GitHub issues after a duplicate search, with evidence,
impact, a concrete trigger, and acceptance. The user has authorized that workflow.
Keep screen-reader polish and speculative infrastructure outside automatic fixes.
Do not defer unresolved security or data-loss risks silently. Validate fixes and
re-review changed risk paths; stop repeated ineffective attempts with a clear blocker.

Prepare and publish the resulting PR stack under the user's implementation request,
with correct bases, merge order, checks, review dispositions, and a short manual trial.
Do not post separate review comments unless explicitly requested; findings can be
summarized in the PR body. Reconcile remote state before retrying publication so
retries do not create duplicate PRs or issues. Update the roadmap's factual status
and use `ataraxia-handoff` to save the next action and remaining owner decisions.

Return the finished stack or exact blocker. The owner reviews, merges, and tests
the app. A running background schedule is separate setup and must not be inferred
from a request to complete one increment.
