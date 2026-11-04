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
it with any SKILL.md you pass. The fixtures have no Git remote, so skills that
publish PRs are told to skip publishing.

There are three cases, chosen with `--case`. Each keeps its trap list, owning
groups, and mutants in `hidden/<case>/case.py`.

### `comparison`: invoice totals

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
Every recorded agent run so far passes all ten traps, so on its own this case
cannot separate one way of applying a change from another.

### `loans`: held-out library loans

The `loan-desk` change has six groups over a different domain: due dates,
overdue days, fines, renewals, holds, and receipts. No skill text names its
traps, and the offline suite fails if a SKILL.md mentions a trap's mistake. The
rules are placed where a reader of only scenarios and tasks would miss them:

| Trap | Where the rule lives | Typical miss |
| --- | --- | --- |
| `SpecScenarios` | Spec scenarios | Baseline; not counted as a trap |
| `RejectsDatetime` | Group 1 prose | `isinstance(x, date)` accepts a `datetime` |
| `ChainedClosures` | Group 1 prose | Moving a closed due date forward by one day only |
| `OpenDaysOnly` | Design decision | Counting calendar days as overdue |
| `BookGraceDay` | Group 3 prose | Charging a book's first overdue day |
| `FineCap` | Design decision only | No cap at the replacement fee |
| `RenewFromDue` | Group 4 prose | Counting the renewal from today |
| `RenewalLimit` | Group 4 prose | Allowing a third renewal |
| `NoMutation` | Design decision | Updating the caller's loan in place |
| `HoldRules` | Group 5 vs. group 4 | The borrower's own hold blocking renewal |
| `ReceiptCrossGroup` | Groups 2, 3, and 6 | Calendar days, no grace, or no cap on receipts |
| `ExistingApi` | Proposal | Editing `HOLIDAYS` or `is_open` |

Task 6.3 asks for confirmation from circulation staff, which cannot happen in
the evaluation repository. `unprovable_checked` records it if checked, and
`report` counts runs that check it.

Before comparing arms on this case, calibrate it: run the `single` arm at least
four times and set aside traps it passes in every run. They show nothing about
a skill.

Calibration (2026-11-04): four headless `single` runs, Sonnet 5.5 at medium
effort, about $0.13 and 0.8 minutes each. Every run passed all 11 code traps,
left task 6.3 unchecked, and reported it as a blocker. So on this case, the
code traps and the unprovable task do not separate arms either. Test strength
does: every run killed exactly 8 of 11 mutants and missed the same three.
`RenewFromDue` survives because every renewal test renews on the due date, as
the scenario does. `ReceiptCrossGroup` survives because receipt tests never
span a closed day. `ExistingApi` survives because no test checks `HOLIDAYS` or
`is_open`. Compare arms on `mutants_killed_count`.

### Recorded result (2026-11-04)

[`results/precision-2026-11-04.json`](results/precision-2026-11-04.json)
records four headless runs per arm on `loans`, Sonnet 5.5 at medium effort.
The skill arm used this branch's `openspec-stack-apply`, with publishing and
review skipped.

| | Single | Skill |
| --- | --- | --- |
| Code traps passed | 11/11 in every run | 11/11 in every run |
| Mean mutants killed | 8.0 of 11 | 10.25 of 11 |
| `RenewFromDue` killed | 0/4 | 4/4 |
| `ReceiptCrossGroup` killed | 0/4 | 4/4 |
| `ExistingApi` killed | 0/4 | 1/4 |
| Stacks with every layer clean | – | 4/4 |
| Recorded cost (different workloads) | $0.13 build | $0.13 verification only |
| Recorded wall-clock (different workloads) | 0.8 min build | 0.5 min verification only |

Both arms wrote correct code. The skill arm's tests also caught the renewal and
receipt mistakes that every single run's tests missed. Those are the
cross-group and scenario-shadowed rules the criteria map and the "fails on the
naive implementation" rule target. For each of those two mutants, 4/4 against
0/4 gives a two-sided Fisher exact p of about 0.03. The recorded skill sessions
only verified existing implementations, so their cost and time cannot be
compared to fresh single runs. Neither arm tested the
existing API reliably.

After the criteria map was changed so group 1 owns preserved behavior, four
more skill runs (`apply_preserved_behavior` in the results file) killed all 11
mutants every time, including `ExistingApi` (4/4, against 1/4 before and 0/4
for single). Fresh implementation cost averaged $0.29 and time 1.8 minutes,
versus $0.13 and 0.8 minutes for single. The apparent increase over the earlier skill
version is not a valid comparison: the exact sessions named by those earlier
`result.json` files began with all six layers already implemented. They only
read and verified existing work. Their 6–7 turns and roughly 2,026 output
tokens per run therefore exclude implementation, whereas the new sessions'
13–17 turns and roughly 12,023 output tokens include writing the code and
tests. The previous explanation attributing this to batching was incorrect.
Artifact correctness and mutant scores remain valid; determining the old
skill's implementation cost requires its original build sessions or fresh runs.
Session IDs and usage counters are retained in the results file.

### `warehouse`: larger stateful change

Ten task groups cover a warehouse ledger: normalization, idempotent receipts,
reservations, expiry/cancellation, shipment retries, transfers, bundle expansion,
snapshots, atomic batches, and an unresolved backorder policy. Unlike the earlier
numeric and date helpers, operations compose over nested state and persisted
history. The reference is roughly twice the size of the loans reference.

The unresolved policy is explicit: no allocation priority has been authorized.
Groups 1–9 are independent of that decision; group 10 must remain pending. We
measure whether agents respect that boundary, not whether they guess an unstated
business rule. This does not test discovering an ambiguity that the artifacts
fail to mention.

Frozen before model runs: 15 hidden traps, one mutant each, a correct reference,
and a naive version that passes basic scenarios while failing the traps. The
fixture, tests, and reference hashes are retained in
[`results/warehouse-2026-11-04.json`](results/warehouse-2026-11-04.json).

| Area | Hidden checks |
| --- | --- |
| Existing contract and validation | Existing API, bool quantity rejection, canonical duplicate items |
| Receipts and reservations | Replay, conflicting event reuse, expiry boundary releasing capacity |
| Lifecycle and transfers | Detached nested state, terminal order id reuse, shipment retry, reserved stock excluded from transfers |
| Extensions and persistence | Shared bundle components, snapshot history, invalid snapshot stock |
| Composition | Batch rollback, receipt replay within ordered reserve/ship batch |

Plan: three fresh runs per arm, same Sonnet 5.5 model at medium effort, no
subagents, no publishing/review, current skill unchanged, maximum $2 per run.
Score code correctness, mutant kills, reference-incompatible tests, per-layer
correctness, unsupported completion claims, scope, cost, and elapsed time. Read
all final reports and failing tests before drawing conclusions. This is one
larger case with three repetitions, not evidence of general superiority.

The first six attempts hit the Claude CLI quota before doing work (zero cost).
Six fresh retry sessions subsequently completed. Each was verified to start at
its untouched baseline; session ids, reports, scores, and reference-test failure
traces are recorded in the results file.

| Outcome | Single | Skill |
| --- | --- | --- |
| All 15 code traps passed | 3/3 | 3/3 |
| Own suite passes | 3/3 | 3/3 |
| Unresolved policy left pending | 3/3 | 3/3 |
| In scope | 3/3 | 3/3 |
| Every stack layer clean | – | 3/3 |
| Mean cost | $0.24 | $0.47 |
| Mean minutes | 1.2 | 2.7 |
| Scorable mutant suites | 3/3 | 2/3 |

The raw mutant means are 14/15 for each arm, but this is not a valid comparison
of test strength. One skill suite imports its own `normalize_items` helper at
module scope; the reference only has `_items`, so the whole suite fails to
import. Other suites depend on helper names and receipt-history layouts that
the spec never fixes. The reference uses lists for events; all three skill
implementations use dicts. Some excluded tests also combine required checks
with validation absent from the reference or unspecified by the contract.
Excluding those whole methods can hide real mutant-killing assertions.
Reference incompatibility is therefore not evidence that an agent's test is
wrong, and the raw mean excludes one skill run entirely. The frozen reference
and traps were kept unchanged after the runs.

On this case, the skill delivered tested stack layers at about twice the cost,
with no observed code-correctness or policy-handling advantage. These runs skip
publishing and review. They do not show that the skill improves implementation
quality in general, nor establish equal test strength. More paid repetitions of
this fixture are unlikely to resolve the measurement limitations.

For another experiment, prepare fresh destinations with `compare.py prepare`.
The completed retry directories below must not be reused:

```sh
python3 tests/compare.py prepare single --case warehouse \
  --directory /tmp/new-warehouse/single-1 --model claude-sonnet-5-5
python3 tests/run_comparison.py /tmp/new-warehouse/single-1
```

`run_comparison.py` refuses modified baselines, extra layer branches, or existing
results. It records the session id, request/skill hashes, exit status, token
usage, actual wall-clock time, and model cost. `score` rejects failed or
incomplete sessions launched by this runner. Score completed retry runs with
`compare.py score --claude-result ... --minutes ...` and report them together.
Never rerun inside a completed directory: prepare a fresh destination instead.

### Running it

Prepare several runs per arm in fresh destinations, using the same host and
model for every arm. `--model` is a label recorded with the run.

```sh
python3 tests/compare.py prepare single --case loans --directory /tmp/cmp/single-1 --model '<model>'
python3 tests/compare.py prepare skill --case loans --directory /tmp/cmp/skill-1 --model '<model>' \
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
trap's plausible mistake applied (`MUTANTS` in `hidden/<case>/case.py`). Tests that fail
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
It builds a comparison case's change as local branches whose own tests all
pass, with planted defects and decoys (correct code that looks suspicious).
Pick a stack with `--stack`.

### `invoice`: the skill's own questions

Five `invoice-totals` layers. The plants are the defects the review skill's
three questions target.

| Plant | Layer | Defect |
| --- | --- | --- |
| `half-even-rounding` | 2 | `round()` on a `Decimal` rounds half-even; the layer's tests never hit a .5 case |
| `coupon-cap-wrong-layer` | 3 or 5 | Layer 3 lets a coupon exceed the subtotal; layer 5 adds the cap, on the wrong layer |
| `scope-leak` | 1 | An unrelated edit to `notes.txt` |
| `grouping-regression` | 5 | Stripping every comma accepts `"1,23"` |
| Decoys | 3, 4 | Integer `(x + 50) // 100` half-up rounding, which is correct |

Layer 1's `\d` also matches non-ASCII digits. That defect was not planted, but
it is real; label findings about it `true`. It is kept so later runs stay
comparable with the recorded ones. The layers live in
[`fixtures/review/layers/`](fixtures/review/layers/).

### `loans`: held out

Six `loan-desk` layers in the held-out domain. The plants are design and spec
fit, outside the skill's three questions. Each layer's tests are written to
match its code, so tests cannot reveal any of them.

| Plant | Layer | Defect |
| --- | --- | --- |
| `design-reuse` | 2 | `days_overdue` restates the closed-day rule the design says to take from `is_open`; behavior is unchanged |
| `exception-type` | 4 | Refused renewals raise a custom `RenewalError`, not the `ValueError` the spec requires |
| `spec-tampering` | 4 | Three renewals allowed, with the layer editing `spec.md` to match |
| `signature-mismatch` | 5 | `place_hold(patron, holds)` instead of `place_hold(holds, patron)` |
| `silent-spec-change` | 6 | `overdue_items` skips overdue loans that owe no fine |
| Decoys | 1 | An exact `type(...) is not date` check, and a loop to the next open day; both correct |

Requests for this stack tell reviewers to judge against the spec as of `main`,
because layer 4 edits it. The layers live in
[`fixtures/review-loans/layers/`](fixtures/review-loans/layers/), mirroring
repository paths.

### Running it

```sh
python3 tests/review_bench.py prepare plain --stack loans --directory /tmp/rev/plain-1 --model '<model>'
python3 tests/review_bench.py prepare skill --stack loans --directory /tmp/rev/skill-1 --model '<model>' \
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
all findings. Findings that hit a decoy are false positives, and so are
unmatched findings unless labeled. `repo_unchanged` checks that the reviewer
moved no branch, left the top branch checked out, and edited nothing.

Pattern matching is approximate in both directions. Read every finding before
trusting a figure: `unmatched` lists findings no pattern caught, and `matched`
maps each credited finding's index to its plants. Record verdicts in
`labels.json` in the run directory, keyed by finding index: `true` or `false`
for an unmatched finding, or `{"plants": [...], "real": true}` to replace a
wrong pattern match.

### Recorded result (2026-11-04, `invoice`)

Three headless runs per arm, Sonnet 5.5 at medium effort. The skill arm ran
this branch's `stacked-pr-feedback` in local review mode with subagents
allowed. Every finding was read and labeled where the patterns were wrong
(see `labels` in the results file). One plain finding had been credited with
the coupon cap; it was about negative coupons and misread layer 3. All other
unplanted findings were real: the `\d` defect, missing `build_invoice` test
coverage, and the `notes.txt` edit reported on the wrong layer.

| | Plain | Skill |
| --- | --- | --- |
| `half-even-rounding` | 3/3 | 3/3 |
| `coupon-cap-wrong-layer` | 0/3 | 3/3 |
| `scope-leak` | 1/3 | 3/3 |
| `grouping-regression` | 3/3 | 3/3 |
| Mean recall | 0.58 | 1.0 |
| Mean precision | 0.93 | 1.0 |
| Decoy hits | 0/3 | 0/3 |
| Mean cost | $0.07 | $0.13 |
| Mean wall-clock | 0.6 min | 0.9 min |

The skill found every plant in every run with no false positives, at about
twice the cost. Plain review never located the wrong-layer fix and missed the
scope leak in two of three runs. Pooled over those two plants, that is 6/6
against 1/6 (two-sided Fisher exact p ≈ 0.015). The plants were designed from
the skill's questions, so this shows the skill does what it says; the `loans`
stack tests whether it generalizes.

### Recorded result (2026-11-04, `loans`)

Three headless runs per arm, set up as for `invoice`. Every finding was read;
the results file retains their text and labels. A holiday-coverage finding was
incorrectly credited to `design-reuse`; that credit is removed. A separate
finding catches the plant, so recall and precision are unchanged.

| | Plain | Skill |
| --- | --- | --- |
| `design-reuse` | 3/3 | 3/3 |
| `exception-type` | 3/3 | 3/3 |
| `spec-tampering` | 2/3 | 3/3 |
| `signature-mismatch` | 3/3 | 3/3 |
| `silent-spec-change` | 3/3 | 3/3 |
| Mean recall | 0.93 | 1.0 |
| Mean precision (labeled) | 1.0 | 1.0 |
| Decoy hits | 0/3 | 0/3 |
| Mean findings | 4.7 | 9 |
| Mean cost | $0.12 | $0.18 |
| Mean wall-clock | 0.5 min | 0.8 min |

On design and spec fit, which are outside the skill's three questions, plain
review is about as good as the skill. The skill's extra findings were real and
of two kinds. Test gaps: renewal tests that never land a renewed due date on a
closed day. Completion claims: every skill run flagged that layer 6 checks task
6.3, a staff confirmation with no evidence, and no plain run did. That task is
checked because the stack builder marks every task of a group. It was not
planted, so it is reported here and not counted toward recall. Taken together,
the skill's advantage is in test strength, layer ownership, scope, and
completion claims. It does not make review better at spec reading in general,
and it costs about 1.5 to 2 times as much.
