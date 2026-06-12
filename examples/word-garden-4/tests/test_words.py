import random
import unittest

from word_garden.words import WORDS, select_word, water_for


class TestWordList(unittest.TestCase):
    def test_words_are_uppercase_strings(self):
        for word in WORDS:
            self.assertIsInstance(word, str)
            self.assertEqual(word, word.upper(), f"{word!r} is not uppercase")

    def test_word_list_has_ten_entries(self):
        self.assertEqual(len(WORDS), 10)


class TestWaterFor(unittest.TestCase):
    def test_easy_water(self):
        self.assertEqual(water_for("easy"), 8)

    def test_normal_water(self):
        self.assertEqual(water_for("normal"), 6)

    def test_hard_water(self):
        self.assertEqual(water_for("hard"), 4)

    def test_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError):
            water_for("extreme")


class TestSelectWord(unittest.TestCase):
    # Test 10: The word selector returns a valid word for every difficulty.

    def test_easy_returns_word_from_list_with_correct_length(self):
        rng = random.Random(42)
        word = select_word("easy", rng=rng)
        self.assertIn(word, WORDS)
        self.assertGreaterEqual(len(word), 4)
        self.assertLessEqual(len(word), 6)

    def test_normal_returns_word_from_list_with_correct_length(self):
        rng = random.Random(42)
        word = select_word("normal", rng=rng)
        self.assertIn(word, WORDS)
        self.assertGreaterEqual(len(word), 5)
        self.assertLessEqual(len(word), 8)

    def test_hard_returns_word_from_list_with_correct_length(self):
        rng = random.Random(42)
        word = select_word("hard", rng=rng)
        self.assertIn(word, WORDS)
        self.assertGreaterEqual(len(word), 7)

    def test_all_difficulties_return_valid_word(self):
        rng = random.Random(7)
        for difficulty in ("easy", "normal", "hard"):
            with self.subTest(difficulty=difficulty):
                word = select_word(difficulty, rng=rng)
                self.assertIn(word, WORDS)

    def test_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError):
            select_word("extreme")

    def test_injected_rng_is_deterministic(self):
        rng_a = random.Random(99)
        rng_b = random.Random(99)
        self.assertEqual(
            select_word("normal", rng=rng_a),
            select_word("normal", rng=rng_b),
        )

    def test_multiple_calls_with_same_seed_agree(self):
        rng = random.Random(0)
        first = select_word("hard", rng=rng)
        rng2 = random.Random(0)
        second = select_word("hard", rng=rng2)
        self.assertEqual(first, second)
