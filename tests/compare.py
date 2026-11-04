#!/usr/bin/env python3
"""Compare ways of applying one OpenSpec change against hidden trap tests.

Arms: `single` applies the change top to bottom with no skill; `skill` applies
it with the SKILL.md given by --skill. The fixture has no remote, so skills that
publish PRs cannot finish here.

prepare: create an isolated run for one arm. score: grade a finished run with
hidden trap tests, the agent's own tests against one mutant per trap, and each
stack layer against the traps its groups own. report: aggregate scored runs by arm.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures/comparison"
HIDDEN = HERE / "hidden/comparison/test_hidden_invoice.py"
REFERENCE = HERE / "reference/comparison/invoice.py"
CHANGE = "invoice-totals"
TASKS = f"openspec/changes/{CHANGE}/tasks.md"
EXPECTED_CHANGES = {"invoice.py", "test_invoice.py", TASKS}
TRAPS = ["SpecScenarios", "ExactParsing", "StrictParsing", "LineHalfUp", "CouponRules",
         "TaxExactHalfUp", "PerLineRounding", "CouponAfterLineDiscounts",
         "GroupedParsingRegression", "NoMutation", "ExistingApi"]
ARMS = ("single", "skill")
# The task group that introduces each trap's rule; a stack layer must pass every
# trap owned by its group or a lower one.
TRAP_GROUPS = {"ExactParsing": 1, "StrictParsing": 1, "ExistingApi": 1, "LineHalfUp": 2,
               "CouponRules": 3, "TaxExactHalfUp": 4, "PerLineRounding": 5,
               "CouponAfterLineDiscounts": 5, "GroupedParsingRegression": 5, "NoMutation": 5}
# One plausible mistake per trap, applied to the reference implementation. The
# offline suite checks that each mutant fails its own trap and no other.
MUTANTS = {
    "ExactParsing": ("return int(whole) * 100 + int(fraction)",
                     'return int(float(f"{whole}.{fraction}") * 100)'),
    "StrictParsing": ('_AMOUNT = re.compile(r"(', '_AMOUNT = re.compile(r"\\+?('),
    "ExistingApi": ("{whole:,}", "{whole}"),
    "LineHalfUp": ("    if discount_percent > 100:\n"
                   '        raise ValueError(f"invalid discount: {discount_percent!r}")\n', ""),
    "CouponRules": ("return min(discount, subtotal_cents)", "return discount"),
    "TaxExactHalfUp": ("return _half_up(taxable_cents * Decimal(rate) / 100)",
                       "return round(taxable_cents * float(rate) / 100)"),
    "PerLineRounding": ('subtotal = sum(line_total(parse_amount(line["price"]), line["quantity"],\n'
                        '                              line.get("discount_percent", 0)) for line in lines)',
                        'subtotal = _half_up(sum(Decimal(parse_amount(line["price"]) * line["quantity"]\n'
                        '                        * (100 - line.get("discount_percent", 0))) / 100 for line in lines))'),
    "CouponAfterLineDiscounts": ("discount = coupon_discount(subtotal, coupon)",
                                 'discount = coupon_discount(sum(parse_amount(line["price"]) * line["quantity"]\n'
                                 '                                   for line in lines), coupon)'),
    "GroupedParsingRegression": (r"(\d{1,3}(?:,\d{3})+|\d+)", r"([\d,]+)"),
    "NoMutation": ('def build_invoice(lines, coupon=None, tax_rate="0"):\n',
                   'def build_invoice(lines, coupon=None, tax_rate="0"):\n'
                   "    for line in lines:\n"
                   '        line.setdefault("discount_percent", 0)\n'),
}


def command(args, cwd):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def git(repo, *args):
    return command(["git", *args], repo)


def markers_by_id(text):
    return {task: mark.lower() for mark, task in
            re.findall(r"^- \[([ xX])\] (\d+\.\d+)\b", text, re.MULTILINE)}


def prepare(arm, directory, model, skill=None):
    if (arm == "skill") != bool(skill):
        raise ValueError("--skill is required for the skill arm and only allowed there")
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
    # A baseline commit lets scoring diff the agent's work, committed or not.
    git(repo, "add", ".")
    git(repo, "commit", "-m", "chore: comparison fixture baseline")
    if arm == "skill":
        prompt = (f"Use the skill at {Path(skill).resolve()} to apply the OpenSpec change "
                  f"{CHANGE}. There is no Git remote; skip any publishing step.")
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
        {"case": "comparison", "arm": arm, "model": model,
         "skill": str(Path(skill).resolve()) if skill else None,
         "baseline": git(repo, "rev-parse", "HEAD")}, indent=2) + "\n")
    return root


def run_tests(cwd, *names):
    try:
        result = subprocess.run([sys.executable, "-E", "-s", "-m", "unittest", *names],
                                cwd=cwd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0


def hidden_traps(source, traps=TRAPS):
    """Run hidden trap classes against one `invoice.py` source; None means no module."""
    with tempfile.TemporaryDirectory(prefix="openspec-compare-") as temp:
        if source is not None:
            Path(temp, "invoice.py").write_text(source)
        shutil.copy2(HIDDEN, temp)
        return {trap: run_tests(temp, f"test_hidden_invoice.{trap}") for trap in traps}


def mutant_source(trap):
    old, new = MUTANTS[trap]
    source = REFERENCE.read_text()
    if source.count(old) != 1:
        raise ValueError(f"mutant {trap} does not match the reference exactly once")
    return source.replace(old, new)


# Prints the ids of failing tests and subtests as a JSON list.
FAILING_TESTS = ("import json, unittest\n"
                 "result = unittest.TestResult()\n"
                 "unittest.defaultTestLoader.discover('.').run(result)\n"
                 "print(json.dumps(sorted(t.id() for t, _ in result.failures + result.errors)))\n")


def failing_tests(tests, source):
    """Ids of the given test files' failures against one `invoice.py`; None on timeout."""
    with tempfile.TemporaryDirectory(prefix="openspec-mutant-") as temp:
        for path in tests:
            shutil.copy2(path, temp)
        Path(temp, "invoice.py").write_text(source)
        try:
            result = subprocess.run([sys.executable, "-E", "-s", "-c", FAILING_TESTS], cwd=temp,
                                    capture_output=True, text=True, timeout=120)
            return set(json.loads(result.stdout.splitlines()[-1]))
        except (subprocess.TimeoutExpired, IndexError, ValueError):
            return None


def mutant_kills(repo):
    """Run the agent's own tests on the reference and on each mutant.

    Tests that fail on the reference (stricter than the spec, or wrong) are set
    aside; a mutant is killed when any other test fails on it. Returns the
    reference failures and the kills, or None for the kills when no test counts.
    """
    tests = sorted(repo.glob("test_*.py"))
    reference = failing_tests(tests, REFERENCE.read_text()) if tests else None
    # Tests that also pass with no implementation prove nothing either.
    without_code = failing_tests(tests, "") if reference is not None else None
    if without_code is None or without_code <= reference:
        return sorted(reference or []), None

    def killed(trap):
        failures = failing_tests(tests, mutant_source(trap))
        return failures is None or bool(failures - reference)

    return sorted(reference), {trap: killed(trap) for trap in MUTANTS}


def committed_source(repo, ref, path="invoice.py"):
    result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=repo,
                            capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def layer_failures(repo):
    """Map each `<change>/<n>-*` branch to the traps owned by groups 1..n it fails."""
    layers = {}
    refs = git(repo, "for-each-ref", "--format=%(refname:short)", f"refs/heads/{CHANGE}/")
    for branch in refs.splitlines():
        match = re.fullmatch(rf"{re.escape(CHANGE)}/(\d+)-.+", branch)
        if match:
            owned = [t for t, group in TRAP_GROUPS.items() if group <= int(match.group(1))]
            results = hidden_traps(committed_source(repo, branch), owned)
            layers[branch] = [t for t in owned if not results[t]]
    return layers


def score(directory, cost=None, minutes=None, validate_spec=True):
    root = Path(directory).resolve()
    metadata = json.loads((root / "evaluation.json").read_text())
    repo = root / "repo"
    saved = root / "score.json"
    previous = json.loads(saved.read_text()) if saved.exists() else {}
    module = repo / "invoice.py"
    traps = hidden_traps(module.read_text() if module.is_file() else None)
    reference_failures, killed = mutant_kills(repo)
    layers = layer_failures(repo)
    own_tests = (repo / "test_invoice.py").is_file() and run_tests(repo, "discover")
    tasks = markers_by_id((repo / TASKS).read_text())
    changed = set(git(repo, "diff", "--name-only", metadata.get("baseline", "HEAD")).splitlines())
    untracked = set(git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    result = {
        "arm": metadata["arm"],
        "model": metadata["model"],
        "traps": traps,
        "traps_passed": sum(traps[t] for t in TRAPS[1:]),
        "traps_total": len(TRAPS) - 1,
        "own_tests_pass": own_tests,
        # Agent tests failing on the reference are set aside for mutant kills.
        "tests_failing_on_reference": reference_failures,
        "mutants_killed": killed,
        "mutants_killed_count": None if killed is None else sum(killed.values()),
        "mutants_total": len(MUTANTS),
        # Empty for runs without stack branches; else failed owned traps per layer.
        "layers": layers,
        "tasks_done": sum(mark == "x" for mark in tasks.values()),
        "tasks_total": len(tasks),
        "out_of_scope": sorted((changed | untracked) - EXPECTED_CHANGES),
        "committed": int(git(repo, "rev-list", "--count", "HEAD")) - 1,
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
        ("Mean tests failing on reference", lambda s: len(s.get("tests_failing_on_reference", []))),
        ("Mean mutants killed", lambda s: s.get("mutants_killed_count")),
        ("Stacks with every layer clean",
         lambda s: int(not any(s["layers"].values())) if s.get("layers") else None),
        ("Mean tasks done", lambda s: s["tasks_done"]),
        ("Runs out of scope", lambda s: int(bool(s["out_of_scope"]))),
        ("Runs that committed", lambda s: int(bool(s["committed"]))),
        ("Mean cost (USD)", lambda s: s.get("cost_usd")),
        ("Mean minutes", lambda s: s["minutes"]),
    ]
    for label, get in metrics:
        if label.startswith("Mean"):
            digits = 2 if "USD" in label else 1
            values = [mean((get(s) for s in rows[a]), digits) for a in arms]
        else:
            counts = [[v for v in map(get, rows[a]) if v is not None] for a in arms]
            values = [f"{sum(c)}/{len(c)}" if c else None for c in counts]
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
    setup.add_argument("--skill", type=Path, help="SKILL.md to apply with (skill arm only)")
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
            root = prepare(args.arm, args.directory, args.model, args.skill)
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
