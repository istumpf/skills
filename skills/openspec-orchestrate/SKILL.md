---
name: openspec-orchestrate
description: Apply an OpenSpec change through sequential task-group delegation using a user-selected worker model. Use when the user wants a fresh subagent for each group and parent review until acceptance, optionally publishing one stacked PR per group when requested.
---

# OpenSpec Orchestrate

Act as the orchestrator and code reviewer. Delegate implementation to one worker
at a time, using the model the user selected. Keep your own model unchanged.
This workflow explicitly requests subagents; workers must not delegate further.

## Inputs and runtime

Accept a change name and worker model in natural language, for example:

- Codex: `$openspec-orchestrate <change> using worker model <model>`
- Claude Code: `/openspec-orchestrate <change> using worker model <model>`

The existing apply-and-review workflow is the default. Enable **stacked PR mode**
only when the user requests one PR per group or a stack of group PRs, for example
by appending `with one stacked PR per group`. A generic request to open a PR
does not select this mode. Preserve the selected mode when resuming a run.

In stacked PR mode, read [references/stacked-prs.md](references/stacked-prs.md)
before implementation. The user's request authorizes the orchestrator to create
group branches, commit accepted changes, push them, and create/update the group's
PR. It does not authorize merging PRs or archiving the change. Workers continue
to implement one group; the orchestrator owns Git and PR operations.

Reuse a model explicitly chosen earlier in the conversation for this run. If no
worker model was chosen, ask for it before spawning; never silently pick one.
Honor a requested reasoning effort when supported. An alias the user supplied
is valid, but do not replace an exact model ID with an alias or another model.

Read [references/runtimes.md](references/runtimes.md) for the active runtime.
Inspect the tools actually available. Confirm that you can select the requested
model, start a fresh worker, and continue that same worker for review fixes.
If a required capability or model is unavailable, explain the specific gap and
ask for the missing choice or setup. Do not silently implement the work yourself
or substitute a different model. Do not change global agent settings to run it.

## Load the OpenSpec change

1. Use the named change or an unambiguous change from conversation context. If
   neither exists, run `openspec list --json`; select the sole active change or
   ask the user to choose among multiple changes.
2. If the user names an OpenSpec store, or this work belongs to a registered
   store, discover its ID with `openspec store list --json`. Preserve
   `--store <id>` on subsequent change/spec commands. Otherwise use the local
   OpenSpec root. Preserve the implementation workspace separately from a
   store's planning location.
3. Run:

   ```sh
   openspec status --change "<change>" --json
   openspec instructions apply --change "<change>" --json
   ```

4. Respect the returned schema, `planningHome`, `changeRoot`, `actionContext`,
   state, and dynamic instructions when present. Read every concrete path in
   `contextFiles`, including arrays of paths. Locate the task artifact from
   that context instead of assuming a fixed filename or directory.
5. If apply is blocked, report the missing prerequisite. If it is already
   `all_done`, report that no pending implementation remains; do not invent work
   or claim to have reviewed earlier implementation. In stacked PR mode, first
   reconcile the run record and finish any pending publication or stack checks;
   completed checkboxes alone do not mean that the requested PRs exist.
   Otherwise read applicable repository instructions and identify the required
   validation commands.

Use the normal OpenSpec apply semantics for discovery and context. This skill
replaces the ordinary implement-and-check-off loop with the review gate below;
do not invoke an unrestricted apply workflow in a worker.

## Identify groups and preserve progress

- A task group is one peer section of the task artifact, normally a heading
  such as `## 2. API`, with its task checkboxes and subordinate headings, up to
  the next heading of the same or higher level. Use the artifact's explicit
  grouping if its schema differs. Do not turn every checkbox into a group or
  combine adjacent groups. Ask for clarification if boundaries are ambiguous.
- Process groups in their written order. Skip groups whose tasks are already
  checked; for a partially completed group, assign only the unchecked tasks
  and preserve the checked work. If an unmet dependency requires a different
  order or a spec change, resolve that before implementing dependent work.
- Record the initial Git status and existing edits. Before each group, capture
  a reviewable baseline of the current worktree, including relevant untracked
  files and staged/unstaged edits. Keep enough content or patches to distinguish
  this group's changes from earlier groups and unrelated user work. A diff
  against `HEAD` alone is insufficient when earlier groups are uncommitted.
  Do not reset, stash, commit, or change branches just to create a baseline.
- Keep a small run record in an existing ignored scratch directory (such as
  `.context/`) or a temporary directory. Record the change/store, workspace,
  mode, model/effort, group/task IDs, baseline location, worker ID, review round,
  findings, validation evidence, and acceptance state. Update it after each
  handoff and review so a resumed session can continue accurately.
- Announce the selected change, worker model, group order, and current progress.

## Implement and review each group

Repeat this sequence until every group is accepted or a genuine blocker remains.
In stacked PR mode, each accepted group must also be published before advancing.

### 1. Start a fresh worker

In stacked PR mode, prepare this group's branch from the preceding group's
published tip (or the selected base for the first group) before spawning.

Spawn a new agent with a new ID and fresh conversation for this group. Never
reuse the previous group's worker. Prefer the shared implementation worktree
so the worker sees all accepted changes, including uncommitted ones. If the
runtime requires isolation, carry that exact baseline into the worker's
workspace and bring its result back before reviewing or starting another group.

Give the worker a self-contained assignment containing:

```text
Role: implement exactly this one OpenSpec task group, then report back.
Change/store and implementation workspace: ...
Group heading and exact pending task IDs/text: ...
OpenSpec context file paths and applicable repository instructions: ...
Relevant accepted work, pre-existing edits to preserve, and constraints: ...
Required acceptance criteria and validation commands: ...

Read the context and implement only these pending tasks. Supporting code and
tests needed for this group are in scope; later groups are not. Do not run the
full apply/orchestration workflow or spawn other agents. Leave task checkboxes
and planning artifacts unchanged; the orchestrator owns acceptance. Leave
branch changes, commits, pushes, and PR operations to the orchestrator, including
in stacked PR mode. Do not archive the change.
If blocked or a task needs a design decision, report it rather than expanding
scope. On completion, report task coverage, changed files, checks with outcomes,
and any remaining concerns. Then stop and wait for review feedback.
```

Supply real values and all essential context; do not assume that the worker
inherits this conversation or the skill. Record its ID and model selection.
When the runtime exposes the effective model, check it against the request;
report any substitution instead of treating it as a successful match.

### 2. Wait and review personally

Wait for the worker to finish its turn. A running or partial worker response is
not completion. Do not advance to another group while this one is under review.

Inspect the actual file changes against the group baseline, including new
files, and read surrounding code and relevant spec scenarios. The worker's
summary is evidence to inspect, not an approval. Review:

- Coverage of each assigned task and relevant acceptance criteria.
- Correct behavior, edge cases, regressions, and compatibility with prior groups.
- Repository conventions, maintainability, and proportionate test coverage.
- Scope discipline and preservation of unrelated edits and planning artifacts.

Run the required checks for this group and inspect the results yourself. Reuse
reliable recorded output when rerunning an expensive check would add no evidence.
Do not claim an unrun or blocked check passed. Judge the group against its own
criteria; do not require a later group's feature before that group is assigned.

### 3. Request changes and repeat

If there are actionable findings, send them to the **same worker ID**, using
the runtime's continuation mechanism and the same requested model. Include
file/line or task references, expected behavior, why the current result fails,
and the validation needed. Ask it to fix only this group's findings and report
back. Do not take over the code changes yourself.

Wait, inspect the new diff, recheck affected behavior, and resolve each finding
with evidence. Repeat until you are satisfied: all assigned tasks are covered,
required checks pass, and no actionable findings remain. A worker's claim that
it is done, a passing test alone, or a review-round limit is not acceptance.

There is no fixed review-round cap. Continue while fixes make progress. If
repeated attempts make no progress, the worker cannot be resumed, required
validation is unavailable, or a missing requirement prevents a decision,
record the blocker and ask for the specific input needed. Leave the group
unaccepted and do not advance merely to bypass it. Respect explicit user stop
requests and actual runtime/resource limits.

### 4. Accept the group and move on

Only after your review passes, mark the assigned task checkboxes complete in
the authoritative task artifact. Preserve prior completion markers. Record
the acceptance rationale and validation evidence. Ensure this worker is idle;
close/release it if the runtime supports that without losing needed records.

In stacked PR mode, follow the reference's publication steps now: commit the
accepted group and its completion markers, push its branch, create or reconcile
its PR against the correct parent, and record the verified URL/head/base.
Keep acceptance and publication as separate states; if publishing fails, retain
the accepted implementation and resume publication before starting another group.

Re-read the tasks and refresh `openspec instructions apply` before choosing the
next pending group. Start a **new** worker for that group and repeat the loop
without asking for approval between routine groups.

## Finish or resume

After the last group, review the cumulative change for integration issues and
run any remaining change-level checks required by the repository or spec. Run
`openspec validate "<change>" --type change --strict --no-interactive` (with the
store flag when applicable); this validates the artifacts, not code behavior.
Refresh apply status and confirm that no tasks remain before claiming success.

If final validation reveals a defect in an accepted group, revoke acceptance
for the affected tasks, uncheck only those tasks, and route the fix through that
group's worker when resumable. Otherwise start a replacement worker scoped only
to that group at the same model and record why it replaced the earlier worker.
Review and revalidate before checking the tasks again. Do not add an unreviewed
orchestrator patch to finish the run.
In stacked PR mode, repair the owning group's branch and propagate the updated
parent through its descendants as described in the reference, then revalidate
the affected stack. Keep the existing one-PR-per-group mapping.

On resume, reconcile the run record with the current artifacts, code, and agent
state. Review unfinished changes rather than assuming a previous worker report
was accepted. Reuse an unfinished group's worker if available; if its session
is lost, record the interruption and use a replacement for that same group.

Report accepted groups/tasks, validation results, and any blocker or remaining
work. In stacked PR mode, also verify and list the PRs in stack order, their base
branches, and publication/check status; leave the topmost PR branch checked out.
Outside that mode, applying alone does not authorize committing or publishing.
Neither mode authorizes merging PRs or archiving the change.
