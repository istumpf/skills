# Tests and evaluations

## Offline checks

From the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

[Tests](../.github/workflows/tests.yml) runs the same command on GitHub Actions
for every push and pull request, on Python 3.9 and 3.13 with only Git
installed. It needs no OpenSpec CLI, model credentials, or PR service.

- `test_stacked_pr_feedback.py` checks the feedback collector with canned
  GitHub data and a real local Git stack: stack discovery, handled-item
  detection, owner attribution, merge detection, and truncation warnings.
- `test_comparison.py` checks the comparison harness below, including that
  every hidden trap separates a correct implementation from a naive one and
  that each mutant fails its own trap and no other.
- `test_review_bench.py` checks the review benchmark below: every layer passes
  its own tests, only the planted traps fail, the decoys are correct, and
  findings are matched and scored.

None of them runs an agent. The skills themselves were exercised end to end against
a private sandbox repository; that run is not automated.

## Comparing ways to apply a change

`compare.py` asks whether a way of applying an OpenSpec change catches defects
that plain top-to-bottom application misses, and at what cost. The `single`
arm applies the change with no skill and no delegation. The `skill` arm applies
it with any SKILL.md you pass. The fixture has no Git remote, so skills that
publish PRs are told to skip publishing.

The `invoice-totals` change has five groups that depend on each other. Rules
that matter are written in the spec prose and design decisions, not in
`tasks.md`. Several groups extend earlier work; group 5, for example, widens
group 1's parser. Hidden checks in `hidden/comparison/` are never copied into the
evaluation repository. Each test class scores one trap:

| Trap | Where the rule lives | Typical miss |
| --- | --- | --- |
| `SpecScenarios` | Spec scenarios | Baseline; not counted as a trap |
| `ExactParsing` | Group 1 prose | `int(float(text) * 100)` turns `"19.99"` into 1998 |
| `StrictParsing` | Group 1 prose | Accepting `"1e3"`, `"+5"`, `"NaN"` |
| `LineHalfUp` | Group 2 prose | `round()` is half-even |
| `CouponRules` | Group 3 prose | Fixed coupon larger than the subtotal |
| `TaxExactHalfUp` | Group 4 prose | Float rate gives 11 instead of 12 for 1000 at 1.15% |
| `PerLineRounding` | Design decision | Rounding once on the summed subtotal |
| `CouponAfterLineDiscounts` | Cross-group | Coupon applied to list price |
| `GroupedParsingRegression` | Group 5 vs. group 1 | `replace(",", "")` accepts `"1,23"` |
| `NoMutation` | Group 5 prose | Defaulting `discount_percent` into caller lines |
| `ExistingApi` | Proposal | Breaking `format_cents` |

`reference/comparison/` passes every check. `reference/comparison-naive/`
passes the written scenarios and fails every trap; the offline suite asserts
both, so each trap is known to separate correct from plausible-but-wrong work.

### Running it

Prepare several runs per arm in fresh destinations, using the same host and
model for every arm. `--model` is a label recorded with the run.

```sh
python3 tests/compare.py prepare single --directory /tmp/cmp/single-1 --model '<model>'
python3 tests/compare.py prepare skill --directory /tmp/cmp/skill-1 --model '<model>' \
  --skill skills/openspec-stack-apply/SKILL.md
```

Start a fresh conversation in each generated `repo/` and give it
`../REQUEST.txt`. Record wall-clock minutes yourself and the run's cost from the
host (for example `/cost` in Claude Code). Headless Claude Code runs can supply
the cost directly:

```sh
cd /tmp/cmp/single-1/repo
claude -p "$(cat ../REQUEST.txt)" --model claude-sonnet-5-5 --effort medium \
  --output-format json --permission-mode acceptEdits \
  --allowedTools Bash Read Edit Write Glob Grep Skill \
  --disallowedTools Agent Workflow > ../result.json
```

For a skill arm that delegates, also allow `Agent` and `SendMessage`, and do
not disallow `Agent`. Then score and report:

```sh
python3 tests/compare.py score /tmp/cmp/single-1 --claude-result /tmp/cmp/single-1/result.json --minutes 0.9
python3 tests/compare.py report /tmp/cmp/*
```

`score` writes `score.json` with per-trap results, whether the agent's own tests
pass, how strong those tests are, per-layer results, completed tasks, files changed outside the expected scope since the
baseline commit (committed or not), the number of commits, and OpenSpec
validation (`--skip-openspec` when the CLI is absent).
Use `--cost` instead of `--claude-result` for other hosts.

Test strength runs the agent's own `test_*.py` files against the reference
implementation, then against one mutant per trap: the reference with that
trap's plausible mistake applied (`MUTANTS` in `compare.py`). Tests that fail
on the reference, because they are stricter than the spec or wrong, are listed
in `tests_failing_on_reference` and set aside. A mutant is killed when any
other test fails on it. `mutants_killed_count` therefore measures whether the
agent wrote tests that would have caught each trap, not only whether its code
avoided it. It is empty when no test both passes on the reference and fails
without an implementation.

Per-layer results apply to runs that leave `invoice-totals/<n>-*` branches.
Each branch's committed `invoice.py` must pass every trap owned by group *n* or
below (`TRAP_GROUPS`). A fix committed on a higher layer instead of the layer
that owns it shows up as a failure on the lower one. Do not take minutes
from the result's `duration_ms`: it omits time spent waiting on subagents.
Rescoring keeps previously recorded cost and minutes. `report` prints a Markdown
table grouped by arm.

Keep skill text free of this fixture's specifics. A skill that names a trap's
mistake (a rounding mode, a parsing shortcut) is handed the answer, and its
score no longer measures the skill.

Agent runs vary. Use at least three runs per arm before drawing conclusions,
and read each session's report to see whether a review found defects or the
first pass avoided them. A trap that both arms
always pass or always fail does not tell you anything about review.

### Recorded result (2026-11-03)

This run compared `single` against the former `openspec-orchestrate` skill,
which delegated each task group to a fresh worker and reviewed it in the
parent. The result led to replacing it with
[OpenSpec Stack Apply](../skills/openspec-stack-apply/README.md).

[`results/comparison-2026-11-03.json`](results/comparison-2026-11-03.json)
records three headless Claude Code runs per arm. Single: Sonnet 5.5 at medium
effort, with delegation disabled. Orchestrate: a Sonnet 5.5 parent with Haiku
5.5 workers, all at medium effort.

| | Single | Orchestrate |
| --- | --- | --- |
| Traps passed | 10/10 in every run | 10/10 in every run |
| Mean cost | $0.18 | $0.41 |
| Mean wall-clock | 0.9 min | 4.7 min |
| Repair rounds | – | 0 in every run |

Both arms got everything right, so on a five-group change whose rules are all
written down, orchestration added cost and time without catching anything. The
parent's own share (~$0.36) exceeded the whole single-agent run, so cheaper
workers did not offset the overhead. This fixture cannot tell the two apart.
Neither very long changes (where one context degrades) nor rules missing from
the spec (where review has something to catch) are tested yet.

### End-to-end sandbox run (2026-11-03)

A private sandbox repository holds one end-to-end run of
the skills before the criteria map and evidence lines were added: five stacked
PRs (#2–#6), seeded review comments handled by `stacked-pr-feedback`, then
merged. Scored afterwards with this harness, every PR head passed every trap
its groups own, and the merged code passed all ten. Its tests killed 7 of 10
mutants. They missed `CouponAfterLineDiscounts` (the tax-after-coupon test has
no line discount, so coupon order is never observed), `ExistingApi` (no test of
`format_cents`), and `NoMutation` (the tested line already sets
`discount_percent`). Code that avoids every trap can still have tests that
would not have caught the cross-group one. That gap is what the mutant score
measures.

## Measuring review precision

`review_bench.py` measures a stack review on its own, with no remote or PRs.
It builds the `invoice-totals` change as five local branches whose own tests all
pass, with four planted defects and two decoys:

| Plant | Layer | Defect |
| --- | --- | --- |
| `half-even-rounding` | 2 | `round()` on a `Decimal` rounds half-even; the layer's tests never hit a .5 case |
| `coupon-cap-wrong-layer` | 3 or 5 | Layer 3 lets a coupon exceed the subtotal; layer 5 adds the cap, on the wrong layer |
| `scope-leak` | 1 | An unrelated edit to `notes.txt` |
| `grouping-regression` | 5 | Stripping every comma accepts `"1,23"` |
| Decoys | 3, 4 | Integer `(x + 50) // 100` half-up rounding, which is correct |

The layers live in [`fixtures/review/layers/`](fixtures/review/layers/).

```sh
python3 tests/review_bench.py prepare plain --directory /tmp/rev/plain-1 --model '<model>'
python3 tests/review_bench.py prepare skill --directory /tmp/rev/skill-1 --model '<model>' \
  --skill skills/stacked-pr-feedback/SKILL.md
```

Run each request as in the comparison above; the reviewer writes
`findings.json` next to `repo/`. Then:

```sh
python3 tests/review_bench.py score /tmp/rev/skill-1 --claude-result /tmp/rev/skill-1/result.json --minutes 2
python3 tests/review_bench.py report /tmp/rev/*
```

A finding counts toward a plant when it names one of the plant's layers and its
path or body matches the plant's pattern; one finding may count toward several
plants. Recall is the share of plants found. Precision is true findings over
all findings. Findings that hit a decoy are false positives. So are unmatched
findings, unless `labels.json` in the run directory marks their index `true`
after you read them, for example `{"6": true}`. `repo_unchanged` checks that
the reviewer moved no branch, left the top branch checked out, and edited
nothing.

Pattern matching is approximate. Read `unmatched` in each `score.json` before
trusting a precision figure, and label any real defect the plants missed.
