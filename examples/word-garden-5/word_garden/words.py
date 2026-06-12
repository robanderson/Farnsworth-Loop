"""Word list and word selection for Word Garden."""

import random as _random

# ---------------------------------------------------------------------------
# Word list (SPEC.md section 8)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Difficulty table (SPEC.md section 7)
# ---------------------------------------------------------------------------

_DIFFICULTY: dict[str, dict] = {
    "easy":   {"water": 8, "min_len": 4, "max_len": 6},
    "normal": {"water": 6, "min_len": 5, "max_len": 8},
    "hard":   {"water": 4, "min_len": 7, "max_len": None},
}


def water_for(difficulty: str = "normal") -> int:
    """Return the starting water level for a given difficulty.

    Raises ValueError for unknown difficulty strings.
    """
    if difficulty not in _DIFFICULTY:
        raise ValueError(
            f"Unknown difficulty {difficulty!r}. "
            f"Choose one of: {', '.join(_DIFFICULTY)}"
        )
    return _DIFFICULTY[difficulty]["water"]


def select_word(difficulty: str = "normal", rng: _random.Random | None = None) -> str:
    """Return a random word filtered by *difficulty*.

    Parameters
    ----------
    difficulty:
        "easy", "normal", or "hard" — see SPEC.md section 7 for the table.
    rng:
        An optional ``random.Random`` instance for deterministic tests.
        When *None* the module-level ``random`` functions are used.

    Raises
    ------
    ValueError
        When *difficulty* is unknown or no words match the filter.
    """
    if difficulty not in _DIFFICULTY:
        raise ValueError(
            f"Unknown difficulty {difficulty!r}. "
            f"Choose one of: {', '.join(_DIFFICULTY)}"
        )

    cfg = _DIFFICULTY[difficulty]
    min_len: int = cfg["min_len"]
    max_len: int | None = cfg["max_len"]

    pool = [
        w for w in WORDS
        if len(w) >= min_len and (max_len is None or len(w) <= max_len)
    ]

    if not pool:
        raise ValueError(
            f"No words match difficulty {difficulty!r} "
            f"(min_len={min_len}, max_len={max_len})."
        )

    if rng is not None:
        return rng.choice(pool)
    return _random.choice(pool)
