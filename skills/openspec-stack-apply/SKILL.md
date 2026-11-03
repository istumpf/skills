---
name: openspec-stack-apply
description: Apply an OpenSpec change top to bottom in one session, building one gh stack layer per task group, then publish the stack as draft PRs and review it with stacked-pr-feedback. Use when the user wants an OpenSpec change implemented as stacked PRs.
---

# OpenSpec Stack Apply

Implement an OpenSpec change yourself, in order, with each task group on its own
`gh stack` branch. Build the stack while implementing; never implement on one
branch and split it afterwards. Do not delegate implementation to subagents.

## Before starting

1. Select the change: the named one, an unambiguous one from context, or the
   sole active change in `openspec list --json`; otherwise ask.
2. Run `openspec status --change "<change>" --json` and
   `openspec instructions apply --change "<change>" --json`. Read every
   `contextFiles` path and the repository's agent instructions and required
   checks. If apply is blocked, report the prerequisite and stop.
3. Check tools: `gh auth status`, `gh stack --version` (else ask the user to run
   `gh extension install github/gh-stack`), and `git config rerere.enabled true`.
   With several remotes, pass `--remote <name>` or ensure `remote.pushDefault`.
4. Require a clean working tree. Never stash, reset, or discard user changes to
   get one; ask instead.
5. Resume: if `gh stack view --json` succeeds on a branch of this change,
   continue from its top branch and the first unchecked task. Do not recreate
   layers that exist.

Each top-level task section is one group, in written order. Skip fully checked
groups. Name branches `<change>/<n>-<group-slug>`.

## Group loop

For each pending group:

1. Create its layer from the trunk or the layer below:
   `gh stack init --base <trunk> <branch>` for the first, `gh stack add <branch>`
   after that. Always pass branch names; bare `init`/`add` open prompts.
   Exit 9 means Stacked PRs are not enabled on the repository: stop and tell
   the user.
2. Implement only this group's tasks. Write tests for its behavior, including
   edge cases stated in the spec and design prose, not only the scenarios. Use
   a `tdd` skill when one is available.
3. Run the required checks for the whole stack so far. Fix failures here.
4. Mark the group's tasks `- [x]` in the tasks file (when it is in this
   repository) and commit them with the code, following repository commit
   conventions.

If a later group exposes a defect in an earlier layer, fix it on the layer that
owns it: `gh stack checkout <branch>`, commit, `gh stack rebase --upstack`,
rerun checks, then `gh stack top`. Never commit a lower layer's concern on the
current branch. On exit 3 (conflict), resolve, `git add`, and
`gh stack rebase --continue`, or `--abort` and ask the user.

Pause and ask when a task is unclear or the implementation contradicts the
spec; suggest an artifact edit instead of guessing.

## Publish and review

1. Run all repository checks and
   `openspec validate "<change>" --type change --strict --no-interactive`.
   Confirm each layer shows only its group: `git diff --stat <parent>...<branch>`.
2. `gh stack submit --auto` pushes every layer and opens **draft** PRs. Then
   rename each PR with `gh pr edit` to the group name and a summary, noting it
   depends on the PR below.
3. Run the `stacked-pr-feedback` skill in review mode on the stack, following
   its default approval flow. If it is not installed, say so and skip.
4. When the user approves, mark the PRs ready with `gh stack submit --auto --open`.

## Report

List PRs bottom to top with branches, checks run, review outcome, and anything
left open. Leave the top branch checked out. Do not merge PRs or archive the
change; the request to apply with stacked PRs authorizes branches, commits,
pushes, and draft PRs, nothing more.
