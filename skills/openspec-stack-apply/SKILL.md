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
   Require `gh` with `headRefOid` support for the feedback collector: run
   `gh pr view --json headRefOid` on an existing PR. If it reports an unknown
   field, stop and ask the user to upgrade `gh`; do not use an API fallback.
   With several remotes, pass `--remote <name>` or ensure `remote.pushDefault`.
4. Require a clean working tree. Never stash, reset, or discard user changes to
   get one; ask instead.
5. Resume: if `gh stack view --json` succeeds on a branch of this change,
   continue from its top branch and the first unchecked task. Do not recreate
   layers that exist.

Each top-level task section is one group, in written order. Skip fully checked
groups. Name branches `<change>/<n>-<group-slug>`.

## Completion gate

Before implementing a group, map each task's acceptance criteria from tasks,
spec, and design to a verification method. Keep compact references and results
in the existing task file or acceptance ledger: criterion, command or evidence
link, result, revision, and relevant environment. Reuse evidence rather than
copying specs or logs. Record missing evidence and blockers explicitly.

Check a task only when every applicable criterion has supporting evidence.
Passing repository checks proves only what those checks exercise. Tasks requiring
publication, CI, measurements, or independent review stay unchecked until that
evidence exists; proceed to later groups when their prerequisites permit it.
On resume, verify evidence for checked tasks before skipping their groups.

After fixes, rebases, or dependency changes, rerun affected checks and explain
any evidence retained. Code checks may remain valid after evidence-only edits;
requirements for CI on the final published head need results for that exact SHA.

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
4. Apply the completion gate and mark only proven tasks `- [x]` in the tasks
   file (when it is in this repository). Commit with the code, following
   repository commit conventions.

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
   its default approval flow. This focused precision pass supplements independent
   review after push by the user's or repository's designated reviewers (for
   example, Codacy and a separate agent). If the skill is not installed, report
   the local pass skipped. Record independent review results and reviewed
   revisions separately; pending results remain an explicit handoff, with review
   tasks unchecked. Local review does not satisfy this gate.
4. After review fixes and restacking, reconcile every task and checked marker
   against current evidence, required checks, and outstanding findings. Correct
   unsupported checkmarks and record deferred task completion on its owning
   layer. Repeat affected verification after restacking. Keep implementation,
   audit results, and external scanner or CI status separate.
5. Request readiness approval only when required checks and independent review
   after push are complete for the current stack and blocking findings are
   addressed. When the user
   approves, mark the PRs ready with `gh stack submit --auto --open`.

## Report

List PRs bottom to top with branches, checks run, review outcome, and anything
left open. Leave the top branch checked out. Do not merge PRs or archive the
change; the request to apply with stacked PRs authorizes branches, commits,
pushes, and draft PRs, nothing more.
Distinguish draft stack delivered, acceptance complete, and ready for approval.
For incomplete acceptance, name the unmet criteria and blockers; publishing
drafts or finishing the session does not make the change complete.
