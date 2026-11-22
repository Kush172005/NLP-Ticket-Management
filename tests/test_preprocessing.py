import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data_loader
from preprocessing import clean_text, mask_text, duplicate_groups


class CleaningTests(unittest.TestCase):
    def test_negation_survives_contractions_and_curly_apostrophes(self):
        self.assertEqual(clean_text("I can’t pay. It isn't working!"), "i cannot pay it is not working")
        self.assertEqual(clean_text("I won't transfer it"), "i will not transfer it")

    def test_sensitive_patterns_do_not_survive_export(self):
        text = "Email person@example.com, card 4111 1111 1111 1111, phone +91 98765 43210, visit https://example.com. Amount 42.50"
        result = mask_text(text)
        for value in ("person@example.com", "4111", "98765", "https://example.com", "42.50"):
            self.assertNotIn(value, result)
        for token in ("<email>", "<card>", "<phone>", "<url>", "<number>"):
            self.assertIn(token, result)

    def test_stopwords_and_short_intent_words_remain(self):
        self.assertEqual(clean_text("My PIN is not working."), "my pin is not working")

    def test_empty_and_whitespace(self):
        self.assertEqual(clean_text("  !!!  "), "")
        self.assertEqual(clean_text("  My\n card\tfailed  "), "my card failed")

    def test_cleaning_is_idempotent(self):
        for text in ("My card isn't working!", "Mail a@b.com", "Paid 123.50 yesterday"):
            self.assertEqual(clean_text(clean_text(text)), clean_text(text))


class DuplicateTests(unittest.TestCase):
    def test_exact_short_queries_group_but_distinct_queries_do_not(self):
        groups, _ = duplicate_groups(["card failed", "card failed", "card arrived"])
        self.assertEqual(groups[0], groups[1])
        self.assertNotEqual(groups[0], groups[2])

    def test_near_duplicate_keeps_exact_copies_connected(self):
        base = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
        groups, pairs = duplicate_groups([base, base + " please", base + " please", "unrelated query"])
        self.assertEqual(len(set(groups[:3])), 1)
        self.assertNotEqual(groups[0], groups[3])
        self.assertTrue(any(kind == "near" for _, _, _, kind in pairs))

    def test_grouping_is_reproducible(self):
        texts = ["one two three four five", "one two three four five", "my pin failed"]
        self.assertEqual(duplicate_groups(texts), duplicate_groups(texts))


class SourceTests(unittest.TestCase):
    def test_changed_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            (raw / "banking77_train.csv").write_text("text,category\nmade up,card_arrival\n")
            with patch.object(data_loader, "RAW", raw):
                with self.assertRaisesRegex(ValueError, "Source verification failed"):
                    data_loader.load_raw()

    def test_missing_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(data_loader, "RAW", Path(directory)):
                with self.assertRaises(FileNotFoundError):
                    data_loader.load_raw()


if __name__ == "__main__":
    unittest.main()
