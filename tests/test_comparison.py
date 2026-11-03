"""Check that the comparison fixture's traps separate correct and naive work."""

from pathlib import Path
import shutil
import tempfile
import unittest

import compare

REFERENCE = compare.HERE / "reference"
SKILL = compare.HERE.parent / "skills/openspec-stack-apply/SKILL.md"


class ComparisonHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="openspec-compare-harness-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def finished_run(self, arm, implementation):
        root = compare.prepare(arm, self.base / f"{arm}-{implementation}", "test-model",
                               SKILL if arm == "skill" else None)
        repo = root / "repo"
        shutil.copy2(REFERENCE / implementation / "invoice.py", repo / "invoice.py")
        (repo / "test_invoice.py").write_text(
            "import unittest\nimport invoice\n"
            "class Smoke(unittest.TestCase):\n"
            "    def test_scenario(self):\n"
            "        self.assertEqual(invoice.parse_amount('7'), 700)\n")
        tasks = repo / compare.TASKS
        tasks.write_text(tasks.read_text().replace("- [ ]", "- [x]"))
        return root

    def test_requests_name_the_skill_only_for_the_skill_arm(self):
        single = compare.prepare("single", self.base / "s", "test-model")
        skilled = compare.prepare("skill", self.base / "k", "test-model", SKILL)
        self.assertIn("Do not spawn subagents", (single / "REQUEST.txt").read_text())
        self.assertIn(str(SKILL), (skilled / "REQUEST.txt").read_text())
        self.assertFalse((single / "repo/test_hidden_invoice.py").exists())
        with self.assertRaises(ValueError):
            compare.prepare("skill", self.base / "missing", "test-model")
        with self.assertRaises(ValueError):
            compare.prepare("single", self.base / "extra", "test-model", SKILL)

    def test_committed_work_is_scored_against_the_baseline(self):
        root = self.finished_run("skill", "comparison")
        compare.git(root / "repo", "add", ".")
        compare.git(root / "repo", "commit", "-m", "feat: apply invoice-totals")
        result = compare.score(root, validate_spec=False)
        self.assertEqual(result["traps_passed"], result["traps_total"])
        self.assertEqual(result["out_of_scope"], [])
        self.assertEqual(result["committed"], 1)

    def test_reference_passes_every_trap(self):
        result = compare.score(self.finished_run("single", "comparison"), validate_spec=False)
        self.assertTrue(all(result["traps"].values()), result["traps"])
        self.assertEqual(result["traps_passed"], result["traps_total"])
        self.assertTrue(result["own_tests_pass"])
        self.assertEqual(result["tasks_done"], result["tasks_total"])
        self.assertEqual(result["out_of_scope"], [])
        self.assertEqual(result["committed"], 0)

    def test_naive_passes_scenarios_but_fails_each_trap(self):
        result = compare.score(self.finished_run("skill", "comparison-naive"),
                               validate_spec=False)
        self.assertTrue(result["traps"]["SpecScenarios"])
        self.assertTrue(result["traps"]["ExistingApi"])
        failed = [t for t in compare.TRAPS if not result["traps"][t]]
        self.assertEqual(sorted(failed), sorted(set(compare.TRAPS) - {"SpecScenarios", "ExistingApi"}))

    def test_scope_and_report(self):
        good = self.finished_run("single", "comparison")
        (good / "repo/notes.txt").write_text("overwritten")
        compare.score(good, cost=0.2, minutes=4, validate_spec=False)
        naive = self.finished_run("skill", "comparison-naive")
        compare.score(naive, cost=0.4, minutes=10, validate_spec=False)
        self.assertEqual(compare.score(good, validate_spec=False)["out_of_scope"], ["notes.txt"])
        table = compare.report([good, naive])
        self.assertIn("| Metric | single | skill |", table)
        self.assertIn("| ExactParsing | 1/1 | 0/1 |", table)
        self.assertIn("| Mean cost (USD) | 0.2 | 0.4 |", table)

    def test_reads_claude_result(self):
        path = self.base / "result.json"
        path.write_text('{"total_cost_usd": 0.4159, "duration_ms": 15860}')
        self.assertEqual(compare.claude_result_cost(path), 0.4159)
