#!/usr/bin/env python3
"""Prepare isolated skill evaluations and verify their observable outcomes."""

import argparse
import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "skills/openspec-orchestrate/SKILL.md"
CASES = {
    "default": ("normalize-tags", "tags.py", "test_tags.py"),
    "stacked-prs": ("number-helpers", "number_helpers.py", "test_number_helpers.py"),
}


def command(args, cwd):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def git(repo, *args):
    return command(["git", *args], repo)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare(case, directory, model):
    root = Path(directory).resolve()
    root.mkdir(parents=True)  # Refuse to replace an existing evaluation.
    repo = root / "repo"
    shutil.copytree(HERE / "fixtures" / case, repo)
    git(repo, "init", "--initial-branch=main")
    git(repo, "config", "user.name", "Skill Evaluation")
    git(repo, "config", "user.email", "skill-evaluation@example.invalid")
    git(repo, "config", "commit.gpgsign", "false")
    # These generated repositories must not inherit user Git hooks.
    (root / "empty-hooks").mkdir()
    git(repo, "config", "core.hooksPath", str(root / "empty-hooks"))
    change = CASES[case][0]
    prompt = (
        f"Use $openspec-orchestrate at {SKILL} to apply {change} "
        f"using worker model {model}"
    )
    initial_commit = None
    if case == "stacked-prs":
        git(repo, "add", ".")
        git(repo, "commit", "-m", "feat: initialize evaluation fixture")
        initial_commit = git(repo, "rev-parse", "HEAD")
        git(repo, "init", "--bare", "--initial-branch=main", str(root / "remote.git"))
        git(repo, "remote", "add", "origin", str(root / "remote.git"))
        git(repo, "push", "-u", "origin", "main")
        git(repo, "switch", "-c", "placeholder")
        shutil.copy2(HERE / "mock-gh", root / "mock-gh")
        (root / "mock-gh").chmod(0o755)
        prompt += (
            " with one stacked PR per group. Target base: main. "
            "Publication remote: origin. Logical repository: fixture/stacked-eval.\n\n"
            f"The only permitted PR interface is {root / 'mock-gh'}, a local mock "
            "of gh. Use that executable instead of real gh or any connected PR "
            f"service. Push only to the existing local origin, {root / 'remote.git'}. "
            "Do not create real PRs or contact other remotes."
        )
    else:
        prompt += ". Complete all remaining groups using the default mode."
    prompt += (
        f"\n\nWork in {repo}. All writes must remain inside {root}. "
        "Read AGENTS.md and report worker assignments, review outcomes, checks, "
        "and any blockers. Do not modify the skill under evaluation.\n"
    )
    (root / "REQUEST.txt").write_text(prompt)
    (root / "evaluation.json").write_text(json.dumps({
        "case": case, "change": change, "model": model,
        "initial_commit": initial_commit,
    }, indent=2) + "\n")
    return root


def markers_by_id(text):
    return {task: mark.lower() for mark, task in
            re.findall(r"^- \[([ xX])\] (\d+\.\d+)\b", text, re.MULTILINE)}


def verify(directory, validate_spec=True):
    root = Path(directory).resolve()
    metadata = json.loads((root / "evaluation.json").read_text())
    case = metadata["case"]
    change, module, test_file = CASES[case]
    repo = root / "repo"
    fixture = HERE / "fixtures" / case
    tasks = Path("openspec/changes") / change / "tasks.md"
    initial_tasks = markers_by_id((fixture / tasks).read_text())
    final_tasks = markers_by_id((repo / tasks).read_text())
    require(final_tasks == {task: "x" for task in initial_tasks},
            "Original task IDs must all be complete, without additions or omissions")
    normalize = lambda text: re.sub(r"^- \[[ xX]\]", "- [ ]", text, flags=re.MULTILINE)
    require(normalize((repo / tasks).read_text()) == normalize((fixture / tasks).read_text()),
            "Task descriptions changed")
    require((repo / test_file).is_file(), "Expected implementation tests are missing")
    for path in fixture.rglob("*"):
        if path.is_file() and path.relative_to(fixture).as_posix() not in (module, tasks.as_posix()):
            actual = repo / path.relative_to(fixture)
            require(actual.is_file() and actual.read_bytes() == path.read_bytes(),
                    f"Pre-existing file changed: {path.relative_to(fixture)}")
    # Execute preserved behavior checks against the new candidate, not its claims.
    with tempfile.TemporaryDirectory(prefix="openspec-behavior-") as temp:
        check = Path(temp)
        shutil.copy2(repo / module, check / module)
        shutil.copy2(HERE / "outputs" / case / test_file, check / test_file)
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=check, check=True)
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=repo, check=True)
    if validate_spec:
        subprocess.run(["openspec", "validate", change, "--type", "change", "--strict", "--no-interactive"],
                       cwd=repo, check=True)
        state = json.loads(command(["openspec", "instructions", "apply", "--change", change, "--json"], repo))
        require(state["state"] == "all_done", "OpenSpec still reports pending work")

    if case == "default":
        require(not git_has_heads(repo), "Default evaluation unexpectedly created a commit")
        require(not git(repo, "remote"), "Default evaluation unexpectedly added a remote")
        require(git(repo, "branch", "--show-current") == "main", "Default branch changed")
        require(not git(repo, "ls-files"), "Default evaluation unexpectedly staged files")
        return {"case": case, "tasks": len(final_tasks), "publication": "none"}

    require(git(repo, "remote", "get-url", "origin") == str(root / "remote.git"), "Origin changed")
    prs = json.loads(command([str(root / "mock-gh"), "pr", "list", "--state", "all"], repo))
    require(len(prs) == 2 and len({pr["number"] for pr in prs}) == 2, "Expected exactly two distinct PRs")
    require(len({pr["headRefName"] for pr in prs}) == 2, "PR heads must be distinct")
    base = "main"
    heads = []
    for index, pr in enumerate(prs, start=1):
        head = pr["headRefName"]
        require(pr["baseRefName"] == base, f"PR {index} has the wrong base")
        require(pr["state"] == "OPEN", "Evaluation must not merge or close PRs")
        sha = git(repo, "rev-parse", head)
        remote_sha = command(["git", "--git-dir", str(root / "remote.git"), "rev-parse", "refs/heads/" + head], root)
        require(sha == remote_sha == pr["headRefOid"], f"PR {index} branch is not fully pushed")
        subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=repo, check=True)
        changed = set(git(repo, "diff", "--name-only", base + "..." + head).splitlines())
        require(changed == {module, test_file, tasks.as_posix()}, f"PR {index} has unexpected scope: {changed}")
        expected = {"1.1": "x", "2.1": " " if index == 1 else "x"}
        require(markers_by_id(git(repo, "show", head + ":" + tasks.as_posix())) == expected,
                f"PR {index} has incorrect group completion markers")
        source = ast.parse(git(repo, "show", head + ":" + module))
        functions = {node.name for node in source.body if isinstance(node, ast.FunctionDef)}
        require("successor" in functions and ("predecessor" in functions) == (index == 2),
                f"PR {index} includes the wrong group's API")
        if index > 1:
            require(prs[index - 2]["url"] in pr["body"], "Missing predecessor PR link")
        require("\n\n" in pr["body"], "PR body should retain paragraph breaks")
        heads.append((head, sha))
        base = head
    require(git(repo, "rev-parse", "main") == metadata["initial_commit"], "Base branch changed")
    require(git(repo, "rev-parse", "placeholder") == metadata["initial_commit"], "Original branch changed")
    require(git(repo, "branch", "--show-current") == base, "Topmost PR branch must remain checked out")
    require(not git(repo, "status", "--porcelain"), "Stacked evaluation worktree is dirty")
    fingerprint = {"heads": heads, "prs": [(p["number"], p["headRefName"], p["baseRefName"]) for p in prs],
                   "tasks": final_tasks, "branches": git(repo, "show-ref", "--heads")}
    fingerprint = json.loads(json.dumps(fingerprint))
    saved = root / "verified-completion.json"
    if saved.exists():
        require(json.loads(saved.read_text()) == fingerprint, "Completed-run resume changed commits, branches, PRs, or tasks")
    else:
        saved.write_text(json.dumps(fingerprint, indent=2) + "\n")
    return {"case": case, "tasks": len(final_tasks), "prs": len(prs), "top_branch": base}


def git_has_heads(repo):
    result = subprocess.run(["git", "show-ref", "--heads", "--quiet"], cwd=repo)
    if result.returncode not in (0, 1):
        raise RuntimeError("Cannot inspect evaluation branches")
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("case", choices=CASES)
    setup.add_argument("--directory", type=Path, required=True)
    setup.add_argument("--model", required=True)
    check = commands.add_parser("verify")
    check.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            root = prepare(args.case, args.directory, args.model)
            print(f"Prepared {root / 'repo'}\nGive the orchestrator {root / 'REQUEST.txt'}")
        else:
            print(json.dumps(verify(args.directory), indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Evaluation failed: {error}\n")


if __name__ == "__main__":
    main()
