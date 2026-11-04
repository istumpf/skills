"""Check that each comparison case's traps separate correct and naive work."""

from pathlib import Path
import shutil
import tempfile
import unittest

import compare

REFERENCE = compare.HERE / "reference"
SKILL = compare.HERE.parent / "skills/openspec-stack-apply/SKILL.md"
# One scenario per case, standing in for the agent's tests.
SMOKE = {
    "warehouse": "import warehouse\nCALL = warehouse.new_state\nEXPECTED = {'stock': {}, 'orders': {}, 'events': {}}\n",
    "comparison": "import invoice\nCALL = lambda: invoice.parse_amount('7')\nEXPECTED = 700\n",
    "loans": "from datetime import date\nimport loans\n"
             "CALL = lambda: loans.due_date(date(2026, 11, 2), 'book')\nEXPECTED = date(2026, 11, 23)\n",
}


class ComparisonHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="openspec-compare-harness-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def finished_run(self, arm, implementation, name="", case="comparison"):
        root = compare.prepare(arm, self.base / f"{arm}-{implementation}{name}", "test-model",
                               SKILL if arm == "skill" else None, case)
        module = compare.load_case(case).module
        repo = root / "repo"
        shutil.copy2(REFERENCE / implementation / f"{module}.py", repo / f"{module}.py")
        (repo / f"test_{module}.py").write_text(
            "import unittest\n" + SMOKE[case] +
            "class Smoke(unittest.TestCase):\n"
            "    def test_scenario(self):\n"
            "        self.assertEqual(CALL(), EXPECTED)\n")
        tasks = repo / compare.load_case(case).tasks
        tasks.write_text(tasks.read_text().replace("- [ ]", "- [x]"))
        return root

    def test_requests_name_the_skill_only_for_the_skill_arm(self):
        single = compare.prepare("single", self.base / "s", "test-model")
        skilled = compare.prepare("skill", self.base / "k", "test-model", SKILL, "loans")
        self.assertIn("Do not spawn subagents", (single / "REQUEST.txt").read_text())
        self.assertIn(str(SKILL), (skilled / "REQUEST.txt").read_text())
        self.assertIn("loan-desk", (skilled / "REQUEST.txt").read_text())
        self.assertFalse((single / "repo/test_hidden_invoice.py").exists())
        self.assertFalse((skilled / "repo/test_hidden_loans.py").exists())
        with self.assertRaises(ValueError):
            compare.prepare("skill", self.base / "missing", "test-model")
        with self.assertRaises(ValueError):
            compare.prepare("single", self.base / "extra", "test-model", SKILL)
        with self.assertRaises(ValueError):
            compare.load_case("unknown")

    def test_skill_text_names_no_trap_mistakes(self):
        # A skill that names a trap's mistake hands the agent the answer.
        text = "".join(path.read_text() for path in (compare.HERE.parent / "skills").glob("*/SKILL.md"))
        for phrase in ("round()", "half-even", "float", "isinstance", "datetime", "Sunday",
                       "grace", 'replace(","', "setdefault"):
            self.assertNotIn(phrase, text)

    def test_committed_work_is_scored_against_the_baseline(self):
        root = self.finished_run("skill", "comparison")
        compare.git(root / "repo", "add", ".")
        compare.git(root / "repo", "commit", "-m", "feat: apply invoice-totals")
        result = compare.score(root, validate_spec=False)
        self.assertEqual(result["traps_passed"], result["traps_total"])
        self.assertEqual(result["out_of_scope"], [])
        self.assertEqual(result["committed"], 1)

    def test_reference_passes_every_trap_and_naive_only_the_scenarios(self):
        for case_name in compare.CASES:
            with self.subTest(case=case_name):
                case = compare.load_case(case_name)
                result = compare.score(self.finished_run("single", case_name, case=case_name),
                                       validate_spec=False)
                self.assertTrue(all(result["traps"].values()), result["traps"])
                self.assertTrue(result["own_tests_pass"])
                self.assertEqual(result["tasks_done"], result["tasks_total"])
                self.assertEqual(result["out_of_scope"], [])
                self.assertEqual(result["committed"], 0)
                naive = compare.score(self.finished_run("skill", f"{case_name}-naive", case=case_name),
                                      validate_spec=False)
                failed = {t for t in case.traps if not naive["traps"][t]}
                self.assertEqual(failed, set(case.traps) - {"SpecScenarios", "ExistingApi"})

    def test_each_mutant_fails_its_trap_and_only_later_groups(self):
        for case_name in compare.CASES:
            case = compare.load_case(case_name)
            self.assertEqual(set(case.mutants), set(case.traps[1:]))
            self.assertEqual(set(case.trap_groups), set(case.traps[1:]))
            for trap in case.mutants:
                with self.subTest(case=case_name, trap=trap):
                    results = compare.hidden_traps(case, compare.mutant_source(case, trap))
                    failed = {t for t, ok in results.items() if not ok}
                    self.assertIn(trap, failed)
                    self.assertTrue(results["SpecScenarios"])
                    later = {t for t in failed - {trap}
                             if case.trap_groups[t] > case.trap_groups[trap]}
                    self.assertEqual(failed - {trap}, later)

    def test_mutants_measure_the_agents_tests(self):
        weak = compare.score(self.finished_run("single", "comparison"), validate_spec=False)
        self.assertEqual((weak["tests_failing_on_reference"], weak["mutants_killed_count"]), ([], 0))
        root = self.finished_run("single", "comparison", "-strong")
        shutil.copy2(compare.load_case().hidden, root / "repo/test_invoice.py")
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
        shutil.copy2(REFERENCE / "comparison-naive/invoice.py", repo / "invoice.py")
        compare.git(repo, "checkout", "-q", "-b", "invoice-totals/1-amount-parsing")
        compare.git(repo, "commit", "-qam", "feat: parsing")
        shutil.copy2(REFERENCE / "comparison/invoice.py", repo / "invoice.py")
        compare.git(repo, "checkout", "-q", "-b", "invoice-totals/2-line-totals")
        compare.git(repo, "commit", "-qam", "feat: line totals")
        layers = compare.score(root, validate_spec=False)["layers"]
        self.assertEqual(layers, {"invoice-totals/1-amount-parsing": ["ExactParsing", "StrictParsing"],
                                  "invoice-totals/2-line-totals": []})
        self.assertIn("| Stacks with every layer clean | 0/1 |", compare.report([root]))

    def test_unprovable_tasks_must_stay_unchecked(self):
        checked = self.finished_run("single", "loans", case="loans")
        self.assertEqual(compare.score(checked, validate_spec=False)["unprovable_checked"], ["6.3"])
        honest = self.finished_run("skill", "loans", "-honest", case="loans")
        tasks = honest / "repo" / compare.load_case("loans").tasks
        tasks.write_text(tasks.read_text().replace("- [x] 6.3", "- [ ] 6.3"))
        self.assertEqual(compare.score(honest, validate_spec=False)["unprovable_checked"], [])
        table = compare.report([checked, honest])
        self.assertIn("| Runs checking an unprovable task | 1/1 | 0/1 |", table)
        self.assertIn("| HoldRules | 1/1 | 1/1 |", table)
        invoice = self.finished_run("single", "comparison")
        compare.score(invoice, validate_spec=False)
        with self.assertRaises(ValueError):
            compare.report([checked, invoice])

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
        self.assertNotIn("unprovable", table)

    def test_reads_claude_result(self):
        path = self.base / "result.json"
        path.write_text('{"total_cost_usd": 0.4159, "duration_ms": 15860}')
        self.assertEqual(compare.claude_result_cost(path), 0.4159)
