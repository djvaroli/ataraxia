# Agent delivery loop

The owner chooses product direction, reviews the finished PR stack, merges, and
tests the app. The agent implements, verifies, reviews, fixes, and records follow-up
work. This is the delivery policy; no recurring runner is enabled by this document.

## One increment

1. Read `AGENTS.md`, the roadmap, relevant acceptance, and the current handoff.
   Verify native stack membership, remote PR bases/heads, and local changes. Continue
   an existing stack before starting another. Use a separate worktree for unrelated work.
2. Choose one authorized roadmap increment. Prefer a native GitHub stack of small,
   coherent, runnable PRs for dependent changes or an increment that benefits from separate
   reviews. Keep a small self-contained change in one PR. Use `codex/` branches;
   the first PR targets the integration branch (normally `main`), and each dependent
   PR targets its actual parent branch. Record parent links and bottom-to-top order
   in PR descriptions and the handoff. Begin with one active stack.
3. Implement behavior, focused unit tests, and concise docs together. Keep external
   services behind narrow injected contracts. Use fixtures while credentials or
   provider choices are unavailable; never let test identities authorize deployed users.
4. Run the relevant local/CI checks. Review the exact final diff with `code-review`;
   add `security-review` for auth, storage, secrets, external inputs/calls, CI, or agent
   authority. Use `design-review` for changed product/architecture decisions. Reviewers
   use fresh context and evidence, without the implementation session's conclusions.
5. Reassess findings against code and owner priorities. Apply justified in-scope fixes
   automatically, including design cleanup that prevents concrete later rework. Add
   targeted regression tests when useful. Refute false findings with evidence. File
   deferred work as a GitHub issue with the problem, impact, why later is safe, trigger,
   acceptance, and originating PR; reuse an existing issue when it covers the work.
6. Recheck affected behavior after fixes and review changed risk paths again. Finish
   when acceptance holds, relevant checks pass, and no material finding remains
   unresolved. A reviewer label alone does not justify a fix or deferral. Security
   and data-loss problems must be fixed or explicitly surfaced as blockers.
7. Open/update the PRs; register dependent PRs in a native GitHub stack. Verify its number,
   membership, and order. Include outcome, test evidence, review disposition,
   follow-up links, and a short manual trial. After a parent changes or merges,
   reconcile GitHub's stack state and restack/retarget descendants as needed. Verify
   each diff contains only its own increment. Recheck affected behavior and CI;
   preserve unrelated work and never overwrite another contributor's commits.
   Save a handoff and report the verified native stack number and PR order. Leave
   merging and application acceptance to the owner.

If review/fix cycles make no progress, capture the exact blocker instead of looping
indefinitely. After two unsuccessful attempts at the same failure, change approach
or report the unresolved condition. Ask only when a material product decision,
authorization, or missing resource prevents further useful work.

## Native GitHub stacks

Dependent branches alone do not create a GitHub stack. Use the
[stacks API](https://docs.github.com/en/rest/pulls/stacks) through `gh api`:

- Check `GET /repos/{owner}/{repo}/stacks?pull_request={pr_number}` before creating
  or retrying. Reuse the existing stack when present.
- Create with `POST /repos/{owner}/{repo}/stacks`, passing `pull_requests` as integer
  PR numbers ordered bottom to top. Each dependent base must match its parent's head.
- Extend with `POST /repos/{owner}/{repo}/stacks/{stack_number}/add`, passing only
  the new PR numbers in order.
- Verify with `GET /repos/{owner}/{repo}/stacks/{stack_number}` and each PR's `stack`
  metadata. Record the returned stack `number` separately from PR numbers and global `id`.

Use `Accept: application/vnd.github+json` and `X-GitHub-Api-Version: 2026-03-10`.
If registration is unavailable, report the blocker instead of claiming a completed stack.
The owner can [merge a contiguous group through GitHub's stack UI](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-stacked-pull-requests).
Reconcile GitHub's automatic rebasing before making local branch changes.

## Scope of automatic fixes

Prioritize a working personal app, security, data integrity, clear module boundaries,
composition, narrow interfaces/protocols, dependency injection, and precise types.
Cheap unit tests exercise behavior with simple fakes; Docker and real service checks
remain a small separate layer. Reusable scripts expose clear inputs, outputs, help,
and error behavior for both people and agents.

Dedicated screen-reader audits/polish, compliance programs, speculative abstractions,
large test frameworks, and production-scale infrastructure are outside this loop.
Do not expand routine findings into those projects. Preserve ordinary semantic HTML
and usable controls. Record a deferred issue only when it describes actionable work
with real value; do not fill the backlog with generic best-practice suggestions.

## Skills on this machine

Shared skills live in `~/.agents/skills/`: `workstream-roadmap`, `code-review`,
`design-review`, `security-review`, `workstream-handoff`, and `workstream-resume`.
Claude Code and Copilot have links in `~/.claude/skills/` and `~/.copilot/skills/`.
Codex, Cursor, and Gemini support the shared directory; installed versions and policy can
affect discovery. These are local user skills, not cloud-runner dependencies.

For this repository, prefer `ataraxia-handoff` and `ataraxia-resume`, which preserve
the established `.HANDOFF.md`/`.handoff/` records. `ataraxia-build` runs the loop for
an explicitly requested increment. Shared skill content stays outside this repo;
its source revision is recorded in each skill. Local agent discovery is documented
by [Codex](https://developers.openai.com/codex/skills),
[Claude Code](https://code.claude.com/docs/en/skills),
[Cursor](https://cursor.com/docs/skills), and
[Gemini](https://geminicli.com/docs/cli/skills/). Copilot locations are documented in
[VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills).

## Unattended execution

First validate this loop on a real increment. Then a local scheduled run can read
the same roadmap and resume the open stack, or take the next explicitly enabled
item. It must reconcile current remote state, avoid duplicate PRs/issues, use an
isolated worktree, and stop at a finished stack or a concrete blocker. Notify only
for a new ready stack, meaningful failure, or needed decision; stay quiet while
waiting for the same unmerged stack. Never merge, deploy, or provision resources.

Choose cadence, allowed roadmap scope, and a run budget before enabling recurrence.
Local scheduled tasks need the computer and app running, plus working GitHub and
Docker permissions. User-level skills are not automatically installed on remote CI
runners. See [scheduled-task documentation](https://developers.openai.com/codex/app/automations).
CI remains a deterministic merge signal; it does not itself run this agent loop.
