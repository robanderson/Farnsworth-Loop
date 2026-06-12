"""Tests for word_garden.game (SPEC.md sections 6, 12, 14, 16).

Covers the UI-free cases in SPEC.md section 16 with positive assertions.
"""

import random
import unittest

from word_garden import game
from word_garden.game import GameState


def make_state(secret="GARDEN", water=6, guessed=None):
    """Helper: a GameState with a known secret word for deterministic tests."""
    return GameState(
        secret_word=secret,
        guessed_letters=set(guessed or set()),
        remaining_water=water,
        weed_count=0,
        max_water=water,
    )


class NewGameTests(unittest.TestCase):
    def test_new_game_initial_state(self):
        state = game.new_game("normal", rng=random.Random(7))
        self.assertEqual(state.secret_word, state.secret_word.upper())
        self.assertGreaterEqual(len(state.secret_word), 5)
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.max_water, 6)
        self.assertEqual(state.weed_count, 0)
        self.assertEqual(state.guessed_letters, set())
        self.assertFalse(state.game_over)
        self.assertFalse(state.won)

    def test_new_game_water_matches_difficulty(self):
        easy = game.new_game("easy", rng=random.Random(1))
        hard = game.new_game("hard", rng=random.Random(1))
        self.assertEqual(easy.remaining_water, 8)
        self.assertEqual(easy.max_water, 8)
        self.assertEqual(hard.remaining_water, 4)
        self.assertEqual(hard.max_water, 4)

    def test_new_game_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError):
            game.new_game("wat")

    def test_default_difficulty_is_normal(self):
        state = game.new_game(rng=random.Random(3))
        self.assertEqual(state.max_water, 6)


class GameStateDefaultsTests(unittest.TestCase):
    def test_field_names_and_defaults(self):
        # SPEC.md section 12 exact field names / defaults.
        state = GameState(secret_word="X")
        self.assertEqual(state.secret_word, "X")
        self.assertEqual(state.guessed_letters, set())
        self.assertEqual(state.remaining_water, 0)
        self.assertEqual(state.weed_count, 0)
        self.assertEqual(state.max_water, 0)
        self.assertEqual(state.status_message, "")
        self.assertFalse(state.game_over)
        self.assertFalse(state.won)


class CorrectGuessTests(unittest.TestCase):
    # SPEC.md section 16, case 1: a correct guess reveals matching letters.

    def test_correct_guess_records_letter_no_penalty(self):
        state = make_state("GARDEN", water=6)
        game.apply_guess(state, "A")
        self.assertIn("A", state.guessed_letters)
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.weed_count, 0)
        self.assertEqual(state.status_message, game.MSG_CORRECT)
        self.assertFalse(state.game_over)

    def test_correct_guess_reveals_all_matching_positions(self):
        state = make_state("BANANA", water=6)
        game.apply_guess(state, "A")
        self.assertEqual(game.display_word(state), "_ A _ A _ A")


class WrongGuessTests(unittest.TestCase):
    # SPEC.md section 16, cases 2 and 3.

    def test_wrong_guess_costs_water_and_adds_weed_and_records(self):
        state = make_state("GARDEN", water=6)
        game.apply_guess(state, "Z")
        self.assertIn("Z", state.guessed_letters)
        self.assertEqual(state.remaining_water, 5)  # -1
        self.assertEqual(state.weed_count, 1)  # +1
        self.assertEqual(state.status_message, game.MSG_WRONG)
        self.assertFalse(state.game_over)


class RepeatGuessTests(unittest.TestCase):
    # SPEC.md section 16, case 4.

    def test_repeat_correct_guess_no_change(self):
        state = make_state("GARDEN", water=6)
        game.apply_guess(state, "A")
        water_before = state.remaining_water
        weeds_before = state.weed_count
        game.apply_guess(state, "A")
        self.assertEqual(state.remaining_water, water_before)
        self.assertEqual(state.weed_count, weeds_before)
        self.assertIn("already guessed A", state.status_message)

    def test_repeat_wrong_guess_no_extra_penalty(self):
        state = make_state("GARDEN", water=6)
        game.apply_guess(state, "Z")
        self.assertEqual(state.remaining_water, 5)
        self.assertEqual(state.weed_count, 1)
        game.apply_guess(state, "Z")
        self.assertEqual(state.remaining_water, 5)  # unchanged
        self.assertEqual(state.weed_count, 1)  # unchanged
        self.assertIn("already guessed Z", state.status_message)


class ValidationTests(unittest.TestCase):
    # SPEC.md section 16, cases 5 and 6.

    def test_valid_letter(self):
        letter, msg = game.validate_guess("a")
        self.assertEqual(letter, "A")
        self.assertEqual(msg, "")

    def test_lowercase_is_normalized(self):
        letter, msg = game.validate_guess("z")
        self.assertEqual(letter, "Z")
        self.assertEqual(msg, "")

    def test_leading_trailing_spaces_trimmed(self):
        letter, msg = game.validate_guess("  b  ")
        self.assertEqual(letter, "B")
        self.assertEqual(msg, "")

    def test_empty_input_rejected(self):
        letter, msg = game.validate_guess("")
        self.assertIsNone(letter)
        self.assertEqual(msg, game.MSG_EMPTY)

    def test_whitespace_only_rejected(self):
        letter, msg = game.validate_guess("   ")
        self.assertIsNone(letter)
        self.assertEqual(msg, game.MSG_EMPTY)

    def test_multiple_characters_rejected(self):
        letter, msg = game.validate_guess("apple")
        self.assertIsNone(letter)
        self.assertEqual(msg, game.MSG_TOO_LONG)

    def test_number_rejected(self):
        letter, msg = game.validate_guess("7")
        self.assertIsNone(letter)
        self.assertEqual(msg, game.MSG_NOT_LETTER)

    def test_symbol_rejected(self):
        letter, msg = game.validate_guess("!")
        self.assertIsNone(letter)
        self.assertEqual(msg, game.MSG_NOT_LETTER)

    def test_invalid_input_does_not_mutate_state(self):
        state = make_state("GARDEN", water=6)
        letter, msg = game.validate_guess("apple")
        # validate_guess never touches state; confirm state untouched.
        self.assertIsNone(letter)
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.weed_count, 0)
        self.assertEqual(state.guessed_letters, set())


class WinTests(unittest.TestCase):
    # SPEC.md section 16, case 7.

    def test_detects_win(self):
        state = make_state("CAT", water=6)
        game.apply_guess(state, "C")
        self.assertFalse(state.game_over)
        game.apply_guess(state, "A")
        self.assertFalse(state.game_over)
        game.apply_guess(state, "T")
        self.assertTrue(game.is_won(state))
        self.assertTrue(state.won)
        self.assertTrue(state.game_over)
        self.assertEqual(state.status_message, game.MSG_WIN)

    def test_is_won_helper(self):
        state = make_state("HI", water=6, guessed={"H", "I"})
        self.assertTrue(game.is_won(state))


class LossTests(unittest.TestCase):
    # SPEC.md section 16, case 8.

    def test_detects_loss(self):
        state = make_state("GARDEN", water=1)
        game.apply_guess(state, "Z")  # wrong -> water hits 0
        self.assertEqual(state.remaining_water, 0)
        self.assertTrue(game.is_lost(state))
        self.assertTrue(state.game_over)
        self.assertFalse(state.won)
        self.assertEqual(state.status_message, game.MSG_LOSS)

    def test_is_lost_false_when_water_remains(self):
        state = make_state("GARDEN", water=3)
        self.assertFalse(game.is_lost(state))

    def test_is_lost_false_when_won_on_final_water(self):
        # Winning even as water reaches a low value is not a loss.
        state = make_state("AB", water=6, guessed={"A", "B"})
        self.assertFalse(game.is_lost(state))


class GameOverNoOpTests(unittest.TestCase):
    def test_guess_after_game_over_is_noop(self):
        state = make_state("GARDEN", water=1)
        game.apply_guess(state, "Z")  # triggers loss
        self.assertTrue(state.game_over)
        water_before = state.remaining_water
        weeds_before = state.weed_count
        guessed_before = set(state.guessed_letters)
        game.apply_guess(state, "A")
        self.assertEqual(state.remaining_water, water_before)
        self.assertEqual(state.weed_count, weeds_before)
        self.assertEqual(state.guessed_letters, guessed_before)
        self.assertEqual(state.status_message, game.MSG_GAME_OVER)


class DisplayWordTests(unittest.TestCase):
    # SPEC.md section 16, case 9.

    def test_masks_unguessed_letters(self):
        state = make_state("GARDEN", water=6, guessed={"G", "R", "E"})
        self.assertEqual(game.display_word(state), "G _ R _ E _")

    def test_all_masked_at_start(self):
        state = make_state("FLOWER", water=6)
        self.assertEqual(game.display_word(state), "_ _ _ _ _ _")

    def test_all_revealed_when_won(self):
        state = make_state("CAT", water=6, guessed={"C", "A", "T"})
        self.assertEqual(game.display_word(state), "C A T")


if __name__ == "__main__":
    unittest.main()
