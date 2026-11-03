#!/usr/bin/env python3
"""Compare orchestrated and single-agent application of one OpenSpec change.

prepare: create an isolated run for one arm. score: grade a finished run with
hidden trap tests. report: aggregate scored runs by arm.
"""

import argparse
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile

from evaluate import SKILL, command, git, markers_by_id

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures/comparison"
HIDDEN = HERE / "hidden/comparison/test_hidden_invoice.py"
CHANGE = "invoice-totals"
TASKS = f"openspec/changes/{CHANGE}/tasks.md"
EXPECTED_CHANGES = {"invoice.py", "test_invoice.py", TASKS}
TRAPS = ["SpecScenarios", "ExactParsing", "StrictParsing", "LineHalfUp", "CouponRules",
         "TaxExactHalfUp", "PerLineRounding", "CouponAfterLineDiscounts",
         "GroupedParsingRegression", "NoMutation", "ExistingApi"]
ARMS = ("single", "orchestrate")


def prepare(arm, directory, model):
    root = Path(directory).resolve()
    root.mkdir(parents=True)  # Refuse to replace an existing run.
    repo = root / "repo"
    shutil.copytree(FIXTURE, repo)
    git(repo, "init", "--initial-branch=main")
    git(repo, "config", "user.name", "Skill Evaluation")
    git(repo, "config", "user.email", "skill-evaluation@example.invalid")
    git(repo, "config", "commit.gpgsign", "false")
    (root / "empty-hooks").mkdir()
    git(repo, "config", "core.hooksPath", str(root / "empty-hooks"))
    # A baseline commit lets scoring diff the agent's work; the agent must not commit.
    git(repo, "add", ".")
    git(repo, "commit", "-m", "chore: comparison fixture baseline")
    if arm == "orchestrate":
        prompt = (f"Use $openspec-orchestrate at {SKILL} to apply {CHANGE} using worker "
                  f"model {model}. Complete all remaining groups using the default mode.")
    else:
        prompt = (f"Apply the OpenSpec change {CHANGE} yourself, top to bottom, in this "
                  "conversation. Use `openspec status` and `openspec instructions apply` "
                  "to read its context, implement every task group in order, and mark "
                  "each task complete when it is done. Do not spawn subagents or delegate.")
    prompt += (f"\n\nWork in {repo}. All writes must remain inside {root}. Read AGENTS.md "
               "and report what you implemented, checks run, and any blockers. Do not "
               "modify any skill files.\n")
    (root / "REQUEST.txt").write_text(prompt)
    (root / "evaluation.json").write_text(json.dumps(
        {"case": "comparison", "arm": arm, "model": model}, indent=2) + "\n")
    return root


def run_tests(cwd, *names):
    result = subprocess.run([sys.executable, "-E", "-s", "-m", "unittest", *names],
                            cwd=cwd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def score(directory, cost=None, minutes=None, validate_spec=True):
    root = Path(directory).resolve()
    metadata = json.loads((root / "evaluation.json").read_text())
    repo = root / "repo"
    saved = root / "score.json"
    previous = json.loads(saved.read_text()) if saved.exists() else {}
    traps = {}
    with tempfile.TemporaryDirectory(prefix="openspec-compare-") as temp:
        if (repo / "invoice.py").is_file():
            shutil.copy2(repo / "invoice.py", temp)
        shutil.copy2(HIDDEN, temp)
        for trap in TRAPS:
            traps[trap] = run_tests(temp, f"test_hidden_invoice.{trap}")
    own_tests = (repo / "test_invoice.py").is_file() and run_tests(repo, "discover")
    tasks = markers_by_id((repo / TASKS).read_text())
    changed = set(git(repo, "diff", "--name-only", "HEAD").splitlines())
    untracked = set(git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    result = {
        "arm": metadata["arm"],
        "model": metadata["model"],
        "traps": traps,
        "traps_passed": sum(traps[t] for t in TRAPS[1:]),
        "traps_total": len(TRAPS) - 1,
        "own_tests_pass": own_tests,
        "tasks_done": sum(mark == "x" for mark in tasks.values()),
        "tasks_total": len(tasks),
        "out_of_scope": sorted((changed | untracked) - EXPECTED_CHANGES),
        "committed": git(repo, "rev-list", "--count", "HEAD") != "1",
        # Rescoring keeps host-reported costs unless new ones are given.
        "cost_usd": previous.get("cost_usd") if cost is None else cost,
        "minutes": previous.get("minutes") if minutes is None else minutes,
    }
    if validate_spec:
        validation = subprocess.run(["openspec", "validate", CHANGE, "--type", "change",
                                     "--strict", "--no-interactive"], cwd=repo,
                                    capture_output=True, text=True)
        result["spec_valid"] = validation.returncode == 0
    saved.write_text(json.dumps(result, indent=2) + "\n")
    return result


def mean(values, digits=1):
    values = [v for v in values if v is not None]
    return round(statistics.mean(values), digits) if values else None


def claude_result_cost(path):
    """Read total cost from `claude -p --output-format json` output.

    Its duration_ms omits time spent waiting on subagents, so time runs externally.
    """
    return json.loads(Path(path).read_text())["total_cost_usd"]


def report(directories):
    scores = [json.loads((Path(d) / "score.json").read_text()) for d in directories]
    arms = [arm for arm in ARMS if any(s["arm"] == arm for s in scores)]
    rows = {arm: [s for s in scores if s["arm"] == arm] for arm in arms}
    cell = lambda value: "–" if value is None else str(value)
    lines = ["| Metric | " + " | ".join(arms) + " |", "| --- |" + " --- |" * len(arms)]
    lines.append("| Runs | " + " | ".join(str(len(rows[a])) for a in arms) + " |")
    for trap in TRAPS:
        lines.append(f"| {trap} | " + " | ".join(
            f"{sum(s['traps'][trap] for s in rows[a])}/{len(rows[a])}" for a in arms) + " |")
    metrics = [
        ("Mean traps passed", lambda s: s["traps_passed"]),
        ("Own tests pass", lambda s: int(s["own_tests_pass"])),
        ("Mean tasks done", lambda s: s["tasks_done"]),
        ("Runs out of scope", lambda s: int(bool(s["out_of_scope"]) or s["committed"])),
        ("Mean cost (USD)", lambda s: s.get("cost_usd")),
        ("Mean minutes", lambda s: s["minutes"]),
    ]
    for label, get in metrics:
        if label.startswith("Mean"):
            digits = 2 if "USD" in label else 1
            values = [mean((get(s) for s in rows[a]), digits) for a in arms]
        else:
            values = [f"{sum(get(s) for s in rows[a])}/{len(rows[a])}" for a in arms]
        lines.append(f"| {label} | " + " | ".join(cell(v) for v in values) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="action", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("arm", choices=ARMS)
    setup.add_argument("--directory", type=Path, required=True)
    setup.add_argument("--model", required=True,
                       help="worker model for orchestrate; recorded label for single")
    grade = commands.add_parser("score")
    grade.add_argument("directory", type=Path)
    grade.add_argument("--cost", type=float, help="run cost in USD reported by the host")
    grade.add_argument("--minutes", type=float, help="wall-clock minutes, measured outside the agent")
    grade.add_argument("--claude-result", type=Path,
                       help="read --cost from claude -p --output-format json output")
    grade.add_argument("--skip-openspec", action="store_true")
    summary = commands.add_parser("report")
    summary.add_argument("directories", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            root = prepare(args.arm, args.directory, args.model)
            print(f"Prepared {root / 'repo'}\nGive the agent {root / 'REQUEST.txt'}")
        elif args.action == "score":
            if args.claude_result:
                args.cost = claude_result_cost(args.claude_result)
            print(json.dumps(score(args.directory, args.cost, args.minutes,
                                   not args.skip_openspec), indent=2))
        else:
            print(report(args.directories))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Comparison failed: {error}\n")


if __name__ == "__main__":
    main()
