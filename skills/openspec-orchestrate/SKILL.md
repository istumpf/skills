---
name: openspec-orchestrate
description: Apply an OpenSpec change one task group at a time with a fresh worker and parent review; optionally publish and maintain one stacked PR per group.
---

# OpenSpec Orchestrate

Own scope, code review, acceptance, and optional PR publication. Delegate one
task group at a time to a fresh worker using the user's selected model; continue
that same worker for fixes. Workers must not delegate or run this skill.

## Select the run

- Accept a change and worker model in natural language, such as
  `$openspec-orchestrate <change> using worker model <model>` in Codex or
  `/openspec-orchestrate <change> using worker model <model>` in Claude Code.
  Reuse an explicit model choice from this run. If none exists, ask before
  spawning. Preserve an exact model ID and requested reasoning effort.
- The default is implementation and local review. Use stacked PR mode only when
  the user requests one PR per group or a stack of group PRs. A generic PR
  request does not select it. Preserve the mode on resume. For stacked mode,
  read [stacked PR guidance](references/stacked-prs.md) before implementation;
  read its PR feedback section when checking published PRs or handling reviews.
- Read only the active host's section of [runtime guidance](references/runtimes.md).
  Confirm that the host can select the model, spawn a fresh worker, and resume
  it for fixes. Report a missing capability; do not substitute a model or take
  over worker implementation. Keep the parent model unchanged.

## Find work and checkpoint it

1. Use the named change, an unambiguous change in context, or the sole active
   change from `openspec list --json`; ask if several remain. Discover a named
   or registered store with `openspec store list --json` and preserve its ID on
   later commands. Keep the planning store separate from the code workspace.
2. Run `openspec status --change "<change>" --json` and
   `openspec instructions apply --change "<change>" --json`, with `--store`
   when applicable. Follow the returned schema, state, paths, and dynamic
   instructions. Read every concrete `contextFiles` path and locate the task
   artifact there. Read applicable repository instructions and required checks.
   If apply is blocked, report the prerequisite. If `all_done`, first reconcile
   any pending stacked PR publication and feedback; otherwise report completion
   without inventing implementation or claiming an earlier review.
3. Treat each peer task section as a group unless the artifact defines another
   grouping. Process groups in written order, skipping checked tasks and
   preserving completed work. Resolve unclear boundaries or unmet dependencies
   before implementing affected tasks.
4. Record initial Git status and existing edits. Before each group, capture a
   baseline that distinguishes its changes from earlier groups and user work,
   including relevant staged, unstaged, and untracked files. Do not reset,
   stash, commit, or switch branches solely to make a baseline.
5. Keep a compact run record outside tracked content: change/store, workspace,
   mode/model, group/task IDs, baseline, worker ID, review and acceptance state,
   validation evidence, and stacked PR mapping and feedback cursor when used.
   Link to evidence instead of copying large diffs or logs. Update the record
   after each handoff and state transition. Announce the selected run and progress.

Use OpenSpec apply discovery, but keep acceptance with the orchestrator; never
start an unrestricted apply workflow in a worker.

## Group loop

For each pending group:

1. In stacked mode, prepare its branch from the previous published group tip.
   Spawn a fresh worker with the requested model. Give it the exact pending
   tasks, relevant spec/context paths, workspace, applicable instructions,
   existing edits to preserve, acceptance criteria, and checks. Supply only
   context needed for this group. Tell it to implement this group and report
   changed files, task coverage, checks, and concerns; it must leave task
   markers, planning artifacts, Git/PR operations, and later groups alone.
   Use the shared worktree when possible; otherwise carry the exact baseline
   into and out of an isolated workspace. Record the worker ID and verify its
   effective model when the runtime exposes it.
2. Wait for the worker to finish. Inspect actual changes against the group's
   baseline, new files, surrounding code, and relevant spec scenarios. Check
   task coverage, correctness, regressions, conventions, test coverage, scope,
   and preservation of user work. Run required checks yourself; reuse reliable
   recorded output when rerunning adds no evidence. Never claim an unrun check
   passed or require a later group's feature now.
3. Send actionable findings, with file/task references and expected behavior,
   to the same worker ID at the same model. Inspect each repair and recheck
   affected behavior. Repeat until no actionable findings remain. If progress
   stops, the worker cannot resume, or a requirement/check blocks judgment,
   record the blocker and leave the group unaccepted. A worker report, passing
   test, or fixed round count alone is not acceptance.
4. Mark only reviewed tasks complete in the authoritative artifact and record
   acceptance evidence. In stacked mode, publish this group's accepted changes
   and task markers as its single PR per [stacked PR guidance](references/stacked-prs.md).
   Track acceptance separately from publication; resume failed publication
   before the next group. Refresh the tasks and apply instructions before
   selecting the next group. Do not ask for approval between routine groups.

## Finish and resume

Review the cumulative result and run remaining repository checks plus
`openspec validate "<change>" --type change --strict --no-interactive` (with
`--store` when applicable). This validates artifacts, not code behavior.
Refresh apply status and confirm no tasks remain.

If final validation finds a defect in an accepted group, uncheck its affected
tasks, route the fix to its worker or a replacement scoped to that group, then
review and revalidate before restoring acceptance. In stacked mode, update the
owning branch/PR and propagate the fix through descendants. Do not add an
unreviewed orchestrator code patch.

On resume, reconcile the run record against files, tasks, agents, branches,
and PR state. Review unfinished work rather than trusting a prior report;
reuse the unfinished group's worker when available or record why a replacement
is needed. For stacked mode, also process new PR review feedback as described
in the reference. Published PR feedback can arrive after later groups start;
do not wait for human reviews between groups unless the user requests that gate.

Report accepted groups, validation, blockers, and remaining work. For stacked
mode, list PRs in stack order with bases, publication/check status, and
outstanding review feedback; leave the top branch checked out when possible.
The stacked request authorizes group branches, commits, pushes, and PR updates.
Neither mode authorizes merging PRs or archiving the change. Outside stacked
mode, applying alone does not authorize commits or publication.
