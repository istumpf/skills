import unittest

import invoice


class ParseAmount(unittest.TestCase):
    def test_valid(self):
        for text, cents in ((" 12.5 ", 1250), ("7", 700), ("0.05", 5), ("19.99", 1999)):
            self.assertEqual(invoice.parse_amount(text), cents)

    def test_invalid(self):
        for text in ("", "-1", "abc", "1.234", "1e3", "+5", "NaN"):
            with self.assertRaises(ValueError, msg=text):
                invoice.parse_amount(text)


class ExistingApi(unittest.TestCase):
    def test_format(self):
        self.assertEqual(invoice.format_cents(123450), "$1,234.50")


class LineTotal(unittest.TestCase):
    def test_discounted(self):
        self.assertEqual(invoice.line_total(999, 2, 10), 1798)
        self.assertEqual(invoice.line_total(250, 4), 1000)

    def test_invalid(self):
        for args in ((100, 0), (100, 1, 101), (100, 1, -1)):
            with self.assertRaises(ValueError, msg=args):
                invoice.line_total(*args)


if __name__ == "__main__":
    unittest.main()
