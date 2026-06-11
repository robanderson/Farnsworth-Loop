"""Word Garden — a friendly terminal word-guessing game.

This package contains the pure game logic (no UI). See SPEC.md for details.
"""

from .game import (
    GameState,
    apply_guess,
    display_word,
    is_lost,
    is_won,
    new_game,
    validate_guess,
)
from .words import WORDS, select_word, water_for

__all__ = [
    "GameState",
    "apply_guess",
    "display_word",
    "is_lost",
    "is_won",
    "new_game",
    "validate_guess",
    "WORDS",
    "select_word",
    "water_for",
]
