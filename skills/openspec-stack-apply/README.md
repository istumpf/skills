# OpenSpec Stack Apply

Implement an OpenSpec change in one session, with one small, tested PR per task
group. The agent builds layers while implementing, publishes them **ready for
review**, and handles confirmed review findings across the stack in a batch. It then gives you the PR links for human or ChatGPT web review.

The skill runs strict specification validation before implementation, escalating
unresolved decisions only for affected groups. It also performs a bounded
cross-layer self-review derived from the change's contracts and code before
publishing. That review records its scope and limits in the top PR and handoff;
a separate reviewer agent remains opt-in.

The goal is fewer manual handoffs while keeping PRs easy to review. The
[recorded evaluations](../../tests/README.md) predate this preflight and
self-review change: they did not find a correctness advantage on the larger
case and found higher costs for the stack workflow. The new review pass has
not been evaluated yet and may further increase time and model cost.

## Requirements

- An OpenSpec project with a change ready to apply, and the OpenSpec CLI.
- `gh` authenticated, plus `gh extension install github/gh-stack`. The
  repository must have GitHub Stacked PRs available; the skill stops and tells
  you if it does not.
- `gh pr view --json` must support `headRefOid` for feedback collection.
  If the field is unavailable, the skill asks you to upgrade `gh`.
- A clean working tree.
- [Stacked PR Feedback](../stacked-pr-feedback/README.md) for automatic feedback
  handling. Findings outside GitHub comments are retrieved through the
  repository's configured tools when available.

## Usage

```text
/openspec-stack-apply <change-name>
```

Use `$openspec-stack-apply` in Codex. The request authorizes creating branches,
commits, pushes, PRs ready for review, and confirmed in-scope review fixes with
replies. There is no separate readiness confirmation. The agent never merges or
archives the change. Spec conflicts and disputed findings come back to you.

| Group in `tasks.md` | Branch | PR base |
| --- | --- | --- |
| `## 1. Amount parsing` | `<change>/1-amount-parsing` | trunk |
| `## 2. Line totals` | `<change>/2-line-totals` | `<change>/1-amount-parsing` |
| `## 3. Coupons` | `<change>/3-coupons` | `<change>/2-line-totals` |

If a later group exposes a bug in an earlier layer, the fix is committed on that
layer and the layers above are rebased with `gh stack rebase --upstack`. Rerun
the command to resume: it continues from the existing stack and the first
unfinished task. Task markers record completion; PR bodies record validation.

Configured automated checks and reviews are checked on the published heads, with up to ten minutes of
waiting per push and two repair batches. Anything still pending is reported.
Once you finish your external review, bring its findings back with
`/stacked-pr-feedback auto` to have the agent apply confirmed fixes across the
stack, or omit `auto` to approve its plan first.

## Installation

Install it together with `stacked-pr-feedback` as described in the
[repository README](../../README.md#installation).

## Files

- [SKILL.md](SKILL.md): instructions loaded by the agent.

[Back to the skill index](../../README.md) · [MIT license](../../LICENSE)
