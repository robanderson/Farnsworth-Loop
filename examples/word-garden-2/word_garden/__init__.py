"""Word Garden — a friendly terminal word-guessing game.

This package contains the pure game engine (no UI):

- :mod:`word_garden.words` — the word list and difficulty-aware selection.
- :mod:`word_garden.game` — game state and the rules that drive it.
"""

from word_garden.game import (
    GameState,
    apply_guess,
    display_word,
    is_lost,
    is_won,
    new_game,
    validate_guess,
)
from word_garden.words import WORDS, select_word, water_for

__all__ = [
    "GameState",
    "new_game",
    "validate_guess",
    "apply_guess",
    "display_word",
    "is_won",
    "is_lost",
    "WORDS",
    "select_word",
    "water_for",
]
