"""Tests for word_garden.game — SPEC.md section 16 cases."""

import unittest

from word_garden.game import (
    GameState,
    MSG_CORRECT_GUESS,
    MSG_WRONG_GUESS,
    MSG_ALREADY_GUESSED,
    MSG_GAME_OVER_ALREADY,
    MSG_WIN,
    MSG_LOSS,
    MSG_EMPTY_INPUT,
    MSG_MULTIPLE_CHARS,
    MSG_NOT_A_LETTER,
    apply_guess,
    display_word,
    is_lost,
    is_won,
    new_game,
    validate_guess,
)


# ---------------------------------------------------------------------------
# Fixture helpers
#
# Per .code-tips.md: build fixtures by constructing GameState directly with
# pinned values — never by calling new_game() and overwriting fields.
# ---------------------------------------------------------------------------

def _state(
    secret_word: str = "GARDEN",
    guessed_letters=None,
    remaining_water: int = 6,
    weed_count: int = 0,
    max_water: int = 6,
    status_message: str = "",
    game_over: bool = False,
    won: bool = False,
) -> GameState:
    return GameState(
        secret_word=secret_word,
        guessed_letters=set(guessed_letters) if guessed_letters is not None else set(),
        remaining_water=remaining_water,
        weed_count=weed_count,
        max_water=max_water,
        status_message=status_message,
        game_over=game_over,
        won=won,
    )


# ---------------------------------------------------------------------------
# SPEC section 16, case 1: correct guess reveals matching letters
# ---------------------------------------------------------------------------

class TestCorrectGuess(unittest.TestCase):
    """Case 1: correct guess reveals matching letters."""

    def test_correct_guess_letter_recorded(self):
        state = _state(secret_word="GARDEN")
        new_state = apply_guess(state, "G")
        self.assertIn("G", new_state.guessed_letters)

    def test_correct_guess_no_water_loss(self):
        state = _state(secret_word="GARDEN", remaining_water=6)
        new_state = apply_guess(state, "G")
        self.assertEqual(new_state.remaining_water, 6)

    def test_correct_guess_no_weed_gain(self):
        state = _state(secret_word="GARDEN", weed_count=0)
        new_state = apply_guess(state, "G")
        self.assertEqual(new_state.weed_count, 0)

    def test_correct_guess_positive_message(self):
        state = _state(secret_word="GARDEN")
        new_state = apply_guess(state, "G")
        self.assertEqual(new_state.status_message, MSG_CORRECT_GUESS)

    def test_correct_guess_display_reveals_letter(self):
        """Case 9 + Case 1 combined: displayed word shows the guessed letter."""
        state = _state(secret_word="GARDEN", guessed_letters={"G"})
        displayed = display_word(state)
        # G is guessed, rest are blanks
        self.assertEqual(displayed, "G _ R D E N".replace("R", "_").replace("D", "_")
                         .replace("E", "_").replace("N", "_"))

    def test_correct_guess_reveals_all_matching_positions(self):
        """All occurrences of a letter in the secret word are revealed."""
        state = _state(secret_word="BANANA")
        new_state = apply_guess(state, "A")
        self.assertIn("A", new_state.guessed_letters)
        displayed = display_word(new_state)
        # BANANA -> _ A _ A _ A
        self.assertEqual(displayed, "_ A _ A _ A")


# ---------------------------------------------------------------------------
# SPEC section 16, cases 2 & 3: wrong guess reduces water and raises weeds
# ---------------------------------------------------------------------------

class TestWrongGuess(unittest.TestCase):
    """Cases 2 & 3: wrong guess changes water, weeds, and records letter."""

    def test_wrong_guess_water_decreases_by_exactly_1(self):
        state = _state(secret_word="GARDEN", remaining_water=6)
        new_state = apply_guess(state, "Z")
        self.assertEqual(new_state.remaining_water, 5)

    def test_wrong_guess_weed_increases_by_exactly_1(self):
        state = _state(secret_word="GARDEN", weed_count=0)
        new_state = apply_guess(state, "Z")
        self.assertEqual(new_state.weed_count, 1)

    def test_wrong_guess_letter_recorded(self):
        state = _state(secret_word="GARDEN")
        new_state = apply_guess(state, "Z")
        self.assertIn("Z", new_state.guessed_letters)

    def test_wrong_guess_message(self):
        state = _state(secret_word="GARDEN")
        new_state = apply_guess(state, "Z")
        self.assertEqual(new_state.status_message, MSG_WRONG_GUESS)

    def test_wrong_guess_all_positive_combined(self):
        """All three effects (water -1, weeds +1, letter recorded) together."""
        state = _state(secret_word="GARDEN", remaining_water=5, weed_count=1)
        new_state = apply_guess(state, "X")
        self.assertEqual(new_state.remaining_water, 4)
        self.assertEqual(new_state.weed_count, 2)
        self.assertIn("X", new_state.guessed_letters)
        self.assertEqual(new_state.status_message, MSG_WRONG_GUESS)


# ---------------------------------------------------------------------------
# SPEC section 16, case 4: repeated guess does not reduce water
# ---------------------------------------------------------------------------

class TestRepeatedGuess(unittest.TestCase):
    """Case 4: repeated guess changes nothing except the message."""

    def test_repeated_guess_no_water_change(self):
        state = _state(secret_word="GARDEN", guessed_letters={"A"}, remaining_water=5)
        new_state = apply_guess(state, "A")
        self.assertEqual(new_state.remaining_water, 5)

    def test_repeated_guess_no_weed_change(self):
        state = _state(secret_word="GARDEN", guessed_letters={"A"}, weed_count=1)
        new_state = apply_guess(state, "A")
        self.assertEqual(new_state.weed_count, 1)

    def test_repeated_guess_message_contains_letter(self):
        state = _state(secret_word="GARDEN", guessed_letters={"A"})
        new_state = apply_guess(state, "A")
        expected = MSG_ALREADY_GUESSED.format(letter="A")
        self.assertEqual(new_state.status_message, expected)
        self.assertIn("A", new_state.status_message)

    def test_repeated_guess_letter_set_unchanged(self):
        """Guessed letters set is not duplicated or mutated."""
        state = _state(secret_word="GARDEN", guessed_letters={"A"})
        new_state = apply_guess(state, "A")
        self.assertEqual(new_state.guessed_letters, {"A"})


# ---------------------------------------------------------------------------
# SPEC section 16, case 5: invalid input is rejected
# ---------------------------------------------------------------------------

class TestValidateGuess(unittest.TestCase):
    """Case 5: invalid input yields None + specific message; case 6: lowercase normalized."""

    # -- Empty input ----------------------------------------------------------

    def test_empty_string_rejected(self):
        letter, msg = validate_guess("")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_EMPTY_INPUT)

    def test_whitespace_only_rejected(self):
        letter, msg = validate_guess("   ")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_EMPTY_INPUT)

    # -- Multiple characters --------------------------------------------------

    def test_multiple_chars_rejected(self):
        letter, msg = validate_guess("apple")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_MULTIPLE_CHARS)

    def test_two_chars_rejected(self):
        letter, msg = validate_guess("ab")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_MULTIPLE_CHARS)

    # -- Non-alpha characters --------------------------------------------------

    def test_digit_rejected(self):
        letter, msg = validate_guess("7")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_NOT_A_LETTER)

    def test_symbol_rejected(self):
        letter, msg = validate_guess("!")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_NOT_A_LETTER)

    # -- Case 6: lowercase normalized -----------------------------------------

    def test_lowercase_normalized_to_uppercase(self):
        letter, msg = validate_guess("a")
        self.assertEqual(letter, "A")
        self.assertEqual(msg, "")

    def test_uppercase_accepted(self):
        letter, msg = validate_guess("Z")
        self.assertEqual(letter, "Z")
        self.assertEqual(msg, "")

    def test_leading_trailing_whitespace_stripped(self):
        letter, msg = validate_guess("  b  ")
        self.assertEqual(letter, "B")
        self.assertEqual(msg, "")

    # -- Valid input returns (letter, "") -------------------------------------

    def test_valid_returns_empty_error_string(self):
        letter, msg = validate_guess("G")
        self.assertEqual(letter, "G")
        self.assertEqual(msg, "")

    # -- validate_guess does NOT mutate state ---------------------------------

    def test_invalid_input_does_not_mutate_state(self):
        """Validation is state-free; calling it leaves GameState untouched."""
        state = _state(secret_word="GARDEN", remaining_water=6, weed_count=0)
        validate_guess("99")  # invalid, but no state passed
        # No exception; state reference unchanged
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.weed_count, 0)


# ---------------------------------------------------------------------------
# SPEC section 16, case 7: win detection
# ---------------------------------------------------------------------------

class TestWinDetection(unittest.TestCase):
    """Case 7: game detects win condition."""

    def test_is_won_true_when_all_letters_guessed(self):
        state = _state(secret_word="GO", guessed_letters={"G", "O"})
        self.assertTrue(is_won(state))

    def test_is_won_false_when_letters_missing(self):
        state = _state(secret_word="GO", guessed_letters={"G"})
        self.assertFalse(is_won(state))

    def test_apply_guess_sets_game_over_and_won_on_last_letter(self):
        """End-to-end win: force known scenario, assert the win artifact."""
        # Secret word "GO", G already guessed. Apply O to win.
        state = _state(
            secret_word="GO",
            guessed_letters={"G"},
            remaining_water=6,
            weed_count=0,
        )
        new_state = apply_guess(state, "O")
        # POSITIVE assertions: all three win indicators
        self.assertTrue(new_state.won)
        self.assertTrue(new_state.game_over)
        self.assertIn("O", new_state.guessed_letters)

    def test_win_status_message_set(self):
        """Per .code-tips.md: end-of-process test MUST assert the terminal message."""
        state = _state(
            secret_word="GO",
            guessed_letters={"G"},
            remaining_water=6,
        )
        new_state = apply_guess(state, "O")
        expected_msg = MSG_WIN.format(word="GO")
        self.assertEqual(new_state.status_message, expected_msg)

    def test_win_water_unchanged_on_last_correct_guess(self):
        state = _state(secret_word="GO", guessed_letters={"G"}, remaining_water=3)
        new_state = apply_guess(state, "O")
        self.assertEqual(new_state.remaining_water, 3)


# ---------------------------------------------------------------------------
# SPEC section 16, case 8: loss detection
# ---------------------------------------------------------------------------

class TestLossDetection(unittest.TestCase):
    """Case 8: game detects loss condition."""

    def test_is_lost_true_when_water_zero(self):
        state = _state(secret_word="GO", guessed_letters=set(), remaining_water=0)
        self.assertTrue(is_lost(state))

    def test_is_lost_false_when_water_positive(self):
        state = _state(secret_word="GO", remaining_water=1)
        self.assertFalse(is_lost(state))

    def test_is_lost_false_when_won(self):
        """Win trumps water=0 loss check."""
        state = _state(
            secret_word="GO",
            guessed_letters={"G", "O"},
            remaining_water=0,
        )
        self.assertFalse(is_lost(state))

    def test_apply_guess_sets_game_over_on_last_water(self):
        """End-to-end loss: force water=1, wrong guess -> game over."""
        state = _state(
            secret_word="GARDEN",
            guessed_letters={"Z"},
            remaining_water=1,
            weed_count=1,
        )
        new_state = apply_guess(state, "X")
        # POSITIVE assertions: both loss indicators
        self.assertTrue(new_state.game_over)
        self.assertFalse(new_state.won)
        self.assertEqual(new_state.remaining_water, 0)
        self.assertEqual(new_state.weed_count, 2)
        self.assertIn("X", new_state.guessed_letters)

    def test_loss_status_message_set(self):
        """Per .code-tips.md: end-of-process test MUST assert the terminal message."""
        state = _state(secret_word="GARDEN", remaining_water=1)
        new_state = apply_guess(state, "Z")
        expected_msg = MSG_LOSS.format(word="GARDEN")
        self.assertEqual(new_state.status_message, expected_msg)


# ---------------------------------------------------------------------------
# SPEC section 16, case 9: display_word masks unguessed letters
# ---------------------------------------------------------------------------

class TestDisplayWord(unittest.TestCase):
    """Case 9: displayed word masks unguessed letters."""

    def test_all_unguessed_shows_blanks(self):
        state = _state(secret_word="GARDEN", guessed_letters=set())
        self.assertEqual(display_word(state), "_ _ _ _ _ _")

    def test_all_guessed_shows_full_word(self):
        state = _state(
            secret_word="GARDEN",
            guessed_letters={"G", "A", "R", "D", "E", "N"},
        )
        self.assertEqual(display_word(state), "G A R D E N")

    def test_partial_guess_shows_correct_mix(self):
        state = _state(secret_word="GARDEN", guessed_letters={"G", "E"})
        self.assertEqual(display_word(state), "G _ _ _ E _")

    def test_single_letter_word(self):
        state = _state(secret_word="A", guessed_letters=set())
        self.assertEqual(display_word(state), "_")

    def test_single_letter_guessed(self):
        state = _state(secret_word="A", guessed_letters={"A"})
        self.assertEqual(display_word(state), "A")


# ---------------------------------------------------------------------------
# Post-game no-op
# ---------------------------------------------------------------------------

class TestPostGameNoOp(unittest.TestCase):
    def test_guessing_after_game_over_is_noop_with_message(self):
        state = _state(secret_word="GARDEN", game_over=True, won=True, remaining_water=6)
        new_state = apply_guess(state, "Z")
        # State is unchanged; message tells user game is over
        self.assertEqual(new_state.remaining_water, 6)
        self.assertEqual(new_state.status_message, MSG_GAME_OVER_ALREADY)
        self.assertTrue(new_state.game_over)

    def test_guessing_after_loss_is_noop(self):
        state = _state(secret_word="GARDEN", game_over=True, won=False, remaining_water=0)
        new_state = apply_guess(state, "G")
        self.assertEqual(new_state.remaining_water, 0)
        self.assertFalse(new_state.won)
        self.assertEqual(new_state.status_message, MSG_GAME_OVER_ALREADY)


# ---------------------------------------------------------------------------
# new_game factory
# ---------------------------------------------------------------------------

class TestNewGame(unittest.TestCase):
    def test_new_game_returns_gamestate(self):
        import random
        g = new_game(rng=random.Random(0))
        self.assertIsInstance(g, GameState)

    def test_new_game_word_is_uppercase(self):
        import random
        g = new_game(rng=random.Random(0))
        self.assertEqual(g.secret_word, g.secret_word.upper())

    def test_new_game_normal_water(self):
        import random
        g = new_game(difficulty="normal", rng=random.Random(0))
        self.assertEqual(g.remaining_water, 6)
        self.assertEqual(g.max_water, 6)

    def test_new_game_easy_water(self):
        import random
        g = new_game(difficulty="easy", rng=random.Random(0))
        self.assertEqual(g.remaining_water, 8)

    def test_new_game_hard_water(self):
        import random
        g = new_game(difficulty="hard", rng=random.Random(0))
        self.assertEqual(g.remaining_water, 4)

    def test_new_game_zero_weeds(self):
        import random
        g = new_game(rng=random.Random(0))
        self.assertEqual(g.weed_count, 0)

    def test_new_game_empty_guessed_letters(self):
        import random
        g = new_game(rng=random.Random(0))
        self.assertEqual(g.guessed_letters, set())

    def test_new_game_not_over(self):
        import random
        g = new_game(rng=random.Random(0))
        self.assertFalse(g.game_over)
        self.assertFalse(g.won)

    def test_new_game_unknown_difficulty_raises(self):
        with self.assertRaises(ValueError):
            new_game(difficulty="legendary")


# ---------------------------------------------------------------------------
# GameState immutability: apply_guess returns a new object
# ---------------------------------------------------------------------------

class TestImmutability(unittest.TestCase):
    def test_apply_guess_returns_new_object(self):
        state = _state(secret_word="GARDEN")
        new_state = apply_guess(state, "G")
        self.assertIsNot(state, new_state)

    def test_original_state_not_mutated_by_correct_guess(self):
        state = _state(secret_word="GARDEN", remaining_water=6, weed_count=0)
        apply_guess(state, "G")
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.weed_count, 0)
        self.assertNotIn("G", state.guessed_letters)

    def test_original_state_not_mutated_by_wrong_guess(self):
        state = _state(secret_word="GARDEN", remaining_water=6, weed_count=0)
        apply_guess(state, "Z")
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.weed_count, 0)


# ---------------------------------------------------------------------------
# Message constants imported in tests (per .code-tips.md)
# ---------------------------------------------------------------------------

class TestMessageConstants(unittest.TestCase):
    """Ensure all user-facing message constants are defined and non-empty."""

    def test_msg_correct_guess_defined(self):
        self.assertIsInstance(MSG_CORRECT_GUESS, str)
        self.assertTrue(MSG_CORRECT_GUESS)

    def test_msg_wrong_guess_defined(self):
        self.assertIsInstance(MSG_WRONG_GUESS, str)
        self.assertTrue(MSG_WRONG_GUESS)

    def test_msg_already_guessed_template(self):
        msg = MSG_ALREADY_GUESSED.format(letter="A")
        self.assertIn("A", msg)

    def test_msg_win_template(self):
        msg = MSG_WIN.format(word="GARDEN")
        self.assertIn("GARDEN", msg)

    def test_msg_loss_template(self):
        msg = MSG_LOSS.format(word="GARDEN")
        self.assertIn("GARDEN", msg)

    def test_msg_empty_input_defined(self):
        self.assertIsInstance(MSG_EMPTY_INPUT, str)
        self.assertTrue(MSG_EMPTY_INPUT)

    def test_msg_not_a_letter_defined(self):
        self.assertIsInstance(MSG_NOT_A_LETTER, str)
        self.assertTrue(MSG_NOT_A_LETTER)

    def test_msg_game_over_already_defined(self):
        self.assertIsInstance(MSG_GAME_OVER_ALREADY, str)
        self.assertTrue(MSG_GAME_OVER_ALREADY)


if __name__ == "__main__":
    unittest.main()
