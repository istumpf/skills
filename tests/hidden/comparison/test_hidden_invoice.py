"""Hidden checks for the comparison scenario; each class scores one trap.

Never copy this file into an evaluation repository before the agent finishes.
"""

import copy
import unittest

import invoice


class SpecScenarios(unittest.TestCase):
    """Every scenario written in the spec; a careful agent tests these directly."""

    def test_scenarios(self):
        self.assertEqual([invoice.parse_amount(t) for t in (" 12.5 ", "7", "0.05")], [1250, 700, 5])
        for text in ("", "-1", "abc", "1.234"):
            with self.assertRaises(ValueError):
                invoice.parse_amount(text)
        self.assertEqual(invoice.line_total(999, 2, 10), 1798)
        with self.assertRaises(ValueError):
            invoice.line_total(100, 0)
        self.assertEqual(invoice.coupon_discount(2000, {"type": "percent", "value": 15}), 300)
        self.assertEqual(invoice.coupon_discount(2000, {"type": "fixed", "value": 500}), 500)
        self.assertEqual(invoice.tax_cents(1000, "8.875"), 89)
        self.assertEqual(invoice.build_invoice([{"price": "10.00", "quantity": 2}],
                                               {"type": "fixed", "value": 500}, "10"),
                         {"subtotal": 2000, "coupon_discount": 500, "tax": 150, "total": 1650})
        self.assertEqual(invoice.parse_amount("1,234.50"), 123450)


class ExactParsing(unittest.TestCase):
    """Group 1 prose: exact, no binary floating point (float * 100 truncates)."""

    def test_exact(self):
        for text, cents in (("19.99", 1999), ("0.29", 29), ("1.15", 115), ("4.35", 435), ("0.07", 7)):
            self.assertEqual(invoice.parse_amount(text), cents, text)
            self.assertIs(type(invoice.parse_amount(text)), int)


class StrictParsing(unittest.TestCase):
    """Group 1 prose: signed, exponent, and non-numeric forms that float/Decimal accept."""

    def test_rejects(self):
        for text in ("1e3", "+5", "NaN", "inf", " ", "1.2.3", "1_000"):
            with self.assertRaises(ValueError, msg=text):
                invoice.parse_amount(text)


class LineHalfUp(unittest.TestCase):
    """Group 2 prose: half-up rounding; round() and Decimal default are half-even."""

    def test_half_up_and_validation(self):
        self.assertEqual(invoice.line_total(5, 1, 50), 3)
        self.assertEqual(invoice.line_total(1, 1, 50), 1)
        self.assertEqual(invoice.line_total(7, 3, 0), 21)
        self.assertEqual(invoice.line_total(250, 4, 100), 0)
        for args in ((100, 1, 101), (100, 1, -1), (100, -2, 0)):
            with self.assertRaises(ValueError, msg=args):
                invoice.line_total(*args)


class CouponRules(unittest.TestCase):
    """Group 3 prose: cap at subtotal, half-up percent, unknown type rejected."""

    def test_rules(self):
        self.assertEqual(invoice.coupon_discount(1500, {"type": "fixed", "value": 2000}), 1500)
        self.assertEqual(invoice.coupon_discount(5, {"type": "percent", "value": 50}), 3)
        with self.assertRaises(ValueError):
            invoice.coupon_discount(1000, {"type": "bogo", "value": 1})


class TaxExactHalfUp(unittest.TestCase):
    """Group 4 prose: exact rate and half-up (float gives 11 for 1000 at 1.15%)."""

    def test_tax(self):
        self.assertEqual(invoice.tax_cents(120, "8.75"), 11)
        self.assertEqual(invoice.tax_cents(10, "5"), 1)
        self.assertEqual(invoice.tax_cents(1000, "1.15"), 12)
        self.assertEqual(invoice.tax_cents(0, "8.875"), 0)


class PerLineRounding(unittest.TestCase):
    """Design decision: subtotal sums separately rounded line totals."""

    def test_subtotal(self):
        line = {"price": "0.05", "quantity": 1, "discount_percent": 50}
        self.assertEqual(invoice.build_invoice([line, dict(line)])["subtotal"], 6)


class CouponAfterLineDiscounts(unittest.TestCase):
    """Cross-group: a percent coupon applies to the line-discounted subtotal, then tax."""

    def test_order(self):
        result = invoice.build_invoice([{"price": "40.00", "quantity": 1, "discount_percent": 10}],
                                       {"type": "percent", "value": 25}, "8.875")
        self.assertEqual(result, {"subtotal": 3600, "coupon_discount": 900, "tax": 240, "total": 2940})


class GroupedParsingRegression(unittest.TestCase):
    """Group 5 extends group 1: separators must not loosen earlier validation."""

    def test_grouping(self):
        self.assertEqual(invoice.parse_amount("1,234,567"), 123456700)
        self.assertEqual(invoice.parse_amount(" 12,345.6 "), 1234560)
        for text in ("1,23", "12,34.5", ",123", "1234,567", "1,234.567", "1,,234", "-1,234", "1e3", "1,2345"):
            with self.assertRaises(ValueError, msg=text):
                invoice.parse_amount(text)
        self.assertEqual(invoice.build_invoice([{"price": "1,000", "quantity": 1}])["total"], 100000)


class NoMutation(unittest.TestCase):
    """Invoice prose: arguments are left unchanged."""

    def test_inputs_unchanged(self):
        lines = [{"price": "3.00", "quantity": 2}, {"price": "1,000.00", "quantity": 1, "discount_percent": 5}]
        coupon = {"type": "fixed", "value": 100}
        before = copy.deepcopy((lines, coupon))
        invoice.build_invoice(lines, coupon, "7")
        self.assertEqual((lines, coupon), before)


class ExistingApi(unittest.TestCase):
    """Proposal: pre-existing API stays intact."""

    def test_existing(self):
        self.assertEqual(invoice.CURRENCY, "USD")
        self.assertEqual(invoice.format_cents(123450), "$1,234.50")
        self.assertEqual(invoice.format_cents(-5), "-$0.05")


TRAPS = [SpecScenarios, ExactParsing, StrictParsing, LineHalfUp, CouponRules, TaxExactHalfUp,
         PerLineRounding, CouponAfterLineDiscounts, GroupedParsingRegression, NoMutation, ExistingApi]
