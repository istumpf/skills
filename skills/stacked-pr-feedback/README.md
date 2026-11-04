# Stacked PR Feedback

Handle review feedback on a chain of stacked PRs. The agent collects unhandled
comments from every PR in the stack, sorts each into fix, already addressed,
disagree, spec change, or question, and shows you the plan. Approved fixes land
on the PR that introduced the code, and every PR above it is restacked. Each
item then gets a reply on GitHub.

It needs Git, an authenticated `gh`, and GitHub's
[`gh stack`](https://github.com/github/gh-stack) extension, which does the
restacking, pushing, and post-merge sync. Stacks not created with `gh stack` are
adopted first. In an OpenSpec repository it also checks feedback against the
change's spec and proposes spec edits instead of silently changing required
behavior. [OpenSpec Stack Apply](../openspec-stack-apply/README.md) runs it in
review mode after publishing.

Your `gh` must support `gh pr view --json headRefOid`. If the field is
unavailable, upgrade using the [official installation instructions](https://github.com/cli/cli#installation).
The skill checks this before collecting; it does not use an API fallback.

## Usage

From a checkout of the repository, on any branch in the stack:

```text
/stacked-pr-feedback
/stacked-pr-feedback 42
/stacked-pr-feedback review the stack first
/stacked-pr-feedback auto
```

| Request | Behavior |
| --- | --- |
| Default | Collect and triage, then wait for your approval before changing code, pushing, or replying |
| `auto` | Apply fixes and post fix replies without asking; disagreements, questions, spec changes, and rebase conflicts still wait for you |
| `review` | First run local AI reviewers in parallel (one for a small stack, else one per PR) that check each acceptance criterion has a test that would catch a naive implementation, and triage its findings with GitHub feedback; findings are never posted |

Use `$stacked-pr-feedback` in Codex.

## How it stays consistent across runs

There is no run record. Every run rebuilds the stack from PR base/head links,
and treats an item as handled when its thread is resolved or the latest reply
carries the hidden marker `<!-- stacked-pr-feedback -->`. Running it again only
shows new feedback, so it is safe to rerun after a teammate replies, or on a
schedule with `/loop`.

The collector also reports when the bottom PR's parent has merged; the agent
then runs `gh stack sync`, which rebases the remaining PRs onto the trunk and
covers squash merges.

## Boundaries

- It never merges PRs, approves, dismisses reviews, or resolves threads unless
  you ask.
- It pushes through `gh stack push`, and stops on rebase conflicts it cannot
  resolve unambiguously.
- A review fix does not reopen OpenSpec tasks unless their acceptance criteria
  are no longer met.
- The collector reads up to 100 reviews, comments, and threads per PR and 50
  comments per thread; it warns when a PR has more.

## Installation

See the [repository README](../../README.md#installation). Copies must include
the `scripts/` directory.

## Files

- [SKILL.md](SKILL.md): instructions loaded by the agent.
- [scripts/collect_feedback.py](scripts/collect_feedback.py): collects the
  stack, unhandled feedback, owning PRs, and merge status as JSON.

Offline tests: `python3 -m unittest tests.test_stacked_pr_feedback -v` from the
repository root.

[Back to the skill index](../../README.md) · [MIT license](../../LICENSE)
