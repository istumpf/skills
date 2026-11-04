"""Hidden checks for the loans scenario; each class scores one trap.

Never copy this file into an evaluation repository before the agent finishes.
"""

import copy
from datetime import date, datetime
import unittest

import loans


def loan(due, kind="book", renewals=0, patron="ana"):
    return {"kind": kind, "due": due, "renewals": renewals, "patron": patron}


class SpecScenarios(unittest.TestCase):
    """Every scenario written in the spec; a careful agent tests these directly."""

    def test_scenarios(self):
        self.assertEqual(loans.due_date(date(2026, 11, 2), "book"), date(2026, 11, 23))
        self.assertEqual(loans.due_date(date(2026, 11, 1), "dvd"), date(2026, 11, 9))
        self.assertEqual(loans.days_overdue(date(2026, 11, 23), date(2026, 11, 25)), 2)
        self.assertEqual(loans.days_overdue(date(2026, 11, 23), date(2026, 11, 20)), 0)
        self.assertEqual(loans.fine_cents("dvd", 3), 300)
        self.assertEqual(loans.fine_cents("book", 0), 0)
        renewed = loans.renew(loan(date(2026, 11, 23)), date(2026, 11, 23))
        self.assertEqual((renewed["due"], renewed["renewals"]), (date(2026, 12, 14), 1))
        with self.assertRaises(ValueError):
            loans.renew(loan(date(2026, 11, 23)), date(2026, 11, 24))
        self.assertEqual(loans.place_hold(("ana",), "bo"), ("ana", "bo"))
        with self.assertRaises(ValueError):
            loans.renew(loan(date(2026, 11, 23)), date(2026, 11, 23), holds=("bo",))
        self.assertEqual(loans.receipt([loan(date(2026, 11, 23), "dvd")], date(2026, 11, 25)),
                         {"overdue_items": 1, "total_cents": 200})
        self.assertEqual(loans.receipt([], date(2026, 11, 25)), {"overdue_items": 0, "total_cents": 0})


class RejectsDatetime(unittest.TestCase):
    """Group 1 prose: datetime is a date subclass, so isinstance lets it through."""

    def test_types(self):
        for value in (datetime(2026, 11, 2, 9, 30), "2026-11-02", None):
            with self.assertRaises(TypeError, msg=value):
                loans.due_date(value, "book")
        with self.assertRaises(ValueError):
            loans.due_date(date(2026, 11, 2), "magazine")


class ChainedClosures(unittest.TestCase):
    """Group 1 prose: "the next day it is open" may be several closed days away."""

    def test_next_open_day(self):
        # 25 Dec (holiday), 26 Dec (holiday), 27 Dec (Sunday).
        self.assertEqual(loans.due_date(date(2026, 12, 18), "dvd"), date(2026, 12, 28))
        self.assertEqual(loans.due_date(date(2026, 12, 11), "book"), date(2027, 1, 2))


class OpenDaysOnly(unittest.TestCase):
    """Design decision: closed days are never counted as overdue."""

    def test_open_days(self):
        self.assertEqual(loans.days_overdue(date(2026, 11, 28), date(2026, 11, 30)), 1)
        self.assertEqual(loans.days_overdue(date(2026, 12, 24), date(2026, 12, 29)), 2)
        self.assertEqual(loans.days_overdue(date(2026, 11, 23), date(2026, 11, 23)), 0)


class BookGraceDay(unittest.TestCase):
    """Group 3 prose: a book's first overdue day is free; a DVD's is not."""

    def test_grace(self):
        self.assertEqual([loans.fine_cents("book", d) for d in (1, 2, 5)], [0, 25, 100])
        self.assertEqual(loans.fine_cents("dvd", 1), 100)
        for days in (-1, 1.5, "2"):
            with self.assertRaises(ValueError, msg=days):
                loans.fine_cents("book", days)


class FineCap(unittest.TestCase):
    """Design decision only: fines are capped at the replacement fee."""

    def test_caps(self):
        self.assertEqual(loans.fine_cents("book", 21), 500)
        self.assertEqual(loans.fine_cents("book", 60), 500)
        self.assertEqual(loans.fine_cents("dvd", 20), 2000)
        self.assertEqual(loans.fine_cents("dvd", 45), 2000)


class RenewFromDue(unittest.TestCase):
    """Group 4 prose: the period counts from the current due date, not from today."""

    def test_from_due(self):
        self.assertEqual(loans.renew(loan(date(2026, 11, 23)), date(2026, 11, 20))["due"],
                         date(2026, 12, 14))
        self.assertEqual(loans.renew(loan(date(2026, 11, 16), "dvd"), date(2026, 11, 10))["due"],
                         date(2026, 11, 23))
        self.assertEqual(loans.renew(loan(date(2026, 12, 4)), date(2026, 12, 1))["due"],
                         date(2026, 12, 28))


class RenewalLimit(unittest.TestCase):
    """Group 4 prose: at most two renewals."""

    def test_limit(self):
        self.assertEqual(loans.renew(loan(date(2026, 11, 23), renewals=1), date(2026, 11, 23))["renewals"], 2)
        with self.assertRaises(ValueError):
            loans.renew(loan(date(2026, 11, 23), renewals=2), date(2026, 11, 23))


class NoMutation(unittest.TestCase):
    """Design decision: arguments are left unchanged."""

    def test_inputs_unchanged(self):
        original = loan(date(2026, 11, 23))
        before = copy.deepcopy(original)
        renewed = loans.renew(original, date(2026, 11, 20))
        self.assertEqual(original, before)
        self.assertIsNot(renewed, original)


class HoldRules(unittest.TestCase):
    """Group 5 extends group 4: only other patrons' holds block a renewal."""

    def test_holds(self):
        mine = loan(date(2026, 11, 23), patron="ana")
        self.assertEqual(loans.renew(mine, date(2026, 11, 23), holds=("ana",))["renewals"], 1)
        with self.assertRaises(ValueError):
            loans.renew(mine, date(2026, 11, 23), holds=("ana", "bo"))
        with self.assertRaises(ValueError):
            loans.renew(loan(date(2026, 11, 23), renewals=2), date(2026, 11, 23), holds=("ana",))
        with self.assertRaises(ValueError):
            loans.place_hold(("ana", "bo"), "bo")
        self.assertEqual(loans.place_hold((), "ana"), ("ana",))


class ReceiptCrossGroup(unittest.TestCase):
    """Group 6 combines groups 2 and 3: open days, grace day, and per-item caps."""

    def test_receipt(self):
        items = [loan(date(2026, 11, 28)), loan(date(2026, 11, 2), "dvd"), loan(date(2026, 12, 1), "dvd")]
        before = copy.deepcopy(items)
        # Book: one open day (Sunday skipped), free. DVD: capped. Last: not yet due.
        self.assertEqual(loans.receipt(items, date(2026, 11, 30)),
                         {"overdue_items": 2, "total_cents": 2000})
        self.assertEqual(items, before)


class ExistingApi(unittest.TestCase):
    """Proposal: HOLIDAYS and is_open stay as they are."""

    def test_existing(self):
        self.assertEqual(loans.HOLIDAYS, frozenset({date(2026, 12, 25), date(2026, 12, 26), date(2027, 1, 1)}))
        self.assertFalse(loans.is_open(date(2026, 11, 29)))
        self.assertTrue(loans.is_open(date(2026, 11, 28)))
        self.assertFalse(loans.is_open(date(2026, 12, 25)))
