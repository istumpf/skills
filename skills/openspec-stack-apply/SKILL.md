---
name: openspec-stack-apply
description: Apply an OpenSpec change top to bottom in one session, building one gh stack layer per task group, then publish the stack as draft PRs and review it with stacked-pr-feedback. Use when the user wants an OpenSpec change implemented as stacked PRs.
---

# OpenSpec Stack Apply

Implement an OpenSpec change yourself, in order, with each task group on its own
`gh stack` branch. Build the stack while implementing, so every layer is a
tested state; never implement on one branch and split it afterwards. Implement
in this session; subagents only review.

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
   continue from its top branch and the first unchecked task, reusing existing
   layers. Run the required checks once at the top and reopen any checked task
   without an `evidence:` line.

Each top-level task section is one group, in written order. Skip fully checked
groups. Name branches `<change>/<n>-<group-slug>`.

## Criteria map

Before the first group (and again on resume), read the proposal, design, and
specs once and write the criteria map in your working notes: one numbered line
per rule (`C1`, `C2`, ...), drawn from scenarios, spec prose, design decisions,
and proposal constraints such as existing APIs that must keep working. Tag each
with the group that owns it. Mark `cross` the rules that span groups: a later
group extending earlier behavior, or an ordering between steps. The map is done
when every rule in those artifacts has a line, not only the scenarios.

## Evidence

Evidence is a stable reference: a test id, or a command and what it shows.
Record it on an indented line under its task in the tasks file (OpenSpec does
not count it as a task):

```markdown
- [x] 2.1 Implement `line_total(...)`.
  - evidence: C4, C5 → tests/test_invoice.py::test_line_half_up
```

Keep commit SHAs out of committed files; rebases rewrite them. SHAs belong only
to evidence tied to a published head (CI runs, independent review), which goes
in PR bodies and the report.

Check a task only when every criterion it owns has evidence. Passing checks
prove only what they exercise. Tasks needing publication, CI, measurements, or
independent review stay unchecked until that evidence exists; later groups
proceed when their prerequisites permit.

## Group loop

For each pending group:

1. Create its layer from the trunk or the layer below:
   `gh stack init --base <trunk> <branch>` for the first, `gh stack add <branch>`
   after that. Always pass branch names; bare `init`/`add` open prompts.
   Exit 9 means Stacked PRs are not enabled on the repository: stop and tell
   the user.
2. Implement only this group's tasks. For each criterion it owns, and each
   `cross` criterion it touches, write a test that goes red on the naive
   implementation: the plausible shortcut that passes the scenarios but breaks
   a rule stated only in prose, or an extension that loosens an earlier
   group's rule. Use a `tdd` skill when one is available.
3. Run the required checks for the whole stack so far. Fix failures here.
4. Check proven tasks `- [x]` with their `evidence:` lines (when the tasks file
   is in this repository). Commit with the code, following repository commit
   conventions.

If a later group exposes a defect in an earlier layer, fix it on the layer that
owns it: `gh stack checkout <branch>`, commit, `gh stack rebase --upstack`,
rerun checks, then `gh stack top`. Commit each concern on the layer that owns
it. On exit 3 (conflict), resolve, `git add`, and
`gh stack rebase --continue`, or `--abort` and ask the user.

Pause and ask when a task is unclear or the implementation contradicts the
spec; suggest an artifact edit instead of guessing.

## Publish and review

1. Run all repository checks and
   `openspec validate "<change>" --type change --strict --no-interactive`.
   Confirm each layer shows only its group: `git diff --stat <parent>...<branch>`.
2. `gh stack submit --auto` pushes every layer and opens **draft** PRs. Edit
   each with `gh pr edit`: title the group name; body a summary, its dependency
   on the PR below, and one line per criterion the layer satisfies with its
   evidence. That list is the checklist reviewers work from.
3. Run the `stacked-pr-feedback` skill in review mode on the stack, following
   its default approval flow, and give it the criteria map. If it is not
   installed, report the local pass skipped. Local review is a precision pass;
   independent review of the pushed heads by the repository's designated
   reviewers (for example, Codacy or a separate agent) is still required.
4. After review fixes and restacking, reconcile: every checkmark has current
   evidence, and every open finding or pending result keeps its task unchecked.
5. Ask for readiness approval only when required checks and independent review
   are complete on the current heads and blocking findings are addressed. When
   the user approves, mark the PRs ready with `gh stack submit --auto --open`.

## Report

List PRs bottom to top with branch, checks run, local review outcome,
independent review status with the reviewed SHA, and unmet criteria and
blockers. State which holds: draft stack delivered, acceptance complete, or
ready for approval; publishing drafts does not complete acceptance. Leave the
top branch checked out. The request authorizes branches, commits, pushes, and
draft PRs only; merging PRs and archiving the change stay with the user.
