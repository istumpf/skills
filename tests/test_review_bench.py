"""Check that the review benchmark plants what it claims and scores findings."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

import compare
import review_bench

SKILL = compare.HERE.parent / "skills/stacked-pr-feedback/SKILL.md"


class ReviewBenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="review-bench-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def finding(self, layer, path, body):
        return {"branch": review_bench.BRANCHES[layer - 1], "path": path, "line": 1, "body": body}

    def test_layers_pass_their_tests_and_fail_only_planted_traps(self):
        root = review_bench.prepare("plain", self.base / "run", "test-model")
        repo = root / "repo"
        expected = {1: [], 2: ["LineHalfUp"], 3: ["LineHalfUp", "CouponRules"],
                    4: ["LineHalfUp", "CouponRules"],
                    # Layer 2's half-even rounding also breaks per-line rounding.
                    5: ["LineHalfUp", "PerLineRounding", "GroupedParsingRegression"]}
        self.assertEqual({int(b.split("/")[1][0]): failed for b, failed in
                          compare.layer_failures(repo).items()}, expected)
        for branch in review_bench.BRANCHES:
            with tempfile.TemporaryDirectory() as temp:
                for name in ("invoice.py", "test_invoice.py"):
                    Path(temp, name).write_text(compare.committed_source(repo, branch, name))
                self.assertTrue(compare.run_tests(temp, "discover"), branch)
        self.assertIn("notes.txt", compare.git(repo, "diff", "--name-only",
                                               "main", review_bench.BRANCHES[0]))
        self.assertEqual(compare.git(repo, "branch", "--show-current"), review_bench.BRANCHES[-1])
        tasks = compare.markers_by_id((repo / compare.TASKS).read_text())
        self.assertTrue(all(mark == "x" for mark in tasks.values()))

    def test_decoys_are_correct(self):
        repo = review_bench.prepare("plain", self.base / "run", "test-model") / "repo"
        coupons = compare.committed_source(repo, review_bench.BRANCHES[2])
        tax = compare.committed_source(repo, review_bench.BRANCHES[3])
        self.assertTrue(compare.hidden_traps(tax, ["TaxExactHalfUp"])["TaxExactHalfUp"])
        namespace = {}
        exec(coupons, namespace)
        for subtotal, value, expected in ((5, 50, 3), (2000, 15, 300), (1, 50, 1), (3, 50, 2)):
            self.assertEqual(namespace["coupon_discount"](subtotal, {"type": "percent", "value": value}),
                             expected)

    def test_requests_name_the_skill_only_for_the_skill_arm(self):
        plain = review_bench.prepare("plain", self.base / "p", "test-model")
        skilled = review_bench.prepare("skill", self.base / "k", "test-model", SKILL)
        self.assertIn("Do not spawn subagents", (plain / "REQUEST.txt").read_text())
        self.assertIn(str(SKILL), (skilled / "REQUEST.txt").read_text())
        for root in (plain, skilled):
            request = (root / "REQUEST.txt").read_text().lower()
            for word in ("plant", "decoy", "half-even", "notes.txt"):
                self.assertNotIn(word, request)
        with self.assertRaises(ValueError):
            review_bench.prepare("skill", self.base / "missing", "test-model")

    def test_scores_plants_decoys_and_labels(self):
        root = review_bench.prepare("skill", self.base / "run", "test-model", SKILL)
        findings = [
            self.finding(2, "invoice.py", "round() on a Decimal is half-even, not half up"),
            self.finding(5, "invoice.py", "Coupon cap belongs to layer 3; min() was added here"),
            self.finding(1, "notes.txt", "Unrelated edit"),
            self.finding(5, "invoice.py", "Stripping every comma accepts 1,23"),
            self.finding(4, "invoice.py", "The +50 // 100 trick may not round half up"),
            self.finding(3, "test_invoice.py", "Missing a test for zero subtotal"),
            self.finding(5, "invoice.py", "Unknown coupon type message could be clearer"),
            # Right defect, wrong layer: not credited.
            self.finding(4, "invoice.py", "Separators accepted loosely"),
        ]
        (root / "findings.json").write_text(json.dumps({"findings": findings}))
        (root / "labels.json").write_text('{"5": true}')
        result = review_bench.score(root, cost=0.3, minutes=2)
        self.assertEqual(result["plants"], dict.fromkeys(review_bench.PLANTS, True))
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual((result["true_positives"], result["false_positives"]), (5, 3))
        self.assertEqual(result["precision"], 0.62)
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
        self.assertIn("| Mean precision | – | 0.62 |", table)
        self.assertIn("| Runs leaving the repo unchanged | 0/1 | 1/1 |", table)


if __name__ == "__main__":
    unittest.main()
