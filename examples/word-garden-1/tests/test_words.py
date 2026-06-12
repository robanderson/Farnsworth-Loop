"""Tests for word_garden.words (SPEC.md sections 7, 8, 16 case 10)."""

import random
import unittest

from word_garden import words


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


class SelectWordTests(unittest.TestCase):
    # SPEC.md section 16, case 10: the word selector returns a valid word.

    def test_returns_valid_word_for_every_difficulty(self):
        bounds = {
            "easy": (4, 6),
            "normal": (5, 8),
            "hard": (7, None),
        }
        for difficulty, (lo, hi) in bounds.items():
            with self.subTest(difficulty=difficulty):
                word = words.select_word(difficulty, rng=random.Random(0))
                self.assertIn(word, words.WORDS)
                self.assertEqual(word, word.upper())
                self.assertGreaterEqual(len(word), lo)
                if hi is not None:
                    self.assertLessEqual(len(word), hi)

    def test_respects_length_filter_across_many_draws(self):
        bounds = {
            "easy": (4, 6),
            "normal": (5, 8),
            "hard": (7, None),
        }
        rng = random.Random(12345)
        for difficulty, (lo, hi) in bounds.items():
            for _ in range(200):
                word = words.select_word(difficulty, rng=rng)
                self.assertGreaterEqual(len(word), lo, msg=f"{word} too short")
                if hi is not None:
                    self.assertLessEqual(len(word), hi, msg=f"{word} too long")

    def test_default_difficulty_is_normal(self):
        word = words.select_word(rng=random.Random(1))
        self.assertGreaterEqual(len(word), 5)
        self.assertLessEqual(len(word), 8)

    def test_injected_rng_is_deterministic(self):
        a = words.select_word("normal", rng=random.Random(42))
        b = words.select_word("normal", rng=random.Random(42))
        self.assertEqual(a, b)

    def test_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError):
            words.select_word("nightmare")

    def test_works_without_injected_rng(self):
        word = words.select_word("easy")
        self.assertIn(word, words.WORDS)
        self.assertLessEqual(len(word), 6)


if __name__ == "__main__":
    unittest.main()
