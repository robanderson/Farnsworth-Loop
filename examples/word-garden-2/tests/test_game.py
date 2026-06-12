"""Tests for word_garden.game (state and rules).

Covers the UI-free cases of SPEC.md section 16.
"""

import random
import unittest

from word_garden import game
from word_garden.game import GameState


def make_state(secret_word="GARDEN", water=6):
    """Build a fresh GameState with a known secret word for testing."""
    return GameState(
        secret_word=secret_word,
        guessed_letters=set(),
        remaining_water=water,
        weed_count=0,
        max_water=water,
    )


class NewGameTests(unittest.TestCase):
    def test_new_game_full_water_zero_weeds(self):
        state = game.new_game("normal", rng=random.Random(1))
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.max_water, 6)
        self.assertEqual(state.weed_count, 0)
        self.assertEqual(state.guessed_letters, set())
        self.assertFalse(state.game_over)
        self.assertFalse(state.won)

    def test_new_game_word_is_uppercase(self):
        state = game.new_game("easy", rng=random.Random(3))
        self.assertEqual(state.secret_word, state.secret_word.upper())

    def test_new_game_water_matches_difficulty(self):
        self.assertEqual(game.new_game("easy", rng=random.Random(0)).max_water, 8)
        self.assertEqual(game.new_game("hard", rng=random.Random(0)).max_water, 4)

    def test_new_game_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError):
            game.new_game("wat", rng=random.Random(0))


class ValidateGuessTests(unittest.TestCase):
    """SPEC.md section 16 case 5 (rejection) and case 6 (normalization)."""

    def test_valid_letter(self):
        letter, msg = game.validate_guess("a")
        self.assertEqual(letter, "A")
        self.assertEqual(msg, "")

    def test_lowercase_is_normalized(self):
        letter, msg = game.validate_guess("z")
        self.assertEqual(letter, "Z")
        self.assertEqual(msg, "")

    def test_whitespace_is_trimmed(self):
        letter, msg = game.validate_guess("  q  ")
        self.assertEqual(letter, "Q")
        self.assertEqual(msg, "")

    def test_empty_input_rejected(self):
        letter, msg = game.validate_guess("")
        self.assertIsNone(letter)
        self.assertNotEqual(msg, "")

    def test_whitespace_only_rejected(self):
        letter, msg = game.validate_guess("   ")
        self.assertIsNone(letter)
        self.assertNotEqual(msg, "")

    def test_multiple_characters_rejected(self):
        letter, msg = game.validate_guess("apple")
        self.assertIsNone(letter)
        self.assertNotEqual(msg, "")

    def test_number_rejected(self):
        letter, msg = game.validate_guess("7")
        self.assertIsNone(letter)
        self.assertNotEqual(msg, "")

    def test_symbol_rejected(self):
        letter, msg = game.validate_guess("!")
        self.assertIsNone(letter)
        self.assertNotEqual(msg, "")

    def test_does_not_consult_state(self):
        # validate_guess takes only text; repeats are not its job.
        letter, msg = game.validate_guess("A")
        self.assertEqual(letter, "A")
        self.assertEqual(msg, "")


class CorrectGuessTests(unittest.TestCase):
    """SPEC.md section 16 case 1: a correct guess reveals matching letters."""

    def test_correct_guess_records_letter(self):
        state = make_state("GARDEN")
        game.apply_guess(state, "G")
        self.assertIn("G", state.guessed_letters)

    def test_correct_guess_no_water_or_weed_change(self):
        state = make_state("GARDEN", water=6)
        game.apply_guess(state, "A")
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.weed_count, 0)

    def test_correct_guess_reveals_in_display(self):
        state = make_state("GARDEN")
        game.apply_guess(state, "G")
        self.assertEqual(game.display_word(state), "G _ _ _ _ _")

    def test_correct_guess_reveals_all_positions(self):
        state = make_state("SEEDLING")
        game.apply_guess(state, "E")
        # Both E positions revealed.
        self.assertEqual(game.display_word(state), "_ E E _ _ _ _ _")

    def test_correct_guess_positive_message(self):
        state = make_state("GARDEN")
        game.apply_guess(state, "G")
        self.assertEqual(state.status_message, game.MSG_CORRECT)


class IncorrectGuessTests(unittest.TestCase):
    """SPEC.md section 16 cases 2 and 3."""

    def test_wrong_guess_full_effect(self):
        state = make_state("GARDEN", water=6)
        game.apply_guess(state, "Z")
        self.assertEqual(state.remaining_water, 5)  # water -1
        self.assertEqual(state.weed_count, 1)       # weeds +1
        self.assertIn("Z", state.guessed_letters)   # letter recorded
        self.assertEqual(state.status_message, game.MSG_WRONG)

    def test_wrong_guess_does_not_reveal(self):
        state = make_state("GARDEN")
        game.apply_guess(state, "Z")
        self.assertEqual(game.display_word(state), "_ _ _ _ _ _")


class RepeatedGuessTests(unittest.TestCase):
    """SPEC.md section 16 case 4: repeated guesses do not reduce water."""

    def test_repeat_correct_guess_no_change(self):
        state = make_state("GARDEN", water=6)
        game.apply_guess(state, "G")
        before_water = state.remaining_water
        before_weeds = state.weed_count
        game.apply_guess(state, "G")
        self.assertEqual(state.remaining_water, before_water)
        self.assertEqual(state.weed_count, before_weeds)
        self.assertIn("already guessed", state.status_message.lower())

    def test_repeat_wrong_guess_no_further_penalty(self):
        state = make_state("GARDEN", water=6)
        game.apply_guess(state, "Z")  # water 5, weeds 1
        game.apply_guess(state, "Z")  # repeat: no change
        self.assertEqual(state.remaining_water, 5)
        self.assertEqual(state.weed_count, 1)
        self.assertIn("already guessed", state.status_message.lower())


class WinTests(unittest.TestCase):
    """SPEC.md section 16 case 7: the game detects a win."""

    def test_win_detected_and_flags_set(self):
        state = make_state("CAB", water=6)
        for letter in "CAB":
            game.apply_guess(state, letter)
        self.assertTrue(game.is_won(state))
        self.assertTrue(state.won)
        self.assertTrue(state.game_over)
        self.assertFalse(game.is_lost(state))
        self.assertEqual(state.status_message, game.MSG_WIN)

    def test_not_won_partway(self):
        state = make_state("CAB", water=6)
        game.apply_guess(state, "C")
        self.assertFalse(game.is_won(state))
        self.assertFalse(state.game_over)


class LossTests(unittest.TestCase):
    """SPEC.md section 16 case 8: the game detects a loss."""

    def test_loss_detected_and_flags_set(self):
        state = make_state("GARDEN", water=2)
        game.apply_guess(state, "Q")  # water 1
        self.assertFalse(state.game_over)
        game.apply_guess(state, "X")  # water 0 -> loss
        self.assertEqual(state.remaining_water, 0)
        self.assertTrue(game.is_lost(state))
        self.assertTrue(state.game_over)
        self.assertFalse(state.won)
        self.assertEqual(state.status_message, game.MSG_LOSS)

    def test_win_on_last_water_is_not_a_loss(self):
        # Revealing the word as water hits zero should win, not lose.
        state = make_state("AB", water=1)
        game.apply_guess(state, "A")  # correct, no water change
        game.apply_guess(state, "B")  # correct, completes word
        self.assertTrue(state.won)
        self.assertFalse(game.is_lost(state))


class GameOverNoOpTests(unittest.TestCase):
    def test_guess_after_game_over_is_noop(self):
        state = make_state("GARDEN", water=1)
        game.apply_guess(state, "Z")  # water 0 -> loss
        self.assertTrue(state.game_over)
        water = state.remaining_water
        weeds = state.weed_count
        guessed = set(state.guessed_letters)
        game.apply_guess(state, "Q")
        self.assertEqual(state.remaining_water, water)
        self.assertEqual(state.weed_count, weeds)
        self.assertEqual(state.guessed_letters, guessed)
        self.assertEqual(state.status_message, game.MSG_GAME_OVER)


class DisplayWordTests(unittest.TestCase):
    """SPEC.md section 16 case 9: display masks unguessed letters."""

    def test_all_masked_initially(self):
        state = make_state("GARDEN")
        self.assertEqual(game.display_word(state), "_ _ _ _ _ _")

    def test_partial_reveal_space_separated(self):
        state = make_state("GARDEN")
        for letter in ("G", "R", "E"):
            game.apply_guess(state, letter)
        self.assertEqual(game.display_word(state), "G _ R _ E _")

    def test_full_reveal(self):
        state = make_state("CAB")
        for letter in "CAB":
            game.apply_guess(state, letter)
        self.assertEqual(game.display_word(state), "C A B")


if __name__ == "__main__":
    unittest.main()
