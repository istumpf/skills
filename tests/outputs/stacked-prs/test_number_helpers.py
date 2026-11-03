"""Tests for integer helpers."""

import unittest

from number_helpers import predecessor, successor


class SuccessorTests(unittest.TestCase):
    def test_negative_one_reaches_zero(self):
        self.assertEqual(successor(-1), 0)

    def test_adjacent_integers(self):
        for value, expected in [(-8, -7), (0, 1), (12, 13)]:
            with self.subTest(value=value):
                self.assertEqual(successor(value), expected)

    def test_arbitrary_precision_integers(self):
        self.assertEqual(successor(10**100), 10**100 + 1)
        self.assertEqual(successor(-(10**100)), -(10**100) + 1)


class PredecessorTests(unittest.TestCase):
    def test_zero_reaches_negative_one(self):
        self.assertEqual(predecessor(0), -1)

    def test_adjacent_integers(self):
        for value, expected in [(-8, -9), (1, 0), (12, 11)]:
            with self.subTest(value=value):
                self.assertEqual(predecessor(value), expected)

    def test_arbitrary_precision_integers(self):
        self.assertEqual(predecessor(10**100), 10**100 - 1)
        self.assertEqual(predecessor(-(10**100)), -(10**100) - 1)


if __name__ == "__main__":
    unittest.main()
