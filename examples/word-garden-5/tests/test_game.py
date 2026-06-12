"""Tests for word_garden/game.py — the pure game engine.

All tests use direct state construction (Code Tips #8) and inject
randomness via the ``rng`` parameter (Code Tips #6) rather than patching.
Message assertions import the constants from game.py (Code Tips #7).
"""

import random
import unittest

from word_garden.game import (
    GameState,
    MSG_ALREADY_GUESSED_TEMPLATE,
    MSG_CORRECT_GUESS,
    MSG_GAME_OVER_ALREADY,
    MSG_INVALID_EMPTY,
    MSG_INVALID_MULTIPLE,
    MSG_INVALID_NOT_ALPHA,
    MSG_LOSS_TITLE,
    MSG_WIN_TITLE,
    apply_guess,
    display_word,
    is_lost,
    is_won,
    new_game,
    validate_guess,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(
    secret: str = "GARDEN",
    guessed: set[str] | None = None,
    water: int = 6,
    weeds: int = 0,
    max_water: int = 6,
    status: str = "",
    game_over: bool = False,
    won: bool = False,
) -> GameState:
    """Build a GameState directly with pinned values (Code Tips #8)."""
    return GameState(
        secret_word=secret,
        guessed_letters=guessed if guessed is not None else set(),
        remaining_water=water,
        weed_count=weeds,
        max_water=max_water,
        status_message=status,
        game_over=game_over,
        won=won,
    )


# ---------------------------------------------------------------------------
# 1. Correct guess reveals matching letters
# ---------------------------------------------------------------------------

class TestCorrectGuess(unittest.TestCase):
    def test_letter_added_to_guessed(self):
        state = _state(secret="GARDEN")
        result = apply_guess(state, "G")
        self.assertIn("G", result.guessed_letters)

    def test_correct_guess_no_water_loss(self):
        state = _state(secret="GARDEN", water=6)
        result = apply_guess(state, "G")
        self.assertEqual(result.remaining_water, 6)

    def test_correct_guess_no_weed_increase(self):
        state = _state(secret="GARDEN", weeds=0)
        result = apply_guess(state, "G")
        self.assertEqual(result.weed_count, 0)

    def test_correct_guess_message(self):
        state = _state(secret="GARDEN")
        result = apply_guess(state, "G")
        self.assertEqual(result.status_message, MSG_CORRECT_GUESS)

    def test_display_word_reveals_guessed_letter(self):
        state = _state(secret="GARDEN", guessed={"G"})
        self.assertEqual(display_word(state), "G _ _ _ _ _")


# ---------------------------------------------------------------------------
# 2 & 3. Incorrect guess reduces water by 1 AND increases weeds by 1
# ---------------------------------------------------------------------------

class TestIncorrectGuess(unittest.TestCase):
    def test_water_decreases_by_exactly_one(self):
        state = _state(secret="GARDEN", water=6)
        result = apply_guess(state, "Z")
        self.assertEqual(result.remaining_water, 5)

    def test_weed_count_increases_by_exactly_one(self):
        state = _state(secret="GARDEN", weeds=0)
        result = apply_guess(state, "Z")
        self.assertEqual(result.weed_count, 1)

    def test_wrong_letter_recorded(self):
        state = _state(secret="GARDEN")
        result = apply_guess(state, "Z")
        self.assertIn("Z", result.guessed_letters)

    def test_wrong_guess_message(self):
        from word_garden.game import MSG_WRONG_GUESS
        state = _state(secret="GARDEN", water=6)
        result = apply_guess(state, "Z")
        self.assertEqual(result.status_message, MSG_WRONG_GUESS)


# ---------------------------------------------------------------------------
# 4. Repeated guess — water, weeds, guessed set unchanged; message set
# ---------------------------------------------------------------------------

class TestRepeatedGuess(unittest.TestCase):
    def test_no_water_change(self):
        state = _state(secret="GARDEN", guessed={"A"}, water=5)
        result = apply_guess(state, "A")
        self.assertEqual(result.remaining_water, 5)

    def test_no_weed_change(self):
        state = _state(secret="GARDEN", guessed={"A"}, weeds=1)
        result = apply_guess(state, "A")
        self.assertEqual(result.weed_count, 1)

    def test_guessed_set_unchanged(self):
        state = _state(secret="GARDEN", guessed={"A"})
        result = apply_guess(state, "A")
        self.assertEqual(result.guessed_letters, {"A"})

    def test_repeated_guess_message(self):
        state = _state(secret="GARDEN", guessed={"A"})
        result = apply_guess(state, "A")
        expected = MSG_ALREADY_GUESSED_TEMPLATE.format(letter="A")
        self.assertEqual(result.status_message, expected)


# ---------------------------------------------------------------------------
# 5. Invalid input is rejected (validate_guess — no state consulted)
# ---------------------------------------------------------------------------

class TestValidateGuess(unittest.TestCase):
    def test_empty_string_rejected(self):
        letter, msg = validate_guess("")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_EMPTY)

    def test_whitespace_only_rejected(self):
        letter, msg = validate_guess("   ")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_EMPTY)

    def test_multiple_chars_rejected(self):
        letter, msg = validate_guess("ab")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_MULTIPLE)

    def test_digit_rejected(self):
        letter, msg = validate_guess("7")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_NOT_ALPHA)

    def test_symbol_rejected(self):
        letter, msg = validate_guess("!")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_NOT_ALPHA)

    # 6. Lowercase normalised
    def test_lowercase_normalised(self):
        letter, msg = validate_guess("a")
        self.assertEqual(letter, "A")
        self.assertEqual(msg, "")

    def test_valid_with_surrounding_spaces(self):
        letter, msg = validate_guess("  z  ")
        self.assertEqual(letter, "Z")
        self.assertEqual(msg, "")


# ---------------------------------------------------------------------------
# 7. Game detects a win
# ---------------------------------------------------------------------------

class TestWinCondition(unittest.TestCase):
    def test_is_won_when_all_letters_guessed(self):
        state = _state(secret="CAT", guessed={"C", "A", "T"})
        self.assertTrue(is_won(state))

    def test_is_not_won_when_letters_missing(self):
        state = _state(secret="CAT", guessed={"C", "A"})
        self.assertFalse(is_won(state))

    def test_is_not_won_empty_guesses(self):
        state = _state(secret="CAT", guessed=set())
        self.assertFalse(is_won(state))

    def test_apply_guess_sets_won_flag(self):
        # One letter away from winning
        state = _state(secret="CAT", guessed={"C", "A"}, water=4, weeds=0)
        result = apply_guess(state, "T")
        self.assertTrue(result.won)
        self.assertTrue(result.game_over)

    def test_win_status_message_is_win_title(self):
        """End-of-game message must be the win title, not the turn message."""
        state = _state(secret="CAT", guessed={"C", "A"}, water=4, weeds=0)
        result = apply_guess(state, "T")
        self.assertEqual(result.status_message, MSG_WIN_TITLE)


# ---------------------------------------------------------------------------
# 8. Game detects a loss
# ---------------------------------------------------------------------------

class TestLossCondition(unittest.TestCase):
    def test_is_lost_when_water_zero_and_not_won(self):
        state = _state(secret="CAT", guessed={"Z"}, water=0)
        self.assertTrue(is_lost(state))

    def test_is_not_lost_when_water_remains(self):
        state = _state(secret="CAT", guessed={"Z"}, water=1)
        self.assertFalse(is_lost(state))

    def test_is_not_lost_when_won(self):
        # Even with water=0, a won state is not a loss
        state = _state(secret="CAT", guessed={"C", "A", "T"}, water=0)
        self.assertFalse(is_lost(state))

    def test_apply_guess_sets_game_over_on_last_water(self):
        state = _state(secret="CAT", guessed={"C", "A"}, water=1, weeds=0)
        result = apply_guess(state, "Z")  # wrong guess, water → 0
        self.assertTrue(result.game_over)
        self.assertFalse(result.won)

    def test_loss_status_message_is_loss_title(self):
        """End-of-game message must be the loss title, not the turn message."""
        state = _state(secret="CAT", guessed={"C", "A"}, water=1, weeds=0)
        result = apply_guess(state, "Z")
        self.assertEqual(result.status_message, MSG_LOSS_TITLE)

    def test_is_lost_predicate_standalone(self):
        """is_lost must be correct when called directly (Code Tips #10)."""
        # Won state at water=0 — must NOT be lost
        won_at_zero = _state(secret="IT", guessed={"I", "T"}, water=0)
        self.assertFalse(is_lost(won_at_zero))

        # Not-won at water=0 — must be lost
        lost = _state(secret="IT", guessed={"X"}, water=0)
        self.assertTrue(is_lost(lost))


# ---------------------------------------------------------------------------
# 9. display_word masks unguessed letters
# ---------------------------------------------------------------------------

class TestDisplayWord(unittest.TestCase):
    def test_all_masked_at_start(self):
        state = _state(secret="GARDEN", guessed=set())
        self.assertEqual(display_word(state), "_ _ _ _ _ _")

    def test_some_letters_revealed(self):
        state = _state(secret="GARDEN", guessed={"G", "R"})
        self.assertEqual(display_word(state), "G _ R _ _ _")

    def test_all_revealed(self):
        state = _state(secret="GARDEN", guessed={"G", "A", "R", "D", "E", "N"})
        self.assertEqual(display_word(state), "G A R D E N")


# ---------------------------------------------------------------------------
# Already-game-over guard
# ---------------------------------------------------------------------------

class TestAlreadyGameOver(unittest.TestCase):
    def test_no_op_when_game_already_over(self):
        state = _state(secret="CAT", game_over=True, won=True, water=3)
        result = apply_guess(state, "X")
        self.assertEqual(result.remaining_water, 3)
        self.assertTrue(result.game_over)
        self.assertEqual(result.status_message, MSG_GAME_OVER_ALREADY)


# ---------------------------------------------------------------------------
# new_game factory
# ---------------------------------------------------------------------------

class TestNewGame(unittest.TestCase):
    def test_new_game_word_is_uppercase(self):
        rng = random.Random(42)
        state = new_game(rng=rng)
        self.assertEqual(state.secret_word, state.secret_word.upper())

    def test_new_game_normal_water(self):
        rng = random.Random(42)
        state = new_game(difficulty="normal", rng=rng)
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.max_water, 6)

    def test_new_game_easy_water(self):
        rng = random.Random(0)
        state = new_game(difficulty="easy", rng=rng)
        self.assertEqual(state.remaining_water, 8)

    def test_new_game_hard_water(self):
        rng = random.Random(0)
        state = new_game(difficulty="hard", rng=rng)
        self.assertEqual(state.remaining_water, 4)

    def test_new_game_zero_weeds(self):
        rng = random.Random(42)
        state = new_game(rng=rng)
        self.assertEqual(state.weed_count, 0)

    def test_new_game_empty_guesses(self):
        rng = random.Random(42)
        state = new_game(rng=rng)
        self.assertEqual(state.guessed_letters, set())
