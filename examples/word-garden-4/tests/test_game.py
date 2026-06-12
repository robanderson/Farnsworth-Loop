import random
import unittest

from word_garden.game import (
    GameState,
    apply_guess,
    display_word,
    is_lost,
    is_won,
    new_game,
    validate_guess,
    MSG_ALREADY_GUESSED_TEMPLATE,
    MSG_CORRECT,
    MSG_GAME_OVER,
    MSG_INCORRECT,
    MSG_INVALID_NOT_LETTER,
    MSG_INVALID_NOT_SINGLE,
    MSG_LOSS_TEMPLATE,
    MSG_WIN_TEMPLATE,
)


def _make_state(**kwargs) -> GameState:
    """Build a GameState with sensible defaults, overridden by kwargs."""
    defaults = dict(
        secret_word="GARDEN",
        guessed_letters=set(),
        remaining_water=6,
        weed_count=0,
        max_water=6,
    )
    defaults.update(kwargs)
    return GameState(**defaults)


# ---------------------------------------------------------------------------
# new_game
# ---------------------------------------------------------------------------

class TestNewGame(unittest.TestCase):
    def test_initial_state_fields(self):
        rng = random.Random(42)
        state = new_game("normal", rng=rng)
        self.assertIsInstance(state.secret_word, str)
        self.assertTrue(state.secret_word.isupper())
        self.assertEqual(state.guessed_letters, set())
        self.assertEqual(state.remaining_water, 6)
        self.assertEqual(state.max_water, 6)
        self.assertEqual(state.weed_count, 0)
        self.assertEqual(state.status_message, "")
        self.assertFalse(state.game_over)
        self.assertFalse(state.won)

    def test_easy_water_level(self):
        state = new_game("easy", rng=random.Random(1))
        self.assertEqual(state.remaining_water, 8)
        self.assertEqual(state.max_water, 8)

    def test_hard_water_level(self):
        state = new_game("hard", rng=random.Random(1))
        self.assertEqual(state.remaining_water, 4)
        self.assertEqual(state.max_water, 4)


# ---------------------------------------------------------------------------
# validate_guess — Test 5 (invalid input) and Test 6 (lowercase normalised)
# ---------------------------------------------------------------------------

class TestValidateGuess(unittest.TestCase):
    # Test 5: Invalid input is rejected with a specific message.

    def test_empty_string_rejected(self):
        letter, msg = validate_guess("")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_NOT_SINGLE)

    def test_whitespace_only_rejected(self):
        letter, msg = validate_guess("   ")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_NOT_SINGLE)

    def test_multiple_letters_rejected(self):
        letter, msg = validate_guess("AB")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_NOT_SINGLE)

    def test_word_rejected(self):
        letter, msg = validate_guess("apple")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_NOT_SINGLE)

    def test_digit_rejected(self):
        letter, msg = validate_guess("7")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_NOT_LETTER)

    def test_symbol_rejected(self):
        letter, msg = validate_guess("!")
        self.assertIsNone(letter)
        self.assertEqual(msg, MSG_INVALID_NOT_LETTER)

    # Test 6: Lowercase input is normalised to uppercase.

    def test_lowercase_normalised(self):
        letter, msg = validate_guess("a")
        self.assertEqual(letter, "A")
        self.assertEqual(msg, "")

    def test_leading_trailing_spaces_stripped(self):
        letter, msg = validate_guess("  b  ")
        self.assertEqual(letter, "B")
        self.assertEqual(msg, "")

    def test_valid_uppercase_accepted(self):
        letter, msg = validate_guess("Z")
        self.assertEqual(letter, "Z")
        self.assertEqual(msg, "")


# ---------------------------------------------------------------------------
# apply_guess — Tests 1–4, 7–8
# ---------------------------------------------------------------------------

class TestApplyGuessCorrect(unittest.TestCase):
    # Test 1: A correct guess reveals matching letters.

    def test_correct_guess_adds_letter_to_guessed(self):
        state = _make_state(secret_word="GARDEN")
        result = apply_guess(state, "G")
        self.assertIn("G", result.guessed_letters)
        self.assertEqual(result.remaining_water, 6)
        self.assertEqual(result.weed_count, 0)
        self.assertEqual(result.status_message, MSG_CORRECT)
        self.assertFalse(result.game_over)
        self.assertFalse(result.won)

    def test_correct_guess_display_reveals_letter(self):
        state = _make_state(secret_word="GARDEN")
        result = apply_guess(state, "G")
        # GARDEN with only G revealed → G _ _ _ _ _
        self.assertEqual(display_word(result), "G _ _ _ _ _")

    def test_correct_guess_recurring_letter_all_positions_revealed(self):
        # SEEDLING has two E's; both should appear in display
        state = _make_state(secret_word="SEEDLING")
        result = apply_guess(state, "E")
        self.assertIn("E", result.guessed_letters)
        displayed = display_word(result)
        parts = displayed.split(" ")
        self.assertEqual(parts[1], "E")  # index 1 in SEEDLING
        self.assertEqual(parts[2], "E")  # index 2 in SEEDLING


class TestApplyGuessIncorrect(unittest.TestCase):
    # Tests 2 & 3: An incorrect guess reduces water by one and adds one weed.

    def test_incorrect_guess_water_weed_letter(self):
        state = _make_state(secret_word="GARDEN")
        result = apply_guess(state, "Z")
        self.assertIn("Z", result.guessed_letters)
        self.assertEqual(result.remaining_water, 5)
        self.assertEqual(result.weed_count, 1)
        self.assertEqual(result.status_message, MSG_INCORRECT)
        self.assertFalse(result.game_over)
        self.assertFalse(result.won)

    def test_incorrect_guess_exact_decrements(self):
        state = _make_state(remaining_water=4, weed_count=2)
        result = apply_guess(state, "Z")
        self.assertEqual(result.remaining_water, 3)
        self.assertEqual(result.weed_count, 3)


class TestApplyGuessRepeated(unittest.TestCase):
    # Test 4: Repeated guesses do not reduce water or weeds.

    def test_repeated_correct_letter_no_change(self):
        state = _make_state(
            secret_word="GARDEN",
            guessed_letters={"G"},
            remaining_water=6,
            weed_count=0,
        )
        result = apply_guess(state, "G")
        self.assertEqual(result.remaining_water, 6)
        self.assertEqual(result.weed_count, 0)
        self.assertEqual(result.guessed_letters, {"G"})
        self.assertEqual(
            result.status_message,
            MSG_ALREADY_GUESSED_TEMPLATE.format(letter="G"),
        )
        self.assertFalse(result.game_over)
        self.assertFalse(result.won)

    def test_repeated_wrong_letter_no_change(self):
        state = _make_state(
            secret_word="GARDEN",
            guessed_letters={"Z"},
            remaining_water=5,
            weed_count=1,
        )
        result = apply_guess(state, "Z")
        self.assertEqual(result.remaining_water, 5)
        self.assertEqual(result.weed_count, 1)
        self.assertEqual(result.guessed_letters, {"Z"})
        self.assertEqual(
            result.status_message,
            MSG_ALREADY_GUESSED_TEMPLATE.format(letter="Z"),
        )


class TestApplyGuessWin(unittest.TestCase):
    # Test 7: The game detects a win.

    def test_win_on_last_letter(self):
        state = _make_state(
            secret_word="GARDEN",
            guessed_letters={"G", "A", "R", "D", "E"},
            remaining_water=6,
            weed_count=0,
        )
        result = apply_guess(state, "N")
        self.assertIn("N", result.guessed_letters)
        self.assertTrue(result.game_over)
        self.assertTrue(result.won)
        self.assertEqual(result.remaining_water, 6)
        self.assertEqual(result.weed_count, 0)
        self.assertEqual(result.status_message, MSG_WIN_TEMPLATE.format(word="GARDEN"))
        self.assertTrue(is_won(result))
        self.assertFalse(is_lost(result))

    def test_guess_after_win_is_noop(self):
        state = _make_state(game_over=True, won=True, remaining_water=6, weed_count=0)
        result = apply_guess(state, "X")
        self.assertEqual(result.remaining_water, 6)
        self.assertEqual(result.weed_count, 0)
        self.assertTrue(result.game_over)
        self.assertTrue(result.won)
        self.assertEqual(result.status_message, MSG_GAME_OVER)


class TestApplyGuessLoss(unittest.TestCase):
    # Test 8: The game detects a loss.

    def test_loss_on_final_water(self):
        state = _make_state(
            secret_word="GARDEN",
            remaining_water=1,
            weed_count=5,
        )
        result = apply_guess(state, "Z")
        self.assertIn("Z", result.guessed_letters)
        self.assertTrue(result.game_over)
        self.assertFalse(result.won)
        self.assertEqual(result.remaining_water, 0)
        self.assertEqual(result.weed_count, 6)
        self.assertEqual(result.status_message, MSG_LOSS_TEMPLATE.format(word="GARDEN"))
        self.assertFalse(is_won(result))
        self.assertTrue(is_lost(result))

    def test_guess_after_loss_is_noop(self):
        state = _make_state(game_over=True, won=False, remaining_water=0, weed_count=6)
        result = apply_guess(state, "A")
        self.assertEqual(result.remaining_water, 0)
        self.assertEqual(result.weed_count, 6)
        self.assertTrue(result.game_over)
        self.assertFalse(result.won)
        self.assertEqual(result.status_message, MSG_GAME_OVER)


class TestApplyGuessImmutability(unittest.TestCase):
    def test_original_state_not_mutated_on_correct_guess(self):
        state = _make_state(secret_word="GARDEN")
        original_guessed = frozenset(state.guessed_letters)
        original_water = state.remaining_water
        apply_guess(state, "G")
        self.assertEqual(state.guessed_letters, original_guessed)
        self.assertEqual(state.remaining_water, original_water)

    def test_original_state_not_mutated_on_wrong_guess(self):
        state = _make_state(secret_word="GARDEN")
        original_guessed = frozenset(state.guessed_letters)
        original_water = state.remaining_water
        apply_guess(state, "Z")
        self.assertEqual(state.guessed_letters, original_guessed)
        self.assertEqual(state.remaining_water, original_water)


# ---------------------------------------------------------------------------
# display_word — Test 9
# ---------------------------------------------------------------------------

class TestDisplayWord(unittest.TestCase):
    # Test 9: The displayed word masks unguessed letters.

    def test_all_unguessed_shows_blanks(self):
        state = _make_state(secret_word="GARDEN", guessed_letters=set())
        self.assertEqual(display_word(state), "_ _ _ _ _ _")

    def test_some_guessed_shows_mixed(self):
        # GARDEN: G(0) A(1) R(2) D(3) E(4) N(5) — G and R guessed
        state = _make_state(secret_word="GARDEN", guessed_letters={"G", "R"})
        self.assertEqual(display_word(state), "G _ R _ _ _")

    def test_all_guessed_shows_full_word(self):
        state = _make_state(
            secret_word="GARDEN",
            guessed_letters={"G", "A", "R", "D", "E", "N"},
        )
        self.assertEqual(display_word(state), "G A R D E N")

    def test_single_letter_word(self):
        state = _make_state(secret_word="A", guessed_letters=set())
        self.assertEqual(display_word(state), "_")

    def test_single_letter_word_guessed(self):
        state = _make_state(secret_word="A", guessed_letters={"A"})
        self.assertEqual(display_word(state), "A")


# ---------------------------------------------------------------------------
# is_won / is_lost
# ---------------------------------------------------------------------------

class TestIsWonIsLost(unittest.TestCase):
    def test_is_won_false_when_incomplete(self):
        state = _make_state(secret_word="GARDEN", guessed_letters={"G"})
        self.assertFalse(is_won(state))

    def test_is_won_true_when_all_letters_guessed(self):
        state = _make_state(
            secret_word="GARDEN",
            guessed_letters={"G", "A", "R", "D", "E", "N"},
        )
        self.assertTrue(is_won(state))

    def test_is_won_true_with_extra_guessed_letters(self):
        # Extra wrong guesses don't prevent a win
        state = _make_state(
            secret_word="GARDEN",
            guessed_letters={"G", "A", "R", "D", "E", "N", "Z", "X"},
        )
        self.assertTrue(is_won(state))

    def test_is_lost_false_when_water_remains(self):
        state = _make_state(remaining_water=1)
        self.assertFalse(is_lost(state))

    def test_is_lost_true_when_water_zero_and_not_won(self):
        state = _make_state(secret_word="GARDEN", remaining_water=0, guessed_letters=set())
        self.assertTrue(is_lost(state))

    def test_is_lost_false_when_won_despite_zero_water(self):
        # Logically shouldn't happen in normal play, but the predicate should be correct
        state = _make_state(
            secret_word="GARDEN",
            guessed_letters={"G", "A", "R", "D", "E", "N"},
            remaining_water=0,
        )
        self.assertFalse(is_lost(state))
