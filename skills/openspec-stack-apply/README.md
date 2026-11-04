# OpenSpec Stack Apply

Implement an OpenSpec change in one session, with one stacked PR per task
group. The agent first maps every rule in the proposal, spec, and design to the
group that owns it. It then works through the change top to bottom. Before each
group it creates a new layer with GitHub's [`gh stack`](https://github.com/github/gh-stack),
then implements the group with tests that fail on a naive implementation of its
rules, and commits it with task markers that name the proving tests. At the end
it publishes the stack as draft PRs and reviews them with
[Stacked PR Feedback](../stacked-pr-feedback/README.md).

## Why one session instead of a worker per group

In a [recorded comparison](../../tests/README.md#recorded-result-2026-11-03),
one session applying a five-group change cost about $0.18 and took about a
minute. A parent delegating each group to a fresh worker cost $0.41, took nearly
five minutes, and caught nothing extra. This skill keeps the single session and
adds the parts that do pay off: one reviewable PR per group, built while
implementing so every layer is a real tested state, and a review pass before
the PRs leave draft.

## Requirements

- An OpenSpec project with a change ready to apply, and the OpenSpec CLI.
- `gh` authenticated, plus `gh extension install github/gh-stack`. The
  repository must have GitHub Stacked PRs available; the skill stops and tells
  you if it does not.
- `gh pr view --json` must support `headRefOid` for feedback collection.
  If the field is unavailable, the skill asks you to upgrade `gh`.
- A clean working tree.
- Optional: [Stacked PR Feedback](../stacked-pr-feedback/README.md) for the
  review step, and a `tdd` skill, which the agent uses when present.

## Usage

```text
/openspec-stack-apply <change-name>
```

Use `$openspec-stack-apply` in Codex. The request authorizes creating branches,
commits, pushes, and draft PRs. The agent asks before marking PRs ready, and it
never merges or archives the change.

| Group in `tasks.md` | Branch | PR base |
| --- | --- | --- |
| `## 1. Amount parsing` | `<change>/1-amount-parsing` | trunk |
| `## 2. Line totals` | `<change>/2-line-totals` | `<change>/1-amount-parsing` |
| `## 3. Coupons` | `<change>/3-coupons` | `<change>/2-line-totals` |

If a later group exposes a bug in an earlier layer, the fix is committed on that
layer and the layers above are rebased with `gh stack rebase --upstack`. Rerun
the command to resume: it continues from the existing stack and the first
unchecked task.

## Installation

Install it together with `stacked-pr-feedback` as described in the
[repository README](../../README.md#installation).

## Files

- [SKILL.md](SKILL.md): instructions loaded by the agent.

[Back to the skill index](../../README.md) · [MIT license](../../LICENSE)
