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
- **Auto:** when explicitly requested by the user or an authorized calling
  workflow, investigate and fix confirmed in-scope defects, missing validation,
  and behavior-preserving contract inconsistencies without another approval.
  Verify fixes and post evidence-backed replies. Stop for genuinely unresolved
  product decisions, changes to approved requirements, authorization boundaries,
  or conflicts that cannot be resolved safely. Reviewer disagreement alone
  does not constitute a missing owner decision.
- **Local review:** only when the user or a calling skill asks for a review.
  Before collecting, start read-only reviewer subagents in parallel: one for the
  whole stack when its diff against trunk is under about 400 changed lines,
  otherwise one per PR. Give each only its PR/base/head identifiers, diff and
  touched-file references, applicable agent instructions, and the acceptance
  criteria for its PRs (the caller's criteria map when given, else the matching
  spec and design passages). Omit session history, logs, and other PRs'
  context. Each answers, in order, then reports anything else it finds:
  1. Does every criterion have a test that goes red on the naive
     implementation? Name the criterion and the shortcut that would pass.
  2. Does any cross-PR criterion break where one layer extends another?
  3. Does any change fall outside its PR's scope?

  Reviewers share the checkout, so they read with `git show <head>:<path>` and
  `git diff` and run nothing that moves `HEAD` or edits files. Checks already
  ran; a reviewer runs code only to confirm a specific suspected finding, in
  its own `git worktree add --detach <tmp-dir> <head>`, removed afterwards.
  Each returns compact JSON: `findings` (items with `pr`, `path`, `line`,
  `body`, and expected behavior), `checked` (scope inspected), `executed`
  (commands, results, revisions), and `not_verified` (coverage limits).
  Save only the combined findings list to a scratch file for `--local`; retain
  coverage for the final report. Never post local findings. An empty review
  means no findings in the inspected scope, with runtime unverified.

Report repository-required review and CI status at the heads actually checked.
An empty feedback queue is not proof that an external review has run. Keep tasks
that explicitly require external results unchecked while those results are
pending; this skill adds no independent-review requirement.

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

For findings supplied by the user from an external web review, or retrieved
from a review service without a GitHub comment, create a scratch findings list for
`--local`. Include the PR, path, line when known, body, and source identifier.
This imports existing feedback without starting local reviewers. Attribute each
finding to its owning layer from the diff; ask only if the PR or intended
behavior cannot be determined. Report dispositions of these items to the user;
there is no GitHub thread to reply to.

If `merged` is set, the stack has fully merged: report that and stop. If `sync`
is set, do step 5 first.

## 2. Triage

Read each finding against the current code at its PR head, relevant tests,
approved requirements, and repository instructions. Trace affected execution
paths and lifecycles rather than relying on a changed file or design note alone.
Distinguish normative requirements from explanatory implementation plans.
Approved requirements are the repository's active normative contracts and,
within its own scope, the assigned change's approved requirements, following
repository precedence. A pending change does not authorize altering unrelated
existing behavior. Escalate missing, conflicting, or ambiguous requirements.

| Class | Meaning | Action |
| --- | --- | --- |
| actionable | Confirmed defect, broken invariant, or missing validation within approved behavior | Fix on `owner_pr` (or the item's PR when `null`); add regression coverage when relevant |
| addressed | Already fixed by a newer commit | Verify the current head and reply with commit and evidence; `outdated` is not proof |
| contract-consistency | Implementation or documentation contradicts an approved invariant without requiring new behavior | Restore that invariant and align documentation within repository change boundaries |
| disagree | Demonstrably incorrect, duplicate, or outside authorized scope | Explain with code paths, tests, or authoritative requirements; a design citation alone is insufficient |
| spec-change | Requires new or changed product behavior, policy, public contract, or numerical values | Explain alternatives and consequences; obtain approval before changing behavior |
| question | An answer missing from all authoritative context | Answer from evidence where possible; escalate only the unresolved choice |

A design document's silence about a safeguard does not forbid it. Fix
demonstrated lifecycle, integrity, or failure-handling gaps needed to uphold
approved behavior without asking the owner to approve the same behavior again.
Do not introduce new user-visible behavior, policy, or numerical tuning as a
correctness fix. When authoritative requirements genuinely conflict, identify
the exact clauses and request a decision. "The design says otherwise" without
technical evidence does not justify dismissing a reproduced defect.

An approving review does not clear unresolved comments; a single comment may
contain multiple findings. Show each item's URL, PR, owner PR, class, and
planned action or draft reply. In default mode, await approval and apply the
user's edits. In auto mode, complete independent authorized fixes even if
another item requires an owner decision.

## 3. Fix, lowest PR first

For each owner PR from the bottom of the stack upward:

1. `gh stack checkout <branch>`. Batch actionable and contract-consistency
   findings into focused changes on their owning layers. Respect the approved
   plan (or authorized auto scope) and coordinate fixes across layers. In auto
   mode, complete follow-ups needed to restore approved behavior; escalate
   only genuine new requirements, authorization boundaries, or unsafe conflicts.
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

Inspect applicable validation results at the actual revised head. A green
general CI job does not replace explicitly required strict validation. Check
exit codes and diagnostics and fix behavior-neutral documentation errors
within authorized scope. When repository policy forbids spec editing in an
implementation PR, use a separate documentation-only PR only when creating
PRs is explicitly authorized; auto mode alone does not authorize it. Preserve completed tasks and approved requirements
under repository rules. If a separate revision is unauthorized, report the
specific restriction and proposed fix instead of silently leaving it failing.

For OpenSpec, reopen tasks whose acceptance criteria are unmet or unverified,
not tasks whose code merely changed. Keep `evidence:` lines current when
their tests change. Run
`openspec validate <change> --type change --strict --no-interactive` after
editing artifacts, and record the actual result.

## 4. Reply

End every reply with the marker line `<!-- stacked-pr-feedback -->`; it is how
later runs recognize handled items.

- Thread items: reply in the thread with
  `gh api repos/<owner>/<repo>/pulls/<pr>/comments/<reply_to>/replies -f body=...`.
- Review and comment items: post a PR comment whose body includes the line
  `in-reply-to: <item url>`.
- Local items: no reply; include them in the final report.

Fixed items cite the commit SHA and verification performed. For disagreements,
give concrete reasons using current code, tests, and authoritative requirements;
an unsupported "not changing" is not a resolution. Never post a handled marker
for an unverified fix. Do not resolve threads, approve, or dismiss reviews
unless requested or required by repository policy.

## 5. Sync after a merge

When the collector reports a merged parent, run `gh stack sync`. It fetches,
replays the remaining layers onto the merge target (squash merges included),
pushes, and refreshes PR bases. If it prints `Sync aborted` because local and
remote diverged, report both chains and stop. Rerun checks and verify diffs as
in step 3.

## Finish

Report per PR: items fixed (with commits), replies posted, items awaiting the
user, restacked branches, checks run, review coverage and limits, independent
review status, and unmet criteria. Report feedback handled, acceptance
satisfied, and readiness separately; a marker reply or empty review does not
prove acceptance. Report the queue clear only when actionable and
contract-consistency findings are verified and remaining decisions or external
blockers are identified.
A response containing only refusals or pending questions is not completed
feedback handling while independent fixes remain.
Do not merge PRs.
