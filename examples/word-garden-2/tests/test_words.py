"""Tests for word_garden.words (word list and selection)."""

import random
import unittest

from word_garden import words


class WaterForTests(unittest.TestCase):
    def test_water_per_difficulty(self):
        self.assertEqual(words.water_for("easy"), 8)
        self.assertEqual(words.water_for("normal"), 6)
        self.assertEqual(words.water_for("hard"), 4)

    def test_default_is_normal(self):
        self.assertEqual(words.water_for(), 6)

    def test_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError):
            words.water_for("impossible")


class WordListTests(unittest.TestCase):
    def test_word_list_matches_spec(self):
        expected = [
            "GARDEN",
            "FLOWER",
            "PLANET",
            "PYTHON",
            "TERMINAL",
            "MEADOW",
            "ORCHARD",
            "VINEYARD",
            "SEEDLING",
            "HARVEST",
        ]
        self.assertEqual(words.WORDS, expected)

    def test_all_words_uppercase(self):
        for word in words.WORDS:
            self.assertEqual(word, word.upper())


class SelectWordTests(unittest.TestCase):
    """SPEC.md section 16, case 10: the selector returns a valid word."""

    def test_select_word_returns_valid_word_each_difficulty(self):
        # Length bounds from SPEC.md section 7.
        bounds = {
            "easy": (4, 6),
            "normal": (5, 8),
            "hard": (7, None),
        }
        for difficulty, (lo, hi) in bounds.items():
            rng = random.Random(1234)
            # Sample many times to exercise the whole candidate pool.
            for _ in range(50):
                word = words.select_word(difficulty, rng=rng)
                self.assertIn(word, words.WORDS)
                self.assertEqual(word, word.upper())
                self.assertGreaterEqual(len(word), lo)
                if hi is not None:
                    self.assertLessEqual(len(word), hi)

    def test_select_word_is_deterministic_with_rng(self):
        a = words.select_word("normal", rng=random.Random(7))
        b = words.select_word("normal", rng=random.Random(7))
        self.assertEqual(a, b)

    def test_select_word_default_difficulty(self):
        word = words.select_word(rng=random.Random(0))
        self.assertIn(word, words.WORDS)
        self.assertGreaterEqual(len(word), 5)
        self.assertLessEqual(len(word), 8)

    def test_select_word_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError):
            words.select_word("nope", rng=random.Random(0))

    def test_select_word_default_rng_path(self):
        # Without an injected rng the module-level random is used.
        word = words.select_word("easy")
        self.assertIn(word, words.WORDS)


if __name__ == "__main__":
    unittest.main()
