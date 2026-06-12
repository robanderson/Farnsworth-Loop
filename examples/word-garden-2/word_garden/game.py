"""Core game state and rules for Word Garden.

Pure logic: stdlib only, no I/O (no ``input``/``print``). The UI (task-002)
is built on top of this module. See SPEC.md sections 6, 12, 13 and 14.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from word_garden import words

# Friendly, non-violent messages (SPEC.md section 6).
MSG_CORRECT = "Good guess! The garden grows."
MSG_WRONG = "No match. A weed appears."
MSG_WIN = "Bloom! The garden is thriving."
MSG_LOSS = "The garden ran out of water."
MSG_GAME_OVER = "The game is over. Start a new garden to play again."


@dataclass
class GameState:
    """The full state of one Word Garden session (SPEC.md section 12)."""

    secret_word: str
    guessed_letters: set[str]
    remaining_water: int
    weed_count: int
    max_water: int
    status_message: str = ""
    game_over: bool = False
    won: bool = False


def new_game(
    difficulty: str = "normal", rng: random.Random | None = None
) -> GameState:
    """Create a fresh :class:`GameState` for ``difficulty`` (SPEC.md 6.1).

    Picks a word via :func:`word_garden.words.select_word`, stores it
    uppercase, starts with full water and zero weeds. ``rng`` is forwarded to
    the word selector for deterministic tests. Raises ``ValueError`` for an
    unknown difficulty.
    """
    water = words.water_for(difficulty)
    secret_word = words.select_word(difficulty, rng=rng).upper()
    return GameState(
        secret_word=secret_word,
        guessed_letters=set(),
        remaining_water=water,
        weed_count=0,
        max_water=water,
    )


def validate_guess(input_text: str) -> tuple[str | None, str]:
    """Validate raw guess input (SPEC.md sections 6.2 and 14).

    Returns ``(letter, "")`` for valid input — trimmed, uppercased, exactly
    one alphabetic character — or ``(None, message)`` with a specific, helpful
    message. Validation does NOT consult game state; repeated-guess detection
    belongs to :func:`apply_guess`.
    """
    text = (input_text or "").strip()
    if text == "":
        return None, "Please enter a single letter."
    if len(text) != 1:
        return None, "Please enter a single letter."
    if not text.isalpha():
        return None, "That is not a letter."
    return text.upper(), ""


def apply_guess(state: GameState, letter: str) -> GameState:
    """Apply one already-validated uppercase ``letter`` (SPEC.md 6.3–6.5).

    Correct guess reveals matching positions (no water/weed change); wrong
    guess costs 1 water and adds 1 weed; a repeated guess changes nothing but
    the message. Updates ``status_message`` and sets ``game_over``/``won``
    when the guess ends the game. Guessing after ``game_over`` is a no-op with
    a message. Mutates and returns ``state``.
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
        state.status_message = MSG_CORRECT
        if is_won(state):
            state.won = True
            state.game_over = True
            state.status_message = MSG_WIN
    else:
        state.remaining_water -= 1
        state.weed_count += 1
        state.status_message = MSG_WRONG
        if is_lost(state):
            state.won = False
            state.game_over = True
            state.status_message = MSG_LOSS

    return state


def display_word(state: GameState) -> str:
    """Return the masked word, space-separated (e.g. ``G _ R _ E _``)."""
    return " ".join(
        letter if letter in state.guessed_letters else "_"
        for letter in state.secret_word
    )


def is_won(state: GameState) -> bool:
    """Return ``True`` when every letter of the secret word is guessed."""
    return all(letter in state.guessed_letters for letter in state.secret_word)


def is_lost(state: GameState) -> bool:
    """Return ``True`` when water has run out before the word is revealed."""
    return state.remaining_water <= 0 and not is_won(state)
