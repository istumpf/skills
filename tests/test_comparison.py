"""Check that the comparison fixture's traps separate correct and naive work."""

from pathlib import Path
import shutil
import tempfile
import unittest

import compare

REFERENCE = compare.HERE / "reference"
NAIVE = REFERENCE / "comparison-naive/invoice.py"
SKILL = compare.HERE.parent / "skills/openspec-stack-apply/SKILL.md"


class ComparisonHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="openspec-compare-harness-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def finished_run(self, arm, implementation, name=""):
        root = compare.prepare(arm, self.base / f"{arm}-{implementation}{name}", "test-model",
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

    def test_each_mutant_fails_only_its_trap(self):
        self.assertEqual(set(compare.MUTANTS), set(compare.TRAPS[1:]))
        self.assertEqual(set(compare.TRAP_GROUPS), set(compare.TRAPS[1:]))
        for trap in compare.MUTANTS:
            results = compare.hidden_traps(compare.mutant_source(trap))
            self.assertEqual([t for t, ok in results.items() if not ok], [trap])

    def test_mutants_measure_the_agents_tests(self):
        weak = compare.score(self.finished_run("single", "comparison"), validate_spec=False)
        self.assertEqual((weak["tests_failing_on_reference"], weak["mutants_killed_count"]), ([], 0))
        root = self.finished_run("single", "comparison", "-strong")
        shutil.copy2(compare.HIDDEN, root / "repo/test_invoice.py")
        # A test stricter than the spec fails on the reference and is set aside.
        (root / "repo/test_strict.py").write_text(
            "import unittest\nimport invoice\nclass Strict(unittest.TestCase):\n"
            "    def test_message(self):\n"
            "        with self.assertRaisesRegex(ValueError, 'expected digits'):\n"
            "            invoice.parse_amount('abc')\n")
        strong = compare.score(root, validate_spec=False)
        self.assertEqual(strong["mutants_killed_count"], strong["mutants_total"])
        self.assertEqual(strong["tests_failing_on_reference"], ["test_strict.Strict.test_message"])
        broken = self.finished_run("single", "comparison", "-broken")
        (broken / "repo/test_invoice.py").write_text(
            "import unittest\nclass Wrong(unittest.TestCase):\n"
            "    def test_fails(self):\n        self.fail()\n")
        result = compare.score(broken, validate_spec=False)
        self.assertEqual(result["tests_failing_on_reference"], ["test_invoice.Wrong.test_fails"])
        self.assertIsNone(result["mutants_killed_count"])

    def test_layers_are_scored_on_the_traps_they_own(self):
        root = self.finished_run("skill", "comparison")
        repo = root / "repo"
        self.assertEqual(compare.score(root, validate_spec=False)["layers"], {})
        # Group 1 lands naive parsing and group 2 fixes it: a lower layer's fix
        # committed on a higher one.
        shutil.copy2(NAIVE, repo / "invoice.py")
        compare.git(repo, "checkout", "-q", "-b", "invoice-totals/1-amount-parsing")
        compare.git(repo, "commit", "-qam", "feat: parsing")
        shutil.copy2(REFERENCE / "comparison/invoice.py", repo / "invoice.py")
        compare.git(repo, "checkout", "-q", "-b", "invoice-totals/2-line-totals")
        compare.git(repo, "commit", "-qam", "feat: line totals")
        layers = compare.score(root, validate_spec=False)["layers"]
        self.assertEqual(layers, {"invoice-totals/1-amount-parsing": ["ExactParsing", "StrictParsing"],
                                  "invoice-totals/2-line-totals": []})
        self.assertIn("| Stacks with every layer clean | 0/1 |", compare.report([root]))

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
