import unittest

from tags import existing_marker, normalize_tags, unique_tags


class NormalizeTagsTests(unittest.TestCase):
    def test_preserves_existing_marker(self):
        self.assertEqual(existing_marker(), "keep-me")

    def test_normalizes_in_order_retaining_duplicates_without_mutating_input(self):
        tags = [" B ", "", "A", "b", " A ", " \t\n"]
        original = tags.copy()

        result = normalize_tags(tags)

        self.assertEqual(result, ["b", "a", "b", "a"])
        self.assertEqual(tags, original)
        self.assertIsNot(result, tags)

    def test_empty_input_returns_an_empty_list(self):
        self.assertEqual(normalize_tags([]), [])

    def test_discards_all_whitespace_tags(self):
        self.assertEqual(normalize_tags(["", " ", "\t\r\n", "\u2003"]), [])

    def test_uses_python_unicode_lowercase_semantics(self):
        self.assertEqual(normalize_tags([" STRAẞE ", " İ ", "É"]),
                         ["straße", "i\u0307", "é"])

    def test_preserves_internal_whitespace(self):
        self.assertEqual(normalize_tags(("  Hello World  ", "A\tB")),
                         ["hello world", "a\tb"])


class UniqueTagsTests(unittest.TestCase):
    def test_deduplicates_normalized_tags_in_first_occurrence_order(self):
        tags = [" B ", "a", "b", " A ", " "]
        original = tags.copy()

        result = unique_tags(tags)

        self.assertEqual(result, ["b", "a"])
        self.assertIsInstance(result, list)
        self.assertEqual(tags, original)
        self.assertIsNot(result, tags)

    def test_empty_and_whitespace_only_inputs_return_empty_lists(self):
        for tags in ([], ["", " ", "\t\r\n", "\u2003"]):
            with self.subTest(tags=tags):
                self.assertEqual(unique_tags(tags), [])

    def test_deduplicates_using_python_lowercase_semantics(self):
        self.assertEqual(
            unique_tags((" STRAẞE ", "straße", "İ", "i\u0307", "SS", "ß")),
            ["straße", "i\u0307", "ss", "ß"],
        )

    def test_preserves_distinct_internal_whitespace(self):
        self.assertEqual(
            unique_tags([" A B ", "a\tb", "a b", "a  b", "A\tB"]),
            ["a b", "a\tb", "a  b"],
        )


if __name__ == "__main__":
    unittest.main()
