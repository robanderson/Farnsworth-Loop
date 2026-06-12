"""Word list and difficulty-aware word selection for Word Garden.

Pure logic: stdlib only, no I/O. See SPEC.md sections 7 and 8.
"""

from __future__ import annotations

import random

# The built-in word list (SPEC.md section 8), stored uppercase.
# Easy to replace or extend.
WORDS: list[str] = [
    "GARDEN",
    "FLOWER",
    "PLANET",
    "PYTHON",
    "TERMINAL",
    "MEADOW",
    "ORCHARD",
    "VINEYARD",
    "SEEDLING",
    "HARVEST",
]

# Difficulty table (SPEC.md section 7): starting water and word-length bounds.
# ``max_length`` of ``None`` means "no upper bound".
_DIFFICULTY = {
    "easy": {"water": 8, "min_length": 4, "max_length": 6},
    "normal": {"water": 6, "min_length": 5, "max_length": 8},
    "hard": {"water": 4, "min_length": 7, "max_length": None},
}


def _difficulty_config(difficulty: str) -> dict:
    """Return the config row for ``difficulty`` or raise ``ValueError``."""
    try:
        return _DIFFICULTY[difficulty]
    except KeyError:
        valid = ", ".join(sorted(_DIFFICULTY))
        raise ValueError(
            f"Unknown difficulty {difficulty!r}; expected one of: {valid}."
        ) from None


def water_for(difficulty: str = "normal") -> int:
    """Return the starting water for ``difficulty`` (SPEC.md section 7).

    Raises ``ValueError`` for an unknown difficulty.
    """
    return _difficulty_config(difficulty)["water"]


def _words_for(difficulty: str) -> list[str]:
    """Return the words from :data:`WORDS` that fit ``difficulty``'s length."""
    config = _difficulty_config(difficulty)
    min_length = config["min_length"]
    max_length = config["max_length"]
    return [
        word
        for word in WORDS
        if len(word) >= min_length
        and (max_length is None or len(word) <= max_length)
    ]


def select_word(
    difficulty: str = "normal", rng: random.Random | None = None
) -> str:
    """Return a random word matching ``difficulty`` (SPEC.md section 7).

    ``rng`` is an injectable :class:`random.Random` instance for deterministic
    tests; when ``None`` the module-level :mod:`random` functions are used.

    Raises ``ValueError`` for an unknown difficulty or if no word in
    :data:`WORDS` matches the difficulty's length constraints.
    """
    candidates = _words_for(difficulty)
    if not candidates:
        raise ValueError(
            f"No words available for difficulty {difficulty!r}."
        )
    choice = random.choice if rng is None else rng.choice
    return choice(candidates).upper()
