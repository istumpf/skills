# Optional stacked PR mode

Use only when the user requests one PR per task group. Keep the normal worker,
review, and acceptance loop. Publish exactly one PR for each group processed by
this run, including a partially completed group's remaining work. Continue to
skip previously completed groups; do not retroactively split their history
unless requested. Record the mode and mapping so resumes preserve the stack.

## Establish the stack

Identify the repository, publication remote, and target base from the user's
instructions and repository/workspace settings; otherwise discover the remote
default branch. Do not hard-code `main` for every repository. Check access and
available PR tools before implementing the first group.
Distinguish a Git remote-tracking ref such as `origin/main` from the PR base
branch name `main`; record which repository owns each head and base.

The branch/PR relationship must be:

| Group | Head branch | PR base |
| --- | --- | --- |
| First processed group | group-1 | selected repository base |
| Next group | group-2 | group-1 |
| Next group | group-3 | group-2 |

Each child branch starts at its parent's accepted, committed, published tip.
Every PR diff against its own base contains only that group's changes and
completion markers. Setting every PR's base to the repository default does
not produce the requested stack.

Before starting, inspect existing commits, staged edits, untracked files, and
the run record. Preserve user work without including unrelated changes in PRs.
If the starting branch contains unrelated commits, start the stack from the
intended base and carry only required, attributable work. Use an isolated Git
worktree when needed to preserve a dirty workspace. Never clear user changes
to make the stack clean. If required prior work is unpublished and cannot be
attributed to a group, resolve its placement before publishing a misleading diff.

Create a distinct, collision-free branch per group using repository conventions.
Reuse the current branch for the first group only if it is suitable and its PR
diff can be limited to that group. Do not rename the user's existing branch
unless explicitly asked. Do not reuse a remote branch or PR merely because its
name matches; verify ownership by this run, repository, head, base, and content.

Keep the run record outside tracked branch content. In addition to the core
fields, record repository/remote, original branch, stack base, and each group's
parent branch, head branch, accepted commit SHA, pushed SHA, PR number/URL,
and publication status. Later groups must inherit earlier accepted code and
checkboxes. Completion markers in a separate OpenSpec store stay in that store;
do not copy the store into the implementation repository merely to create a PR.

## Publish after acceptance, before the next group

The orchestrator performs these steps after its own code review passes:

1. Mark this group's tasks complete. Run repository-required formatting and
   pre-commit checks. Review any formatter changes and recheck affected behavior
   before committing. Honor commit/PR title conventions and attribution rules.
2. Stage only changes attributable to this group, including its task markers
   when they are in this repository. Inspect the staged diff and the entire
   proposed PR diff against its intended parent. Exclude scratch records and
   unrelated user work. If a repository requires staging everything, first use
   a workspace containing only the group's changes; do not publish unrelated
   files to satisfy that rule.
3. Commit the accepted result on the group's branch. One PR may contain several
   commits, including later reviewed repairs; the invariant is one PR per group.
4. Push that branch explicitly to the selected remote with an upstream. Do not
   push other branches or rely on PR creation to choose a remote or create a fork.
5. Look for an existing PR for this run's head branch before creating one. If it
   exists, verify its base and update it as needed. Otherwise create a PR with
   explicit head and base. For GitHub CLI, the command shape is:

   ```sh
   gh pr create --repo "<owner/repo>" --head "<group-branch>" \
     --base "<parent-branch>" --title "<repository-compliant-title>" \
     --body-file "<prepared-body-path>"
   ```

   Substitute the selected repository and provider's supported head syntax.
   Prefer an available service tool with equivalent capabilities. Use structured
   text or a body file to preserve multiline descriptions. Follow the user's or
   repository's preference for draft status.
6. Describe this group's concrete problem and resulting behavior, covered task
   IDs, and validation. Link its predecessor PR and state that it depends on it;
   the first PR targets the selected repository base. Include known check
   limitations. Do not describe all preceding groups as changes in this PR.
7. Read back the PR URL, head, base, and head SHA. Confirm that they match the
   recorded branch chain and accepted commit. Record publication separately
   from code acceptance. Only then create the next group's branch and worker.

A verification-only group may have just its task-completion diff. If there is
no publishable repository diff, explain the conflict with the requested PR
mapping and resolve how to represent that group; do not fabricate filler edits,
silently omit its PR, or publish unrelated work.

Failed pushes or PR creation leave a publication checkpoint to retry, not a
reason to redo accepted implementation. After an uncertain creation response,
query for the PR before retrying to avoid duplicates. If all task checkboxes
are complete on resume, finish missing publication and verification from this
record rather than stopping at OpenSpec's `all_done` state.

## Address reviews on each PR

At published-PR checkpoints and on resume, read [PR review feedback](pr-reviews.md)
and handle new reviews on each PR. Do not wait for a human review between groups
unless the user requested that gate. A later request to address reviews resumes
this stack from its run record, even if OpenSpec already reports `all_done`.

## Repair and verify the stack

For a defect in an earlier group, make the reviewed fix on that group's branch
and update its existing PR. Use its worker when resumable or a replacement
scoped to that group, with the selected model. Do not put the earlier group's
repair exclusively in the top PR or create a second PR for the same group.

Propagate the updated parent tip through descendants in order before further
implementation or final validation. By default, append fix commits and merge
the updated parent branch into each child so published history need not be
rewritten. Review conflict resolutions, preserve each child's own work and
completion markers, and rerun affected checks before pushing updated children.
Delegate any required code/conflict fixes to the owning group's worker for
review. Respect a repository's linear-history convention; if that requires a
published-history rewrite, use existing authorization or resolve that specific
requirement before rewriting. Do not force-push as an unannounced fallback.

On resume, reconcile local/remote SHAs and actual PR state before changing
anything. Do not duplicate a PR or overwrite collaborators' changes. If a
parent was merged, closed, or deleted externally, resolve the changed stack
topology and recheck the diffs before continuing; do not recreate it blindly.

After cumulative code/spec validation, verify one PR per processed group,
correct head/base relationships, pushed accepted commits, and group-only diffs.
Report required checks accurately; local acceptance is not a claim that remote
CI or human review passed. List URLs in dependency order with merge order from
the first group to the last, but do not merge them.

Leave the topmost PR's branch checked out in the user's workspace so Conductor
shows that PR. If preserving pre-existing changes prevents that checkout, keep
those changes safe and report the exact limitation instead of discarding them.

Command reference: [GitHub CLI PR creation](https://cli.github.com/manual/gh_pr_create).
