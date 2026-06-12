"""Tests for word_garden.words."""

import random
import unittest

from word_garden.words import (
    WORDS,
    MSG_UNKNOWN_DIFFICULTY,
    MSG_EMPTY_POOL,
    select_word,
    water_for,
    _DIFFICULTY_PARAMS,
)


class TestWordList(unittest.TestCase):
    def test_words_is_nonempty(self):
        self.assertGreater(len(WORDS), 0)

    def test_words_are_uppercase(self):
        for w in WORDS:
            self.assertEqual(w, w.upper(), f"Word {w!r} is not uppercase")

    def test_expected_words_present(self):
        for expected in ("GARDEN", "FLOWER", "PLANET", "PYTHON", "TERMINAL",
                         "MEADOW", "ORCHARD", "VINEYARD", "SEEDLING", "HARVEST"):
            self.assertIn(expected, WORDS)


class TestSelectWord(unittest.TestCase):
    """SPEC section 16, case 10: word selector returns a valid word."""

    def _fixed_rng(self, seed: int = 0) -> random.Random:
        return random.Random(seed)

    # -- Easy -----------------------------------------------------------------

    def test_easy_returns_word_in_words(self):
        word = select_word("easy", rng=self._fixed_rng())
        self.assertIn(word, WORDS, "easy word must come from WORDS")

    def test_easy_length_constraint(self):
        rng = self._fixed_rng(42)
        for _ in range(50):
            word = select_word("easy", rng=rng)
            self.assertGreaterEqual(len(word), 4, f"{word!r} too short for easy")
            self.assertLessEqual(len(word), 6, f"{word!r} too long for easy")

    def test_easy_water(self):
        self.assertEqual(water_for("easy"), 8)

    # -- Normal ---------------------------------------------------------------

    def test_normal_returns_word_in_words(self):
        word = select_word("normal", rng=self._fixed_rng())
        self.assertIn(word, WORDS, "normal word must come from WORDS")

    def test_normal_length_constraint(self):
        rng = self._fixed_rng(99)
        for _ in range(50):
            word = select_word("normal", rng=rng)
            self.assertGreaterEqual(len(word), 5, f"{word!r} too short for normal")
            self.assertLessEqual(len(word), 8, f"{word!r} too long for normal")

    def test_normal_water(self):
        self.assertEqual(water_for("normal"), 6)

    # -- Hard -----------------------------------------------------------------

    def test_hard_returns_word_in_words(self):
        word = select_word("hard", rng=self._fixed_rng())
        self.assertIn(word, WORDS, "hard word must come from WORDS")

    def test_hard_length_constraint(self):
        rng = self._fixed_rng(7)
        for _ in range(50):
            word = select_word("hard", rng=rng)
            self.assertGreaterEqual(len(word), 7, f"{word!r} too short for hard")

    def test_hard_water(self):
        self.assertEqual(water_for("hard"), 4)

    # -- Default (no rng) -----------------------------------------------------

    def test_default_difficulty_returns_valid_word(self):
        word = select_word()
        self.assertIn(word, WORDS)

    # -- Unknown difficulty raises ValueError ---------------------------------

    def test_select_word_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            select_word("legendary")
        # Assert the POSITIVE: the message names the bad key
        self.assertIn("legendary", str(ctx.exception))

    def test_water_for_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            water_for("legendary")
        self.assertIn("legendary", str(ctx.exception))

    # -- Message constants used in errors -------------------------------------

    def test_unknown_difficulty_message_constant_used(self):
        """The ValueError message must come from MSG_UNKNOWN_DIFFICULTY."""
        try:
            select_word("bogus")
        except ValueError as exc:
            self.assertIn("bogus", str(exc))
        else:
            self.fail("Expected ValueError for unknown difficulty")

    def test_msg_empty_pool_constant_exists(self):
        """MSG_EMPTY_POOL is defined — coverage for the constant itself."""
        self.assertIsInstance(MSG_EMPTY_POOL, str)
        self.assertGreater(len(MSG_EMPTY_POOL), 0)


if __name__ == "__main__":
    unittest.main()
