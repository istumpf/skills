"""Exercise the portable harness with local Git and the mock PR service."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import evaluate


class EvaluationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="openspec-harness-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "evaluation"

    def prepare(self, case):
        evaluate.prepare(case, self.root, "test-model")
        self.repo = self.root / "repo"

    def complete_task(self, task):
        metadata = json.loads((self.root / "evaluation.json").read_text())
        path = self.repo / "openspec/changes" / metadata["change"] / "tasks.md"
        path.write_text(path.read_text().replace(f"- [ ] {task}", f"- [x] {task}"))

    def mock(self, *args):
        return evaluate.command([str(self.root / "mock-gh"), *args], self.repo)

    def test_setup_refuses_existing_directory(self):
        self.prepare("default")
        sentinel = self.root / "keep.txt"
        sentinel.write_text("keep")
        with self.assertRaises(FileExistsError):
            evaluate.prepare("default", self.root, "test-model")
        self.assertEqual(sentinel.read_text(), "keep")

    def test_default_verification_preserves_user_files_and_detects_changes(self):
        self.prepare("default")
        for path in (evaluate.HERE / "outputs/default").glob("*.py"):
            shutil.copy2(path, self.repo / path.name)
        for task in ("2.2", "2.3", "3.1", "3.2"):
            self.complete_task(task)
        result = evaluate.verify(self.root, validate_spec=False)
        self.assertEqual(result["tasks"], 6)
        self.assertEqual(result["publication"], "none")
        (self.repo / "notes.txt").write_text("unexpected replacement")
        with self.assertRaisesRegex(ValueError, "Pre-existing file changed"):
            evaluate.verify(self.root, validate_spec=False)

    def publish(self, branch, base, title, body):
        evaluate.git(self.repo, "add", ".")
        evaluate.git(self.repo, "commit", "-m", title)
        evaluate.git(self.repo, "push", "-u", "origin", branch)
        body_path = self.root / (branch + "-body.md")
        body_path.write_text(body)
        return self.mock("pr", "create", "--repo", "fixture/stacked-eval",
                         "--head", branch, "--base", base, "--title", title,
                         "--body-file", str(body_path))

    def test_stacked_publication_and_completed_resume(self):
        self.prepare("stacked-prs")
        evaluate.git(self.repo, "switch", "-c", "group-1", "main")
        (self.repo / "number_helpers.py").write_text("def successor(n):\n    return n + 1\n")
        (self.repo / "test_number_helpers.py").write_text(
            "import unittest\nfrom number_helpers import successor\n"
            "class SuccessorTests(unittest.TestCase):\n"
            "    def test_successor(self):\n        self.assertEqual(successor(-1), 0)\n"
        )
        self.complete_task("1.1")
        first_url = self.publish("group-1", "main", "feat: add successor",
                                 "Add successor.\n\nValidation: unit tests.\n")
        evaluate.git(self.repo, "switch", "-c", "group-2")
        for path in (evaluate.HERE / "outputs/stacked-prs").glob("*.py"):
            shutil.copy2(path, self.repo / path.name)
        self.complete_task("2.1")
        self.publish("group-2", "group-1", "feat: add predecessor",
                     f"Add predecessor.\n\nDepends on {first_url}.\n")
        before = (self.root / "prs.json").read_bytes()
        first = evaluate.verify(self.root, validate_spec=False)
        second = evaluate.verify(self.root, validate_spec=False)
        self.assertEqual(first, second)
        self.assertEqual(before, (self.root / "prs.json").read_bytes())
        duplicate = subprocess.run(
            [str(self.root / "mock-gh"), "pr", "create", "--head", "group-2", "--base", "group-1"],
            cwd=self.repo, capture_output=True, text=True,
        )
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertEqual(before, (self.root / "prs.json").read_bytes())
        self.mock("pr", "edit", "2", "--base", "main")
        with self.assertRaisesRegex(ValueError, "wrong base"):
            evaluate.verify(self.root, validate_spec=False)
