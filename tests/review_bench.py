#!/usr/bin/env python3
"""Measure a stack review's precision and recall on planted defects.

Each stack applies one comparison case's change as local branches. Every
layer's own tests pass, but defects are planted and some correct changes look
suspicious (decoys). Stacks: `invoice` plants the defects the review skill's
three questions target; `loans` is held out, with plants outside them (design
and spec fit). Arms: `plain` reviews with no skill and no delegation; `skill`
reviews with the SKILL.md given by --skill.

prepare: build the stack for one arm. score: match findings.json against the
plants. report: aggregate scored runs by arm.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from types import SimpleNamespace

import compare

ARMS = ("plain", "skill")
# Each plant names the layers a finding may be attributed to and a pattern its
# path or body must match (case-insensitive). One finding may match several.
STACKS = {
    "invoice": SimpleNamespace(
        case=compare.load_case("comparison"),
        layers=compare.HERE / "fixtures/review/layers",
        slugs=("amount-parsing", "line-totals", "coupons", "sales-tax", "invoice-summary"),
        plants={
            "half-even-rounding": ([2], r"half[- ]?(up|even)|banker|round\("),
            "coupon-cap-wrong-layer": ([3, 5], r"\bcap\b|exceed|larger than|greater than|more than|min\("),
            "scope-leak": ([1], r"notes\.txt"),
            "grouping-regression": ([5], r"separator|comma|group|replace|1,23"),
        },
        # Correct code that looks suspicious; a finding here is a false positive.
        decoys={
            "integer-half-up-coupon": ([3], r"\+ ?50|// ?100|half|round"),
            "integer-half-up-tax": ([4], r"\+ ?50|// ?100|half|round"),
        },
        # Kept empty so requests match the recorded runs.
        spec_ref=""),
    "loans": SimpleNamespace(
        case=compare.load_case("loans"),
        layers=compare.HERE / "fixtures/review-loans/layers",
        slugs=("due-dates", "overdue-days", "fines", "renewals", "holds", "receipts"),
        plants={
            "design-reuse": ([2], r"is_open|restat|duplicat|reuse|weekday|sunday"),
            "exception-type": ([4], r"ValueError|RenewalError"),
            "spec-tampering": ([4], r"spec\.md|three (times|renewals)|third renewal|twice|"
                                    r"MAX_RENEWALS|renewal limit"),
            "signature-mismatch": ([5], r"order|swap|signature|argument|parameter|place_hold\(holds"),
            "silent-spec-change": ([6], r"overdue_items|zero fine|no fine|fine > 0|fine of 0|"
                                        r"due before"),
        },
        decoys={
            "exact-type-check": ([1], r"isinstance|type\(checkout\)|subclass"),
            "next-open-loop": ([1], r"infinite|forever|terminat|unbounded"),
        },
        # A layer edits the spec, so reviewers judge against trunk's copy.
        spec_ref=" as of `main`"),
}


def branches(stack):
    return [f"{stack.case.change}/{n}-{slug}" for n, slug in enumerate(stack.slugs, 1)]


def build_stack(stack, repo):
    for n, branch in enumerate(branches(stack), 1):
        compare.git(repo, "checkout", "-q", "-b", branch)
        # Layer directories mirror repository paths.
        shutil.copytree(stack.layers / str(n), repo, dirs_exist_ok=True)
        tasks = repo / stack.case.tasks
        tasks.write_text(re.sub(rf"^- \[ \] ({n}\.\d+)", r"- [x] \1",
                                tasks.read_text(), flags=re.MULTILINE))
        compare.git(repo, "add", ".")
        compare.git(repo, "commit", "-q", "-m", f"feat({stack.case.change}): {stack.slugs[n - 1]}")


def repo_state(stack, repo):
    """Checked-out branch and every stack head; review must leave both unchanged."""
    return {"checked_out": compare.git(repo, "branch", "--show-current"),
            "heads": {branch: compare.git(repo, "rev-parse", branch) for branch in branches(stack)}}


def prepare(arm, directory, model, skill=None, stack_name="invoice"):
    if (arm == "skill") != bool(skill):
        raise ValueError("--skill is required for the skill arm and only allowed there")
    if stack_name not in STACKS:
        raise ValueError(f"unknown stack: {stack_name}")
    stack = STACKS[stack_name]
    change = stack.case.change
    root = Path(directory).resolve()
    root.mkdir(parents=True)  # Refuse to replace an existing run.
    repo = root / "repo"
    shutil.copytree(stack.case.fixture, repo)
    for args in (("init", "-q", "--initial-branch=main"), ("config", "user.name", "Skill Evaluation"),
                 ("config", "user.email", "skill-evaluation@example.invalid"),
                 ("config", "commit.gpgsign", "false")):
        compare.git(repo, *args)
    (root / "empty-hooks").mkdir()
    compare.git(repo, "config", "core.hooksPath", str(root / "empty-hooks"))
    compare.git(repo, "add", ".")
    compare.git(repo, "commit", "-q", "-m", "chore: review fixture baseline")
    build_stack(stack, repo)
    listed = ", ".join(f"`{b}`" for b in branches(stack))
    output = (f"Write the combined findings to {root / 'findings.json'} as "
              '{"findings": [{"branch": ..., "path": ..., "line": ..., "body": ...}]}, '
              "attributing each finding to the branch that introduced the problem.")
    if arm == "skill":
        prompt = (f"Use the skill at {Path(skill).resolve()} and run only its local review "
                  f"mode on this stack of local branches, trunk `main`, bottom to top: {listed}. "
                  "There is no Git remote and there are no PRs: skip collection, triage, "
                  "fixes, replies, and pushing, and use branch names wherever the skill asks "
                  f"for PR identifiers. The acceptance criteria are in the OpenSpec change "
                  f"{change}{stack.spec_ref}. {output}")
    else:
        prompt = (f"Review this stack of local branches, trunk `main`, bottom to top: {listed}. "
                  f"Each branch is one task group of the OpenSpec change {change} and "
                  "targets the branch below it. Report defects against the change's "
                  f"proposal, design, and specs{stack.spec_ref}. Do not spawn subagents or "
                  f"delegate. {output}")
    prompt += (f"\n\nWork in {repo}. All writes must remain inside {root}. Read AGENTS.md. "
               "Do not modify the repository, its branches, or any skill files.\n")
    (root / "REQUEST.txt").write_text(prompt)
    (root / "evaluation.json").write_text(json.dumps(
        {"case": "review", "stack": stack_name, "arm": arm, "model": model,
         "skill": str(Path(skill).resolve()) if skill else None,
         "state": repo_state(stack, repo)}, indent=2) + "\n")
    return root


def layer_of(stack, finding):
    match = re.match(rf"{re.escape(stack.case.change)}/(\d+)-", str(finding.get("branch", "")))
    return int(match.group(1)) if match else None


def matches(stack, finding, rules):
    text = f"{finding.get('path', '')}\n{finding.get('body', '')}"
    return [name for name, (layers, pattern) in rules.items()
            if layer_of(stack, finding) in layers and re.search(pattern, text, re.IGNORECASE)]


def score(directory, cost=None, minutes=None):
    """Score findings.json against the stack's plants and decoys.

    labels.json maps finding indexes to a verdict after you read them: `true` or
    `false` for whether an unmatched finding is real, or
    `{"plants": [...], "real": bool}` to replace the pattern match. Unmatched,
    unlabeled findings count as false positives.
    """
    root = Path(directory).resolve()
    metadata = json.loads((root / "evaluation.json").read_text())
    stack = STACKS[metadata.get("stack", "invoice")]
    repo = root / "repo"
    saved = root / "score.json"
    previous = json.loads(saved.read_text()) if saved.exists() else {}
    findings_path = root / "findings.json"
    findings = json.loads(findings_path.read_text())["findings"] if findings_path.exists() else []
    labels_path = root / "labels.json"
    labels = json.loads(labels_path.read_text()) if labels_path.exists() else {}
    found, matched, decoy_hits, unmatched = set(), {}, [], []
    true_positives = false_positives = 0
    for index, finding in enumerate(findings):
        label = labels.get(str(index))
        if isinstance(label, dict):
            plants, real = label["plants"], label["real"]
            found.update(plants)
            if plants:
                matched[str(index)] = plants
            true_positives += real
            false_positives += not real
            continue
        plants = matches(stack, finding, stack.plants)
        found.update(plants)
        if plants:
            true_positives += 1
            matched[str(index)] = plants
        elif matches(stack, finding, stack.decoys):
            false_positives += 1
            decoy_hits.append(index)
        elif label is True:
            true_positives += 1
        else:
            false_positives += 1
            unmatched.append({"index": index, "labeled": str(index) in labels, **finding})
    status = compare.git(repo, "status", "--porcelain")
    result = {
        "stack": metadata.get("stack", "invoice"),
        "arm": metadata["arm"],
        "model": metadata["model"],
        "plants": {name: name in found for name in stack.plants},
        "recall": round(len(found) / len(stack.plants), 2),
        "findings": len(findings),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "precision": round(true_positives / len(findings), 2) if findings else None,
        # Pattern matches can over-credit; audit them with the findings they name.
        "matched": matched,
        "decoy_hits": decoy_hits,
        "unmatched": unmatched,
        "repo_unchanged": not status and repo_state(stack, repo) == metadata["state"],
        "cost_usd": previous.get("cost_usd") if cost is None else cost,
        "minutes": previous.get("minutes") if minutes is None else minutes,
    }
    saved.write_text(json.dumps(result, indent=2) + "\n")
    return result


def report(directories):
    scores = [json.loads((Path(d) / "score.json").read_text()) for d in directories]
    names = {s.get("stack", "invoice") for s in scores}
    if len(names) != 1:
        raise ValueError(f"report one stack at a time, got {sorted(names)}")
    stack = STACKS[names.pop()]
    arms = [arm for arm in ARMS if any(s["arm"] == arm for s in scores)]
    rows = {arm: [s for s in scores if s["arm"] == arm] for arm in arms}
    cell = lambda value: "–" if value is None else str(value)
    lines = ["| Metric | " + " | ".join(arms) + " |", "| --- |" + " --- |" * len(arms)]
    lines.append("| Runs | " + " | ".join(str(len(rows[a])) for a in arms) + " |")
    for plant in stack.plants:
        lines.append(f"| {plant} | " + " | ".join(
            f"{sum(s['plants'][plant] for s in rows[a])}/{len(rows[a])}" for a in arms) + " |")
    lines.append("| Runs hitting a decoy | " + " | ".join(
        f"{sum(bool(s['decoy_hits']) for s in rows[a])}/{len(rows[a])}" for a in arms) + " |")
    lines.append("| Runs leaving the repo unchanged | " + " | ".join(
        f"{sum(s['repo_unchanged'] for s in rows[a])}/{len(rows[a])}" for a in arms) + " |")
    for label, key, digits in (("Mean recall", "recall", 2), ("Mean precision", "precision", 2),
                               ("Mean findings", "findings", 1), ("Mean cost (USD)", "cost_usd", 2),
                               ("Mean minutes", "minutes", 1)):
        values = [compare.mean((s.get(key) for s in rows[a]), digits) for a in arms]
        lines.append(f"| {label} | " + " | ".join(cell(v) for v in values) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="action", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("arm", choices=ARMS)
    setup.add_argument("--directory", type=Path, required=True)
    setup.add_argument("--model", required=True, help="model label recorded with the run")
    setup.add_argument("--skill", type=Path, help="SKILL.md to review with (skill arm only)")
    setup.add_argument("--stack", choices=sorted(STACKS), default="invoice")
    grade = commands.add_parser("score")
    grade.add_argument("directory", type=Path)
    grade.add_argument("--cost", type=float, help="run cost in USD reported by the host")
    grade.add_argument("--minutes", type=float, help="wall-clock minutes, measured outside the agent")
    grade.add_argument("--claude-result", type=Path,
                       help="read --cost from claude -p --output-format json output")
    summary = commands.add_parser("report")
    summary.add_argument("directories", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            root = prepare(args.arm, args.directory, args.model, args.skill, args.stack)
            print(f"Prepared {root / 'repo'}\nGive the agent {root / 'REQUEST.txt'}")
        elif args.action == "score":
            if args.claude_result:
                args.cost = compare.claude_result_cost(args.claude_result)
            print(json.dumps(score(args.directory, args.cost, args.minutes), indent=2))
        else:
            print(report(args.directories))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Review benchmark failed: {error}\n")


if __name__ == "__main__":
    main()
