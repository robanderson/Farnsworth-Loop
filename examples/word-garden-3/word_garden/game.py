"""Core game logic for Word Garden (no I/O)."""

from __future__ import annotations

import random as _random_mod
from dataclasses import dataclass

from word_garden import words as _words

# ---------------------------------------------------------------------------
# User-facing message constants (SPEC.md sections 6.3–6.7, 14)
# ---------------------------------------------------------------------------

MSG_CORRECT_GUESS = "Good guess! The garden grows."
MSG_WRONG_GUESS = "No match. A weed appears."
MSG_ALREADY_GUESSED = "You already guessed {letter}. Try another letter."
MSG_GAME_OVER_ALREADY = "The game is already over."

MSG_WIN = "Bloom! You guessed the word: {word}. The garden is thriving."
MSG_LOSS = "The garden ran out of water. The word was: {word}. Try again and grow a new garden."

# Validation messages (SPEC.md section 14)
MSG_EMPTY_INPUT = "Please enter a single letter."
MSG_MULTIPLE_CHARS = "Please enter a single letter."
MSG_NOT_A_LETTER = "That is not a letter."


# ---------------------------------------------------------------------------
# GameState dataclass (SPEC.md section 12)
# ---------------------------------------------------------------------------

@dataclass
class GameState:
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

def new_game(difficulty: str = "normal", rng: _random_mod.Random | None = None) -> GameState:
    """Create a fresh GameState for a new game.

    Parameters
    ----------
    difficulty:
        One of "easy", "normal", "hard".
    rng:
        Injectable ``random.Random`` instance; *None* uses module-level random.

    Raises
    ------
    ValueError
        Propagated from ``words.select_word`` / ``words.water_for`` on bad
        difficulty or empty pool.
    """
    word = _words.select_word(difficulty=difficulty, rng=rng)
    water = _words.water_for(difficulty=difficulty)
    return GameState(
        secret_word=word.upper(),
        guessed_letters=set(),
        remaining_water=water,
        weed_count=0,
        max_water=water,
    )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_guess(input_text: str) -> tuple[str | None, str]:
    """Validate raw player input.

    Does NOT consult game state (repeated-guess detection is in
    ``apply_guess``).

    Returns
    -------
    (letter, "")
        When *input_text* represents a single alphabetic character after
        stripping and uppercasing.
    (None, message)
        When input is invalid, with a specific helpful message.
    """
    stripped = input_text.strip()
    if not stripped:
        return None, MSG_EMPTY_INPUT
    if len(stripped) > 1:
        return None, MSG_MULTIPLE_CHARS
    if not stripped.isalpha():
        return None, MSG_NOT_A_LETTER
    return stripped.upper(), ""


# ---------------------------------------------------------------------------
# Apply guess
# ---------------------------------------------------------------------------

def apply_guess(state: GameState, letter: str) -> GameState:
    """Apply an already-validated, uppercased letter to *state*.

    Returns a *new* ``GameState`` — the original is never mutated.

    Handles (SPEC.md sections 6.3–6.5):
    - Correct guess: reveals letters, positive message.
    - Wrong guess: water -1, weeds +1, gentle message.
    - Repeated guess: no state change except message.
    - Post-game no-op: returns state with "already over" message.
    """
    # No-op after game over
    if state.game_over:
        return GameState(
            secret_word=state.secret_word,
            guessed_letters=set(state.guessed_letters),
            remaining_water=state.remaining_water,
            weed_count=state.weed_count,
            max_water=state.max_water,
            status_message=MSG_GAME_OVER_ALREADY,
            game_over=state.game_over,
            won=state.won,
        )

    # Repeated guess (SPEC.md 6.5)
    if letter in state.guessed_letters:
        return GameState(
            secret_word=state.secret_word,
            guessed_letters=set(state.guessed_letters),
            remaining_water=state.remaining_water,
            weed_count=state.weed_count,
            max_water=state.max_water,
            status_message=MSG_ALREADY_GUESSED.format(letter=letter),
            game_over=False,
            won=False,
        )

    new_guessed = set(state.guessed_letters) | {letter}

    if letter in state.secret_word:
        # Correct guess (SPEC.md 6.3)
        new_water = state.remaining_water
        new_weeds = state.weed_count
        # Check win condition
        if all(ch in new_guessed for ch in state.secret_word):
            return GameState(
                secret_word=state.secret_word,
                guessed_letters=new_guessed,
                remaining_water=new_water,
                weed_count=new_weeds,
                max_water=state.max_water,
                status_message=MSG_WIN.format(word=state.secret_word),
                game_over=True,
                won=True,
            )
        return GameState(
            secret_word=state.secret_word,
            guessed_letters=new_guessed,
            remaining_water=new_water,
            weed_count=new_weeds,
            max_water=state.max_water,
            status_message=MSG_CORRECT_GUESS,
            game_over=False,
            won=False,
        )
    else:
        # Wrong guess (SPEC.md 6.4)
        new_water = state.remaining_water - 1
        new_weeds = state.weed_count + 1
        # Check loss condition
        if new_water <= 0:
            return GameState(
                secret_word=state.secret_word,
                guessed_letters=new_guessed,
                remaining_water=new_water,
                weed_count=new_weeds,
                max_water=state.max_water,
                status_message=MSG_LOSS.format(word=state.secret_word),
                game_over=True,
                won=False,
            )
        return GameState(
            secret_word=state.secret_word,
            guessed_letters=new_guessed,
            remaining_water=new_water,
            weed_count=new_weeds,
            max_water=state.max_water,
            status_message=MSG_WRONG_GUESS,
            game_over=False,
            won=False,
        )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_word(state: GameState) -> str:
    """Return the masked word string, e.g. ``G _ R _ E _``."""
    return " ".join(
        ch if ch in state.guessed_letters else "_"
        for ch in state.secret_word
    )


def is_won(state: GameState) -> bool:
    """True when all letters of secret_word have been guessed."""
    return all(ch in state.guessed_letters for ch in state.secret_word)


def is_lost(state: GameState) -> bool:
    """True when water has reached zero (before a win)."""
    return state.remaining_water <= 0 and not is_won(state)
