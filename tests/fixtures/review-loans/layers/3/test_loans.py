from datetime import date, datetime
import unittest

import loans


class DueDate(unittest.TestCase):
    def test_periods(self):
        self.assertEqual(loans.due_date(date(2026, 11, 2), "book"), date(2026, 11, 23))
        self.assertEqual(loans.due_date(date(2026, 11, 1), "dvd"), date(2026, 11, 9))

    def test_closed_days_in_a_row(self):
        self.assertEqual(loans.due_date(date(2026, 12, 18), "dvd"), date(2026, 12, 28))

    def test_rejects(self):
        with self.assertRaises(TypeError):
            loans.due_date(datetime(2026, 11, 2, 9), "book")
        with self.assertRaises(ValueError):
            loans.due_date(date(2026, 11, 2), "magazine")

    def test_existing_api(self):
        self.assertFalse(loans.is_open(date(2026, 11, 29)))
        self.assertFalse(loans.is_open(date(2026, 12, 25)))


class DaysOverdue(unittest.TestCase):
    def test_open_days(self):
        self.assertEqual(loans.days_overdue(date(2026, 11, 23), date(2026, 11, 25)), 2)
        self.assertEqual(loans.days_overdue(date(2026, 11, 28), date(2026, 11, 30)), 1)
        self.assertEqual(loans.days_overdue(date(2026, 11, 23), date(2026, 11, 20)), 0)


class FineCents(unittest.TestCase):
    def test_fines(self):
        self.assertEqual(loans.fine_cents("dvd", 3), 300)
        self.assertEqual([loans.fine_cents("book", d) for d in (0, 1, 2)], [0, 0, 25])

    def test_caps(self):
        self.assertEqual(loans.fine_cents("book", 60), 500)
        self.assertEqual(loans.fine_cents("dvd", 45), 2000)

    def test_invalid(self):
        for days in (-1, 1.5):
            with self.assertRaises(ValueError):
                loans.fine_cents("book", days)


if __name__ == "__main__":
    unittest.main()
