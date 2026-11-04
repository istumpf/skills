---
name: stacked-pr-feedback
description: Triage and address review feedback across a chain of stacked PRs, fixing each issue on the PR that introduced the code and restacking the PRs above it; optionally run a local AI review first. Use when a user asks to handle reviews, comments, or a merged parent on a PR stack.
---

# Stacked PR Feedback

Handle review feedback on a stack of PRs where each PR targets the one below it.
Rebuild state from GitHub and Git every run; keep no run record. OpenSpec checks
apply only when the repository uses OpenSpec.

Branch moves, restacking, pushing, and merge sync go through `gh stack`
(`gh extension install github/gh-stack`). Always pass explicit arguments; bare
`init`, `add`, `checkout`, `view`, and `submit` open prompts. If
`gh stack view --json` exits 2 (no local stack), adopt the PR branches bottom to
top with `gh stack init --base <trunk> <branch-1> <branch-2> ...`.

Require `gh` with `headRefOid` support: run `gh pr view <pr> --json headRefOid`
before collecting. If it reports an unknown field, stop and ask the user to
upgrade `gh`; do not use an API fallback.

## Modes

- **Default (ask first):** collect, triage, show the plan, and wait for approval
  before changing code, pushing, or replying.
- **Auto:** only when the user asks for it. Apply fixes and post fix replies
  without asking. Disagreements, questions, spec conflicts, and rebase
  conflicts still wait for the user.
- **Local review:** only when the user asks for a review. Before collecting,
  start one read-only reviewer subagent per PR in parallel. This is a focused
  precision pass: check spec fit, test claims, and completion claims. Give each
  only its PR/base/head identifiers, diff and touched-file references, applicable
  agent instructions, and matching acceptance criteria. Add a short verification
  summary or decision only when it affects that PR's review. Reviewers may read
  more source as needed; omit session history, full logs, unrelated specs, and
  other layers' context. Each returns a compact JSON object with
  `findings` (items with `pr`, `path`, `line`, `body`, and expected behavior),
  `checked` (scope inspected), `executed` (commands, results, revisions), and
  `not_verified` (coverage limits). For changed tests, assess what claim each
  proves and what incorrect behavior would make it fail.
  Reviewers share the checkout, so they must not run any command that moves
  `HEAD` or edits files: read with `git show <head>:<path>` and `git diff`, and
  run tests only in their own `git worktree add --detach <tmp-dir> <head>`,
  removed afterwards.
  Save only the combined findings list to a scratch file for `--local`; retain
  coverage for the final report. Never post local findings. An empty static
  review means no findings in the inspected scope, with runtime unverified.
  For runtime-sensitive changes (dependencies, runner or build configuration),
  the orchestrator remains responsible for executable verification; reviewers
  need not duplicate it. Static review does not satisfy those checks.

Local review supplements independent review of the pushed stack (for example,
Codacy and a separate agent). Track the user's or repository's designated
reviewers and their results at the reviewed revisions. A local pass or an empty
feedback queue does not complete that independent review. If results are still
pending, report the handoff and leave its acceptance criteria unchecked.

## 1. Collect

Fetch the stack's branches (`git fetch origin`), then run:

```sh
python3 <skill-dir>/scripts/collect_feedback.py [<pr|branch>] [--local findings.json]
```

It prints the stack from trunk upward, unhandled items, each item's `owner_pr`
(the lowest PR whose own commits introduced the commented line; `null` when the
code predates the stack or has no line), a `sync` entry when the bottom PR's
parent already merged, and warnings about truncated results. Handled means a
resolved thread, or our marker reply as the latest thread comment or quoting
the item's URL. Report warnings; do not assume truncated feedback is absent.

If `merged` is set, the stack has fully merged: report that and stop. If `sync`
is set, do step 5 first.

## 2. Triage

Read each item against the current code at its PR head and, for OpenSpec, the
change's proposal, design, and spec. Classify every item:

| Class | Meaning | Action |
| --- | --- | --- |
| actionable | Correct and in scope | Fix on `owner_pr` (or the item's PR when `null`) |
| addressed | Already fixed by a newer commit | Reply citing the commit; verify, since `outdated` alone is not proof |
| disagree | Incorrect, out of scope, or conflicts with the spec as written | Draft a reasoned reply |
| spec-change | Valid, but changes required behavior | Propose an edit to the OpenSpec artifacts; do not change code until approved |
| question | Needs an answer, not code | Draft the answer |

An approving review does not clear its unresolved comments, and one comment
may hold several findings. Show the table with item URL, PR, owner PR, class,
and planned action or draft reply. In default mode, wait for approval and
apply the user's edits to the plan.

## 3. Fix, lowest PR first

For each owner PR from the bottom of the stack upward:

1. `gh stack checkout <branch>`. Batch its actionable items into one focused
   change; stay inside that PR's scope. Make only the changes in the approved
   plan. If a fix also needs a follow-up on another PR (for example, behavior
   that a later PR extends), list that follow-up in the plan; if it only
   becomes apparent while fixing, ask before committing it, even in auto mode.
2. Run the repository's required checks. Commit with a message linking the
   item URLs; follow the repository's commit conventions.
3. `gh stack rebase --upstack` to replay every PR above it. On exit 3
   (conflict), resolve only when the resolution is unambiguous, then `git add`
   and `gh stack rebase --continue`; otherwise `gh stack rebase --abort` and
   report it.
4. Rerun checks on each rebased branch. Confirm each PR still shows only its
   own changes: `git diff --stat <base>...<head>`.

Then `gh stack top` and `gh stack push`. Never push commits you have not
inspected.

For OpenSpec, reopen tasks whose acceptance criteria are unmet or unverified,
rather than reopening tasks merely because review changed their code. Run
`openspec validate <change> --type change --strict --no-interactive` after
editing artifacts. Correct checkmarks with missing or stale evidence.
Record criterion references, results, revisions, and relevant
environment in the existing task file or ledger. Reassess evidence after fixes
and restacking; rerun affected checks. CI required on the final published head
must match that SHA; evidence-only edits need not invalidate code checks.

## 4. Reply

End every reply with the marker line `<!-- stacked-pr-feedback -->`; it is how
later runs recognize handled items.

- Thread items: reply in the thread with
  `gh api repos/<owner>/<repo>/pulls/<pr>/comments/<reply_to>/replies -f body=...`.
- Review and comment items: post a PR comment whose body includes the line
  `in-reply-to: <item url>`.
- Local items: no reply; include them in the final report.

Fixed items cite the commit SHA. Do not resolve threads, approve, or dismiss
reviews unless the user asks or the repository's convention requires it.

## 5. Sync after a merge

When the collector reports a merged parent, run `gh stack sync`. It fetches,
replays the remaining layers onto the merge target (squash merges included),
pushes, and refreshes PR bases. If it prints `Sync aborted` because local and
remote diverged, report both chains and stop. Rerun checks and verify diffs as
in step 3.

## Finish

Report per PR: items fixed (with commits), replies posted, items awaiting the
user, restacked branches, checks run, review coverage and limits, and anything
left unhandled. Reconcile fixes, required checks, and acceptance evidence at
the final revisions before claiming completion. Report feedback handled,
acceptance satisfied, and readiness separately: a marker reply or empty review
does not prove acceptance. Include independent review status after push.
Name unmet criteria and blockers. Never report the
queue clear while actionable items remain. Do not merge PRs.
