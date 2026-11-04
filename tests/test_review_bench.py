"""Check that the review benchmark plants what it claims and scores findings."""

from datetime import date, datetime
import json
from pathlib import Path
import tempfile
import unittest

import compare
import review_bench

SKILL = compare.HERE.parent / "skills/stacked-pr-feedback/SKILL.md"
INVOICE = review_bench.STACKS["invoice"]
LOANS = review_bench.STACKS["loans"]
# Hidden traps each layer fails: planted defects that change behavior, and
# their effect on later traps.
EXPECTED_FAILURES = {
    "invoice": {1: [], 2: ["LineHalfUp"], 3: ["LineHalfUp", "CouponRules"],
                4: ["LineHalfUp", "CouponRules"],
                # Layer 2's half-even rounding also breaks per-line rounding.
                5: ["LineHalfUp", "PerLineRounding", "GroupedParsingRegression"]},
    # Layer 2's restated rule and the layer-4 exception type change no trap
    # that layer 4 does not already fail; they are design and spec fit only.
    "loans": {1: [], 2: [], 3: [], 4: ["RenewalLimit"], 5: ["RenewalLimit", "HoldRules"],
              6: ["RenewalLimit", "HoldRules", "ReceiptCrossGroup"]},
}


class ReviewBenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="review-bench-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def finding(self, stack, layer, path, body):
        return {"branch": review_bench.branches(stack)[layer - 1], "path": path, "line": 1, "body": body}

    def module_at(self, repo, stack, layer):
        namespace = {}
        exec(compare.committed_source(repo, review_bench.branches(stack)[layer - 1],
                                      f"{stack.case.module}.py"), namespace)
        return namespace

    def test_layers_pass_their_tests_and_fail_only_planted_traps(self):
        for name, stack in review_bench.STACKS.items():
            with self.subTest(stack=name):
                repo = review_bench.prepare("plain", self.base / name, "test-model", stack_name=name) / "repo"
                failures = compare.layer_failures(stack.case, repo)
                self.assertEqual({int(b.split("/")[1].split("-")[0]): f for b, f in failures.items()},
                                 EXPECTED_FAILURES[name])
                module = stack.case.module
                for branch in review_bench.branches(stack):
                    with tempfile.TemporaryDirectory() as temp:
                        for path in (f"{module}.py", f"test_{module}.py"):
                            Path(temp, path).write_text(compare.committed_source(repo, branch, path))
                        self.assertTrue(compare.run_tests(temp, "discover"), branch)
                self.assertEqual(compare.git(repo, "branch", "--show-current"),
                                 review_bench.branches(stack)[-1])
                tasks = compare.markers_by_id((repo / stack.case.tasks).read_text())
                self.assertTrue(all(mark == "x" for mark in tasks.values()))

    def test_invoice_plants_and_decoys(self):
        repo = review_bench.prepare("plain", self.base / "run", "test-model") / "repo"
        self.assertIn("notes.txt", compare.git(repo, "diff", "--name-only",
                                               "main", review_bench.branches(INVOICE)[0]))
        tax = compare.committed_source(repo, review_bench.branches(INVOICE)[3], "invoice.py")
        self.assertTrue(compare.hidden_traps(INVOICE.case, tax, ["TaxExactHalfUp"])["TaxExactHalfUp"])
        coupon_discount = self.module_at(repo, INVOICE, 3)["coupon_discount"]
        for subtotal, value, expected in ((5, 50, 3), (2000, 15, 300), (1, 50, 1), (3, 50, 2)):
            self.assertEqual(coupon_discount(subtotal, {"type": "percent", "value": value}), expected)

    def test_loans_plants_and_decoys(self):
        repo = review_bench.prepare("plain", self.base / "run", "test-model", stack_name="loans") / "repo"
        layer = lambda n: self.module_at(repo, LOANS, n)
        # design-reuse: same answers as is_open, but the rule is restated.
        overdue = compare.committed_source(repo, review_bench.branches(LOANS)[1], "loans.py")
        self.assertIn("day.weekday() != 6 and day not in HOLIDAYS:\n            days", overdue)
        self.assertTrue(compare.hidden_traps(LOANS.case, overdue, ["OpenDaysOnly"])["OpenDaysOnly"])
        # exception-type: renewals raise an error the spec does not name.
        renewals = layer(4)
        self.assertFalse(issubclass(renewals["RenewalError"], ValueError))
        # spec-tampering: the layer allows a third renewal and edits the spec to match.
        spec = LOANS.case.tasks.replace("tasks.md", "specs/loan-desk/spec.md")
        self.assertIn("three times", compare.committed_source(repo, review_bench.branches(LOANS)[3], spec))
        self.assertIn("renewed twice", compare.committed_source(repo, "main", spec))
        third = {"kind": "book", "due": date(2026, 11, 23), "renewals": 2, "patron": "ana"}
        self.assertEqual(renewals["renew"](third, date(2026, 11, 23))["renewals"], 3)
        # signature-mismatch: place_hold takes (patron, holds).
        self.assertEqual(layer(5)["place_hold"]("bo", ("ana",)), ("ana", "bo"))
        # silent-spec-change: a loan due before today with no fine is not counted.
        free = {"kind": "book", "due": date(2026, 11, 28), "renewals": 0, "patron": "ana"}
        self.assertEqual(layer(6)["receipt"]([free], date(2026, 11, 30))["overdue_items"], 0)
        # Decoys: the exact type check and the closed-day loop are correct.
        first = layer(1)
        with self.assertRaises(TypeError):
            first["due_date"](datetime(2026, 11, 2, 9), "book")
        self.assertEqual(first["due_date"](date(2026, 12, 18), "dvd"), date(2026, 12, 28))

    def test_requests_name_the_skill_only_for_the_skill_arm(self):
        plain = review_bench.prepare("plain", self.base / "p", "test-model")
        skilled = review_bench.prepare("skill", self.base / "k", "test-model", SKILL, "loans")
        self.assertIn("Do not spawn subagents", (plain / "REQUEST.txt").read_text())
        self.assertIn(str(SKILL), (skilled / "REQUEST.txt").read_text())
        self.assertIn("as of `main`", (skilled / "REQUEST.txt").read_text())
        self.assertNotIn("as of `main`", (plain / "REQUEST.txt").read_text())
        for root in (plain, skilled):
            request = (root / "REQUEST.txt").read_text().lower()
            for word in ("plant", "decoy", "half-even", "notes.txt", "renewalerror", "is_open"):
                self.assertNotIn(word, request)
        with self.assertRaises(ValueError):
            review_bench.prepare("skill", self.base / "missing", "test-model")
        with self.assertRaises(ValueError):
            review_bench.prepare("plain", self.base / "unknown", "test-model", stack_name="other")

    def test_scores_plants_decoys_and_labels(self):
        root = review_bench.prepare("skill", self.base / "run", "test-model", SKILL)
        findings = [
            self.finding(INVOICE, 2, "invoice.py", "round() on a Decimal is half-even, not half up"),
            self.finding(INVOICE, 5, "invoice.py", "Coupon cap belongs to layer 3; min() was added here"),
            self.finding(INVOICE, 1, "notes.txt", "Unrelated edit"),
            self.finding(INVOICE, 5, "invoice.py", "Stripping every comma accepts 1,23"),
            self.finding(INVOICE, 4, "invoice.py", "The +50 // 100 trick may not round half up"),
            self.finding(INVOICE, 3, "test_invoice.py", "Missing a test for zero subtotal"),
            self.finding(INVOICE, 5, "invoice.py", "Unknown coupon type message could be clearer"),
            # Right defect, wrong layer: not credited.
            self.finding(INVOICE, 4, "invoice.py", "Separators accepted loosely"),
        ]
        (root / "findings.json").write_text(json.dumps({"findings": findings}))
        # Index 1 overridden: real, but credited to no plant.
        (root / "labels.json").write_text('{"5": true, "1": {"plants": [], "real": true}}')
        result = review_bench.score(root, cost=0.3, minutes=2)
        self.assertEqual(result["plants"], {**dict.fromkeys(INVOICE.plants, True),
                                            "coupon-cap-wrong-layer": False})
        self.assertEqual(result["recall"], 0.75)
        self.assertEqual((result["true_positives"], result["false_positives"]), (5, 3))
        self.assertEqual(result["precision"], 0.62)
        self.assertNotIn("1", result["matched"])
        self.assertEqual(result["matched"]["3"], ["grouping-regression"])
        self.assertEqual(result["decoy_hits"], [4])
        self.assertEqual([u["index"] for u in result["unmatched"]], [6, 7])
        self.assertTrue(result["repo_unchanged"])

        empty = review_bench.prepare("plain", self.base / "empty", "test-model")
        compare.git(empty / "repo", "checkout", "-q", "main")
        result = review_bench.score(empty)
        self.assertEqual((result["recall"], result["precision"]), (0.0, None))
        self.assertFalse(result["repo_unchanged"])
        table = review_bench.report([root, empty])
        self.assertIn("| Metric | plain | skill |", table)
        self.assertIn("| scope-leak | 0/1 | 1/1 |", table)
        self.assertIn("| coupon-cap-wrong-layer | 0/1 | 0/1 |", table)
        self.assertIn("| Mean precision | – | 0.62 |", table)
        self.assertIn("| Runs leaving the repo unchanged | 0/1 | 1/1 |", table)

    def test_scores_loans_plants(self):
        root = review_bench.prepare("skill", self.base / "run", "test-model", SKILL, "loans")
        spec = "openspec/changes/loan-desk/specs/loan-desk/spec.md"
        findings = [
            self.finding(LOANS, 2, "loans.py", "days_overdue restates the Sunday rule instead of calling is_open"),
            self.finding(LOANS, 4, "loans.py", "renew raises RenewalError; the spec requires ValueError"),
            self.finding(LOANS, 4, spec, "The layer rewrites the requirement to allow a third renewal"),
            self.finding(LOANS, 5, "loans.py", "place_hold takes its arguments in the wrong order"),
            self.finding(LOANS, 6, "loans.py", "overdue_items skips loans with no fine"),
            self.finding(LOANS, 1, "loans.py", "Use isinstance instead of an exact type check"),
        ]
        (root / "findings.json").write_text(json.dumps({"findings": findings}))
        result = review_bench.score(root)
        self.assertEqual(result["plants"], dict.fromkeys(LOANS.plants, True))
        self.assertEqual((result["true_positives"], result["decoy_hits"]), (5, [5]))
        self.assertIn("| exception-type | 1/1 |", review_bench.report([root]))
        invoice = review_bench.prepare("plain", self.base / "invoice", "test-model")
        review_bench.score(invoice)
        with self.assertRaises(ValueError):
            review_bench.report([root, invoice])


if __name__ == "__main__":
    unittest.main()
