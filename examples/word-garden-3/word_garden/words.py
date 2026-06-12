"""Word list and selection logic for Word Garden."""

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
# Difficulty parameters (SPEC.md section 7)
# ---------------------------------------------------------------------------

_DIFFICULTY_PARAMS: dict[str, dict] = {
    "easy":   {"water": 8, "min_len": 4, "max_len": 6},
    "normal": {"water": 6, "min_len": 5, "max_len": 8},
    "hard":   {"water": 4, "min_len": 7, "max_len": None},  # 7+
}

# ---------------------------------------------------------------------------
# User-facing message constants
# ---------------------------------------------------------------------------

MSG_UNKNOWN_DIFFICULTY = "Unknown difficulty {!r}. Choose from: easy, normal, hard."
MSG_EMPTY_POOL = (
    "No words match difficulty {!r} (min_len={}, max_len={}). "
    "Check WORDS list."
)


def water_for(difficulty: str = "normal") -> int:
    """Return starting water count for a given difficulty.

    Raises ValueError for unknown difficulty.
    """
    if difficulty not in _DIFFICULTY_PARAMS:
        raise ValueError(MSG_UNKNOWN_DIFFICULTY.format(difficulty))
    return _DIFFICULTY_PARAMS[difficulty]["water"]


def select_word(difficulty: str = "normal", rng: "_random.Random | None" = None) -> str:
    """Return a random word filtered by difficulty.

    Parameters
    ----------
    difficulty:
        One of "easy", "normal", "hard".
    rng:
        An injectable ``random.Random`` instance for deterministic tests.
        When *None* (default) the module-level ``random`` functions are used —
        never a freshly seeded ``Random``, which would be deterministic.

    Raises
    ------
    ValueError
        If *difficulty* is unknown or no words match the filter.
    """
    if difficulty not in _DIFFICULTY_PARAMS:
        raise ValueError(MSG_UNKNOWN_DIFFICULTY.format(difficulty))

    params = _DIFFICULTY_PARAMS[difficulty]
    min_len: int = params["min_len"]
    max_len: int | None = params["max_len"]

    pool = [
        w for w in WORDS
        if len(w) >= min_len and (max_len is None or len(w) <= max_len)
    ]

    if not pool:
        raise ValueError(MSG_EMPTY_POOL.format(difficulty, min_len, max_len))

    if rng is not None:
        return rng.choice(pool)
    return _random.choice(pool)
