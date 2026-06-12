"""Word list and difficulty-aware word selection for Word Garden.

Pure logic only: stdlib imports, no I/O. See SPEC.md sections 7 and 8.
"""

from __future__ import annotations

import random

# The built-in word list (SPEC.md section 8), uppercase.
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

# Difficulty table (SPEC.md section 7): water and word-length bounds.
# Bounds are inclusive; ``None`` means "no upper bound".
_DIFFICULTY = {
    "easy": {"water": 8, "min_len": 4, "max_len": 6},
    "normal": {"water": 6, "min_len": 5, "max_len": 8},
    "hard": {"water": 4, "min_len": 7, "max_len": None},
}


def _config(difficulty: str) -> dict:
    """Return the difficulty config or raise ValueError for unknown values."""
    try:
        return _DIFFICULTY[difficulty]
    except KeyError:
        valid = ", ".join(sorted(_DIFFICULTY))
        raise ValueError(
            f"Unknown difficulty {difficulty!r}. Choose one of: {valid}."
        ) from None


def water_for(difficulty: str = "normal") -> int:
    """Return the starting water for ``difficulty`` (SPEC.md section 7)."""
    return _config(difficulty)["water"]


def _candidates(difficulty: str) -> list[str]:
    """Return all WORDS matching the length filter for ``difficulty``."""
    cfg = _config(difficulty)
    min_len = cfg["min_len"]
    max_len = cfg["max_len"]
    return [
        word
        for word in WORDS
        if len(word) >= min_len and (max_len is None or len(word) <= max_len)
    ]


def select_word(
    difficulty: str = "normal", rng: random.Random | None = None
) -> str:
    """Return a random uppercase word matching ``difficulty``.

    ``rng`` is an injectable ``random.Random`` for deterministic tests; when
    ``None`` the module-level ``random`` functions are used. Unknown difficulty
    raises ``ValueError`` (via ``_config``).
    """
    candidates = _candidates(difficulty)
    if not candidates:
        # Defensive: should not happen with the shipped WORDS list.
        raise ValueError(
            f"No words available for difficulty {difficulty!r}."
        )
    chooser = rng.choice if rng is not None else random.choice
    return chooser(candidates).upper()
