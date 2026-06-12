import random as _random

WORDS = [
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

# Difficulty table: (starting water, minimum word length, maximum word length or None)
_DIFFICULTY_CONFIG: dict[str, dict] = {
    "easy":   {"water": 8, "min_len": 4, "max_len": 6},
    "normal": {"water": 6, "min_len": 5, "max_len": 8},
    "hard":   {"water": 4, "min_len": 7, "max_len": None},
}


def water_for(difficulty: str = "normal") -> int:
    """Return the starting water level for the given difficulty."""
    if difficulty not in _DIFFICULTY_CONFIG:
        raise ValueError(f"Unknown difficulty: {difficulty!r}")
    return _DIFFICULTY_CONFIG[difficulty]["water"]


def select_word(difficulty: str = "normal", rng=None) -> str:
    """Return a random word matching the given difficulty's length constraints.

    Raises ValueError for an unknown difficulty or if no words match.
    Pass a seeded random.Random instance as rng for deterministic selection.
    """
    if difficulty not in _DIFFICULTY_CONFIG:
        raise ValueError(f"Unknown difficulty: {difficulty!r}")
    cfg = _DIFFICULTY_CONFIG[difficulty]
    pool = [
        w for w in WORDS
        if len(w) >= cfg["min_len"]
        and (cfg["max_len"] is None or len(w) <= cfg["max_len"])
    ]
    if not pool:
        raise ValueError(f"No words match difficulty {difficulty!r}")
    if rng is not None:
        return rng.choice(pool)
    return _random.choice(pool)
