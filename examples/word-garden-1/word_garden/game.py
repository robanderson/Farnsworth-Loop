"""Core Word Garden game logic.

Pure logic only: stdlib imports, no I/O (no input/print). The UI (task-002)
is built on top of this module. See SPEC.md sections 6, 12, 13, 14, 16.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import words

# Friendly status messages (SPEC.md sections 6.3-6.5, 14).
MSG_CORRECT = "Good guess! The garden grows."
MSG_WRONG = "No match. A weed appears."
MSG_WIN = "Bloom! The garden is thriving."
MSG_LOSS = "The garden ran out of water. Try again and grow a new garden."
MSG_GAME_OVER = "The game is over. Start a new garden to play again."

# Validation messages (SPEC.md section 14).
MSG_EMPTY = "Please enter a single letter."
MSG_TOO_LONG = "Please enter a single letter, not several."
MSG_NOT_LETTER = "That is not a letter. Please enter a letter from A to Z."


@dataclass
class GameState:
    """The full state of a single Word Garden game (SPEC.md section 12)."""

    secret_word: str
    guessed_letters: set[str] = field(default_factory=set)
    remaining_water: int = 0
    weed_count: int = 0
    max_water: int = 0
    status_message: str = ""
    game_over: bool = False
    won: bool = False


def new_game(
    difficulty: str = "normal", rng: random.Random | None = None
) -> GameState:
    """Create a fresh GameState (SPEC.md section 6.1).

    Picks a word via ``words.select_word``, uppercases it, sets full water for
    the difficulty, and starts with zero weeds and no guesses.
    """
    secret = words.select_word(difficulty, rng=rng).upper()
    water = words.water_for(difficulty)
    return GameState(
        secret_word=secret,
        guessed_letters=set(),
        remaining_water=water,
        weed_count=0,
        max_water=water,
        status_message="",
        game_over=False,
        won=False,
    )


def validate_guess(input_text: str) -> tuple[str | None, str]:
    """Validate raw guess input (SPEC.md sections 6.2, 14).

    Returns ``(letter, "")`` for valid input (trimmed, uppercased, exactly one
    alphabetic character) or ``(None, message)`` with a specific message.

    Validation does NOT consult game state; repeated-guess detection lives in
    ``apply_guess``.
    """
    text = "" if input_text is None else str(input_text)
    trimmed = text.strip()

    if trimmed == "":
        return None, MSG_EMPTY
    if len(trimmed) > 1:
        return None, MSG_TOO_LONG
    if not trimmed.isalpha():
        return None, MSG_NOT_LETTER
    return trimmed.upper(), ""


def apply_guess(state: GameState, letter: str) -> GameState:
    """Apply one already-validated uppercase letter (SPEC.md sections 6.3-6.5).

    Mutates and returns ``state``:
      - Correct guess: reveal (no water/weed change), positive message.
      - Wrong guess: water -1, weeds +1, gentle warning.
      - Repeated guess: nothing changes but the message.
      - After game over: no-op with a message.

    Updates ``game_over`` and ``won`` when the guess ends the game.
    """
    if state.game_over:
        state.status_message = MSG_GAME_OVER
        return state

    if letter in state.guessed_letters:
        state.status_message = (
            f"You already guessed {letter}. Try another letter."
        )
        return state

    state.guessed_letters.add(letter)

    if letter in state.secret_word:
        if is_won(state):
            state.won = True
            state.game_over = True
            state.status_message = MSG_WIN
        else:
            state.status_message = MSG_CORRECT
    else:
        state.remaining_water -= 1
        state.weed_count += 1
        if is_lost(state):
            state.won = False
            state.game_over = True
            state.status_message = MSG_LOSS
        else:
            state.status_message = MSG_WRONG

    return state


def display_word(state: GameState) -> str:
    """Return the masked secret word, space-separated (e.g. ``G _ R _ E _``)."""
    return " ".join(
        ch if ch in state.guessed_letters else "_"
        for ch in state.secret_word
    )


def is_won(state: GameState) -> bool:
    """True when every letter of the secret word has been guessed."""
    return all(ch in state.guessed_letters for ch in state.secret_word)


def is_lost(state: GameState) -> bool:
    """True when water is exhausted before the word is fully revealed."""
    return state.remaining_water <= 0 and not is_won(state)
