---
name: ataraxia-handoff
description: Save an Ataraxia workstream for a fresh session in a local .HANDOFF, preserving earlier checkpoints in .handoff/. Use when asked to hand off, save session context, or prepare to resume later.
---

# Ataraxia handoff

Read [Session continuity](../../../docs/session-continuity.md) for the shared record
format, history procedure, and Ataraxia scope. Follow applicable `AGENTS.md` files
when present.

## Establish the checkpoint

Confirm the current repository and worktree with `pwd`, `git rev-parse
--show-toplevel`, `git status --short --branch`, and `git worktree list`. Use this
worktree's `.HANDOFF` unless the user selected another reading source. Resolve a
material repository or workstream mismatch before writing.

Read the current brief and relevant history. Reconcile them with this session,
unfinished edits, Git history, and relevant issues/PRs. For an active stack, check
actual PR bases and merge status rather than relying on remembered order. Record
unavailable remote evidence explicitly.

Capture the overall objective, completed outcomes, remaining work, decisions,
verification evidence, and the next useful increment. Distinguish designed,
implemented, tested, and merged work. Preserve unresolved user questions and an
explicit review boundary. Reuse existing test evidence; do not run tests merely to
write a checkpoint.

## Save the record

Prepare a concise replacement brief using the shared format. Keep the first next
action concrete and link only the reading needed for that action. Preserve existing
scope and explain material changes to the plan. If a routine implementation choice
remains open, label a reasonable default rather than creating an approval gate.

Use the shared history procedure to archive the previous brief unchanged and replace
the current brief. Read the saved file back and verify its local references.
Keep useful evidence in the brief or history instead of depending on temporary files.

Handoff saves context only. Do not commit, stash, discard changes, publish a PR,
merge, provision cloud resources, or start the next implementation step as part of
this skill unless the user separately requested that action.

## Report

Report the local handoff path, checkpoint, next action, and any actual blocker.
State that the records belong to this worktree and are not included in a clone.
Give the fresh-session invocation `$ataraxia-resume` from this worktree.
