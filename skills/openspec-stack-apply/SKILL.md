---
name: openspec-stack-apply
description: Apply an OpenSpec change in one session with one tested gh stack layer per task group, publish PRs ready for review, and batch review feedback. Use when the user wants an OpenSpec change implemented as stacked PRs.
---

# OpenSpec Stack Apply

Implement the change in this session, building one tested layer per task group.
Publish the stack ready for review, handle automated review feedback, then hand the PRs to
the user for external review. Local LLM review is opt-in.

## Before starting

1. Select the named change, an unambiguous one from context, or the sole active
   change in `openspec list --json`; otherwise ask.
2. Run `openspec status --change "<change>" --json` and
   `openspec instructions apply --change "<change>" --json`. Read every
   `contextFiles` path, repository agent instructions, and required checks.
   If apply is blocked, report the prerequisite and stop.
3. Check `gh auth status` and `gh stack --version`. If the extension is missing,
   ask the user to run `gh extension install github/gh-stack`.
   Enable `git config rerere.enabled true`. With several remotes, pass
   `--remote <name>` or ensure `remote.pushDefault`.
4. Require a clean working tree; preserve user changes and ask if it is dirty.
5. Resume an existing stack with `gh stack view --json`: reuse its layers and
   continue from the first unfinished task. Check the existing stack once
   before extending it; reopen tasks whose behavior is broken or unverified.

Read the proposal, design, and specs once. Identify which group owns each rule
and which later groups extend earlier behavior. Pin preserved APIs, constants,
and formats with tests in group 1. Keep these notes brief; use the tasks file
for completion markers and PR bodies for validation details.

## Build the stack

Each top-level task section is one group, in written order. Skip completed
groups. Name branches `<change>/<n>-<group-slug>`.

For each pending group:

1. Create its layer before implementing:
   `gh stack init --base <trunk> <branch>` for the first, then
   `gh stack add <branch>`. Pass explicit branch names to avoid prompts.
   Exit 9 means Stacked PRs are unavailable: report it and stop.
2. Implement this group's tasks and test its rules, including prose constraints
   and interactions with earlier groups. Choose cases that distinguish the
   required behavior from plausible shortcuts.
3. Run the required checks for the stack so far and fix failures.
4. Mark completed tasks `- [x]` and commit code, tests, and task updates together.
   Leave tasks needing unavailable stakeholder decisions or external results
   unchecked; continue independent groups when their prerequisites permit.

If a later group exposes an earlier defect, fix it on its owning layer:
`gh stack checkout <branch>`, commit, `gh stack rebase --upstack`, rerun checks,
then `gh stack top`. On exit 3, resolve unambiguous conflicts, `git add`, and
`gh stack rebase --continue`; otherwise abort and ask. Ask about spec conflicts
rather than changing the required behavior to fit the implementation.

## Publish ready for review

1. Run repository checks and
   `openspec validate "<change>" --type change --strict --no-interactive`.
   Inspect each layer's diff against its parent to confirm it contains only its
   group's changes and remains understandable on its own.
2. Run `gh stack submit --auto --open`. This creates PRs ready for review;
   this invocation authorizes publication without another
   readiness confirmation. Merging and archiving remain with the user.
3. Use `gh pr edit` to give each PR its group title and a concise body explaining
   the behavior, dependency on the PR below, and tests/checks run. Link the
   relevant OpenSpec artifacts so an external reviewer can find the contract.

## Batch review feedback

Wait for configured automated checks and reviews on the published heads, with bounded polling (up to ten
minutes per push). A missing or pending analysis is pending, not a clean result.
If analysis cannot be retrieved, report the limitation with the published PRs.

Use `stacked-pr-feedback` in **auto** mode to collect and triage the stack's
feedback, fix confirmed in-scope defects on their owning layers, restack, check,
push, and reply in one batch. This workflow authorizes those fixes and replies.
Use its local LLM review mode only if the user requests it. If the skill is
unavailable, report feedback handling as pending.

Use the repository's configured tools for review findings not posted as GitHub
comments. Include them in the same ownership and triage process, deduplicated
by source identifier. Report their dispositions and any access limitations.
Disputed findings and spec changes wait for the user; do not suppress them to
make a check pass.

After fixes, check analysis at the new heads. Allow up to two repair batches;
then report anything still open or pending. Repository-required checks and
reviews still apply, but this workflow adds no independent-review gate.

## Handoff

List PRs bottom to top with their dependencies, checks, review findings fixed,
and outstanding decisions or results. Report review status at the heads actually
analyzed, including heads invalidated by restacking. Give the user the PR links
for their external review and leave the top branch checked out. When the user
returns review findings, use `stacked-pr-feedback` to handle them across the
stack under the authorization given in that request.
