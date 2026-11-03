# PR review feedback

Inspect reviews and comments on every PR in the stack, including general review
bodies and inline threads. A review on an earlier PR can require a repair after
later PRs exist.

Track each PR's last inspected review/comment IDs or timestamps and the status
of actionable findings in the run record. Fetch only new feedback when possible,
but reconcile unresolved threads and the current PR head on resume so missed or
edited feedback is not silently skipped. Distinguish a review decision from its
individual comments: approval does not erase an unresolved actionable comment,
and a request for changes may have several distinct findings.

Triage each finding against the current diff and spec. Record whether it is
actionable, already addressed, obsolete after a newer commit, or needs a design
decision; cite its PR/comment URL and reason. Do not treat outdated line
position alone as proof that the concern is obsolete. Batch related actionable
findings for the same group into one concise worker handoff, with expected
behavior and relevant file/line references. Do not paste the entire discussion
or full stack diff into a worker prompt.

Fix the code on the branch owning the reviewed PR, using that group's worker
when resumable or a replacement at the selected model. Review the resulting
diff and rerun affected checks before updating the same PR. A PR comment is
feedback on published work; it does not automatically revoke completed OpenSpec
tasks. Reopen only affected tasks when their acceptance criteria are no longer
met. Apply the repair and descendant propagation rules in [stacked PRs](stacked-prs.md)
before declaring the finding addressed. Verify that each PR again shows only
its group's diff.

When the PR service permits it, reply on the relevant thread with the fix commit
or a brief reason for declining the suggestion. Do not claim reviewer approval
or resolve someone else's thread on their behalf unless the repository's review
convention permits it. Record remaining feedback and any blocked decisions;
do not mark the review queue clear while actionable comments remain.
