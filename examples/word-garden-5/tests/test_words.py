"""Tests for word_garden/words.py — word list and difficulty selection."""

import random
import unittest

from word_garden.words import WORDS, select_word, water_for


class TestSelectWord(unittest.TestCase):
    """10. The word selector returns a valid word (SPEC section 16)."""

    def test_returns_uppercase_string(self):
        rng = random.Random(0)
        word = select_word(rng=rng)
        self.assertIsInstance(word, str)
        self.assertTrue(word.isupper())

    def test_word_is_in_word_list(self):
        rng = random.Random(0)
        word = select_word(rng=rng)
        self.assertIn(word, WORDS)

    def test_easy_word_length_4_to_6(self):
        seen = set()
        for seed in range(100):
            w = select_word(difficulty="easy", rng=random.Random(seed))
            seen.add(w)
        for w in seen:
            self.assertGreaterEqual(len(w), 4)
            self.assertLessEqual(len(w), 6)

    def test_normal_word_length_5_to_8(self):
        seen = set()
        for seed in range(100):
            w = select_word(difficulty="normal", rng=random.Random(seed))
            seen.add(w)
        for w in seen:
            self.assertGreaterEqual(len(w), 5)
            self.assertLessEqual(len(w), 8)

    def test_hard_word_length_7_plus(self):
        seen = set()
        for seed in range(100):
            w = select_word(difficulty="hard", rng=random.Random(seed))
            seen.add(w)
        for w in seen:
            self.assertGreaterEqual(len(w), 7)

    def test_unknown_difficulty_raises(self):
        """Empty/unknown pool must raise ValueError (Code Tips #5)."""
        with self.assertRaises(ValueError):
            select_word(difficulty="legendary")

    def test_empty_pool_raises_value_error(self):
        """Force an empty pool and confirm ValueError is raised (Code Tips #5)."""
        import word_garden.words as words_module
        original = words_module.WORDS[:]
        try:
            words_module.WORDS.clear()
            with self.assertRaises(ValueError):
                select_word(difficulty="normal")
        finally:
            words_module.WORDS.extend(original)


class TestWaterFor(unittest.TestCase):
    def test_easy_water(self):
        self.assertEqual(water_for("easy"), 8)

    def test_normal_water(self):
        self.assertEqual(water_for("normal"), 6)

    def test_hard_water(self):
        self.assertEqual(water_for("hard"), 4)

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            water_for("legendary")
