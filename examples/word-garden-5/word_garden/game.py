"""Core game engine for Word Garden.

No stdin/stdout here — all I/O is handled by main.py (injected functions).
"""

from __future__ import annotations

import random as _random
from dataclasses import dataclass, field

from word_garden import words as _words

# ---------------------------------------------------------------------------
# User-facing message constants (single source of truth — SPEC section 7)
# Tests MUST import these constants rather than re-typing the strings.
# ---------------------------------------------------------------------------

MSG_CORRECT_GUESS = "Good guess! The garden grows."
MSG_WRONG_GUESS = "No match. A weed appears."
MSG_ALREADY_GUESSED_TEMPLATE = "You already guessed {letter}. Try another letter."
MSG_GAME_OVER_ALREADY = "The game is already over."

# Win / loss end-screen messages (also used by ui.py)
MSG_WIN_TITLE = "\U0001f33b Bloom!"
MSG_WIN_BODY_TEMPLATE = "You guessed the word: {word}\nThe garden is thriving."
MSG_LOSS_TITLE = "\U0001f940 The garden ran out of water."
MSG_LOSS_BODY_TEMPLATE = "The word was: {word}\nTry again and grow a new garden."

# Validation messages
MSG_INVALID_EMPTY = "Please enter a single letter."
MSG_INVALID_MULTIPLE = "Please enter a single letter."
MSG_INVALID_NOT_ALPHA = "That is not a letter."


# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """Complete, serialisable snapshot of one Word Garden game."""

    secret_word: str
    guessed_letters: set[str]
    remaining_water: int
    weed_count: int
    max_water: int
    status_message: str = ""
    game_over: bool = False
    won: bool = False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def new_game(difficulty: str = "normal", rng: _random.Random | None = None) -> GameState:
    """Create a fresh GameState for the given difficulty.

    Parameters
    ----------
    difficulty:
        Forwarded to ``words.select_word`` and ``words.water_for``.
    rng:
        Optional ``random.Random`` instance injected for deterministic tests.
    """
    word = _words.select_word(difficulty=difficulty, rng=rng).upper()
    water = _words.water_for(difficulty=difficulty)
    return GameState(
        secret_word=word,
        guessed_letters=set(),
        remaining_water=water,
        weed_count=0,
        max_water=water,
    )


# ---------------------------------------------------------------------------
# Display helper
# ---------------------------------------------------------------------------

def display_word(state: GameState) -> str:
    """Return the secret word with unguessed letters masked as '_'.

    Letters are space-separated: ``G _ R _ E _``.
    """
    return " ".join(
        letter if letter in state.guessed_letters else "_"
        for letter in state.secret_word
    )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_guess(input_text: str) -> tuple[str | None, str]:
    """Validate raw user input (does NOT consult game state).

    Returns
    -------
    (letter, "")
        When *input_text* represents exactly one alphabetic character
        (trimmed and uppercased).
    (None, message)
        When input is invalid, with a specific, helpful message.
    """
    stripped = input_text.strip()
    if len(stripped) == 0:
        return None, MSG_INVALID_EMPTY
    if len(stripped) > 1:
        return None, MSG_INVALID_MULTIPLE
    if not stripped.isalpha():
        return None, MSG_INVALID_NOT_ALPHA
    return stripped.upper(), ""


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------

def is_won(state: GameState) -> bool:
    """Return True when every letter of the secret word has been guessed."""
    return all(letter in state.guessed_letters for letter in state.secret_word)


def is_lost(state: GameState) -> bool:
    """Return True when water has reached zero and the game has not been won."""
    return state.remaining_water <= 0 and not is_won(state)


# ---------------------------------------------------------------------------
# State transition
# ---------------------------------------------------------------------------

def apply_guess(state: GameState, letter: str) -> GameState:
    """Apply a single already-validated uppercase letter to *state*.

    This function never mutates *state*; it returns a new GameState.

    Rules (SPEC.md sections 6.3–6.5):
    - If game is already over: no-op with a message.
    - Repeated guess: no resource changes, message notes the repeat.
    - Correct guess: letter added to guessed set; win checked.
    - Wrong guess: water −1, weeds +1, letter added; loss checked.
    """
    if state.game_over:
        return GameState(
            secret_word=state.secret_word,
            guessed_letters=state.guessed_letters,
            remaining_water=state.remaining_water,
            weed_count=state.weed_count,
            max_water=state.max_water,
            status_message=MSG_GAME_OVER_ALREADY,
            game_over=True,
            won=state.won,
        )

    # --- Repeated guess ------------------------------------------------
    if letter in state.guessed_letters:
        return GameState(
            secret_word=state.secret_word,
            guessed_letters=state.guessed_letters,
            remaining_water=state.remaining_water,
            weed_count=state.weed_count,
            max_water=state.max_water,
            status_message=MSG_ALREADY_GUESSED_TEMPLATE.format(letter=letter),
            game_over=False,
            won=False,
        )

    # --- Apply the new guess -------------------------------------------
    new_guessed = state.guessed_letters | {letter}

    if letter in state.secret_word:
        # Correct guess — no resource change
        new_water = state.remaining_water
        new_weeds = state.weed_count
        turn_message = MSG_CORRECT_GUESS
    else:
        # Wrong guess — costs water, grows weeds
        new_water = state.remaining_water - 1
        new_weeds = state.weed_count + 1
        turn_message = MSG_WRONG_GUESS

    # Build a provisional state so the predicates can inspect it
    provisional = GameState(
        secret_word=state.secret_word,
        guessed_letters=new_guessed,
        remaining_water=new_water,
        weed_count=new_weeds,
        max_water=state.max_water,
        status_message=turn_message,
        game_over=False,
        won=False,
    )

    # --- Check terminal conditions -------------------------------------
    if is_won(provisional):
        # Win: overwrite the turn message with the end-of-game message
        return GameState(
            secret_word=provisional.secret_word,
            guessed_letters=provisional.guessed_letters,
            remaining_water=provisional.remaining_water,
            weed_count=provisional.weed_count,
            max_water=provisional.max_water,
            status_message=MSG_WIN_TITLE,
            game_over=True,
            won=True,
        )

    if is_lost(provisional):
        # Loss: overwrite the turn message with the end-of-game message
        return GameState(
            secret_word=provisional.secret_word,
            guessed_letters=provisional.guessed_letters,
            remaining_water=provisional.remaining_water,
            weed_count=provisional.weed_count,
            max_water=provisional.max_water,
            status_message=MSG_LOSS_TITLE,
            game_over=True,
            won=False,
        )

    return provisional
