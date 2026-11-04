#!/usr/bin/env python3
"""Measure a stack review's precision and recall on planted defects.

The stack applies the comparison fixture's `invoice-totals` change as five local
branches. Every layer's own tests pass, but four defects are planted and two
correct changes look suspicious (decoys). Arms: `plain` reviews with no skill
and no delegation; `skill` reviews with the SKILL.md given by --skill.

prepare: build the stack for one arm. score: match findings.json against the
plants. report: aggregate scored runs by arm.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

import compare

LAYERS = compare.HERE / "fixtures/review/layers"
ARMS = ("plain", "skill")
BRANCHES = [f"{compare.CHANGE}/{n}-{slug}" for n, slug in enumerate(
    ("amount-parsing", "line-totals", "coupons", "sales-tax", "invoice-summary"), 1)]
# Each plant names the layers a finding may be attributed to and a pattern its
# path or body must match (case-insensitive). One finding may match several.
PLANTS = {
    "half-even-rounding": ([2], r"half[- ]?(up|even)|banker|round\("),
    "coupon-cap-wrong-layer": ([3, 5], r"\bcap|exceed|larger than|greater than|more than|min\("),
    "scope-leak": ([1], r"notes\.txt"),
    "grouping-regression": ([5], r"separator|comma|group|replace|1,23"),
}
# Correct code that looks suspicious; a finding here is a false positive.
DECOYS = {
    "integer-half-up-coupon": ([3], r"\+ ?50|// ?100|half|round"),
    "integer-half-up-tax": ([4], r"\+ ?50|// ?100|half|round"),
}


def build_stack(repo):
    for n, branch in enumerate(BRANCHES, 1):
        compare.git(repo, "checkout", "-q", "-b", branch)
        for path in (LAYERS / str(n)).iterdir():
            shutil.copy2(path, repo / path.name)
        tasks = repo / compare.TASKS
        tasks.write_text(re.sub(rf"^- \[ \] ({n}\.\d+)", r"- [x] \1",
                                tasks.read_text(), flags=re.MULTILINE))
        compare.git(repo, "add", ".")
        compare.git(repo, "commit", "-q", "-m", f"feat({compare.CHANGE}): {branch.split('-', 2)[-1]}")


def repo_state(repo):
    """Checked-out branch and every stack head; review must leave both unchanged."""
    return {"checked_out": compare.git(repo, "branch", "--show-current"),
            "heads": {branch: compare.git(repo, "rev-parse", branch) for branch in BRANCHES}}


def prepare(arm, directory, model, skill=None):
    if (arm == "skill") != bool(skill):
        raise ValueError("--skill is required for the skill arm and only allowed there")
    root = Path(directory).resolve()
    root.mkdir(parents=True)  # Refuse to replace an existing run.
    repo = root / "repo"
    shutil.copytree(compare.FIXTURE, repo)
    for args in (("init", "-q", "--initial-branch=main"), ("config", "user.name", "Skill Evaluation"),
                 ("config", "user.email", "skill-evaluation@example.invalid"),
                 ("config", "commit.gpgsign", "false")):
        compare.git(repo, *args)
    (root / "empty-hooks").mkdir()
    compare.git(repo, "config", "core.hooksPath", str(root / "empty-hooks"))
    compare.git(repo, "add", ".")
    compare.git(repo, "commit", "-q", "-m", "chore: review fixture baseline")
    build_stack(repo)
    stack = ", ".join(f"`{b}`" for b in BRANCHES)
    output = (f"Write the combined findings to {root / 'findings.json'} as "
              '{"findings": [{"branch": ..., "path": ..., "line": ..., "body": ...}]}, '
              "attributing each finding to the branch that introduced the problem.")
    if arm == "skill":
        prompt = (f"Use the skill at {Path(skill).resolve()} and run only its local review "
                  f"mode on this stack of local branches, trunk `main`, bottom to top: {stack}. "
                  "There is no Git remote and there are no PRs: skip collection, triage, "
                  "fixes, replies, and pushing, and use branch names wherever the skill asks "
                  f"for PR identifiers. The acceptance criteria are in the OpenSpec change "
                  f"{compare.CHANGE}. {output}")
    else:
        prompt = (f"Review this stack of local branches, trunk `main`, bottom to top: {stack}. "
                  "Each branch is one task group of the OpenSpec change "
                  f"{compare.CHANGE} and targets the branch below it. Report defects "
                  "against the change's proposal, design, and specs. Do not spawn "
                  f"subagents or delegate. {output}")
    prompt += (f"\n\nWork in {repo}. All writes must remain inside {root}. Read AGENTS.md. "
               "Do not modify the repository, its branches, or any skill files.\n")
    (root / "REQUEST.txt").write_text(prompt)
    (root / "evaluation.json").write_text(json.dumps(
        {"case": "review", "arm": arm, "model": model,
         "skill": str(Path(skill).resolve()) if skill else None,
         "state": repo_state(repo)}, indent=2) + "\n")
    return root


def layer_of(finding):
    match = re.match(rf"{re.escape(compare.CHANGE)}/(\d+)-", str(finding.get("branch", "")))
    return int(match.group(1)) if match else None


def matches(finding, rules):
    text = f"{finding.get('path', '')}\n{finding.get('body', '')}"
    return [name for name, (layers, pattern) in rules.items()
            if layer_of(finding) in layers and re.search(pattern, text, re.IGNORECASE)]


def score(directory, cost=None, minutes=None):
    """Score findings.json; labels.json may map unmatched finding indexes to true or false.

    Unmatched findings count as false positives unless labeled true.
    """
    root = Path(directory).resolve()
    metadata = json.loads((root / "evaluation.json").read_text())
    repo = root / "repo"
    saved = root / "score.json"
    previous = json.loads(saved.read_text()) if saved.exists() else {}
    findings_path = root / "findings.json"
    findings = json.loads(findings_path.read_text())["findings"] if findings_path.exists() else []
    labels_path = root / "labels.json"
    labels = json.loads(labels_path.read_text()) if labels_path.exists() else {}
    found, decoy_hits, unmatched = set(), [], []
    true_positives = false_positives = 0
    for index, finding in enumerate(findings):
        plants = matches(finding, PLANTS)
        found.update(plants)
        if plants:
            true_positives += 1
        elif matches(finding, DECOYS):
            false_positives += 1
            decoy_hits.append(index)
        elif labels.get(str(index)) is True:
            true_positives += 1
        else:
            false_positives += 1
            unmatched.append({"index": index, "labeled": str(index) in labels, **finding})
    status = compare.git(repo, "status", "--porcelain")
    result = {
        "arm": metadata["arm"],
        "model": metadata["model"],
        "plants": {name: name in found for name in PLANTS},
        "recall": round(len(found) / len(PLANTS), 2),
        "findings": len(findings),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "precision": round(true_positives / len(findings), 2) if findings else None,
        "decoy_hits": decoy_hits,
        "unmatched": unmatched,
        "repo_unchanged": not status and repo_state(repo) == metadata["state"],
        "cost_usd": previous.get("cost_usd") if cost is None else cost,
        "minutes": previous.get("minutes") if minutes is None else minutes,
    }
    saved.write_text(json.dumps(result, indent=2) + "\n")
    return result


def report(directories):
    scores = [json.loads((Path(d) / "score.json").read_text()) for d in directories]
    arms = [arm for arm in ARMS if any(s["arm"] == arm for s in scores)]
    rows = {arm: [s for s in scores if s["arm"] == arm] for arm in arms}
    cell = lambda value: "–" if value is None else str(value)
    lines = ["| Metric | " + " | ".join(arms) + " |", "| --- |" + " --- |" * len(arms)]
    lines.append("| Runs | " + " | ".join(str(len(rows[a])) for a in arms) + " |")
    for plant in PLANTS:
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
            root = prepare(args.arm, args.directory, args.model, args.skill)
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
