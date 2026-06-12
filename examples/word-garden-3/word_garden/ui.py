"""Pure rendering for Word Garden (no I/O).

Every function in this module takes a :class:`~word_garden.game.GameState`
and returns a string. Nothing here reads stdin or writes stdout — all
terminal interaction lives in :mod:`word_garden.main`. This keeps rendering
trivially testable: feed a pinned state, assert on the returned text.

Two visual modes are supported:

* **Emoji mode** (default) uses the SPEC section 10 glyphs.
* **ASCII mode** (``ascii_mode=True``) uses the section 10 ASCII fallback and
  is guaranteed to contain no non-ASCII characters anywhere in its output.

Accessibility (SPEC section 18): water and weeds always carry a text label
AND a numeric count, never bare symbols.
"""

from __future__ import annotations

from word_garden import game
from word_garden.game import GameState

# ---------------------------------------------------------------------------
# Static, user-facing strings (single source of truth — import, don't retype)
# ---------------------------------------------------------------------------

TITLE = "Word Garden"
PROMPT = "Guess a letter: "

LABEL_WORD = "Word:"
LABEL_GUESSED = "Guessed:"
LABEL_WATER = "Water:"
LABEL_WEEDS = "Weeds:"

# Growth-stage glyphs (SPEC section 10 table).
STAGE_GLYPHS = {
    "start": "\N{SEEDLING}",            # 🌱
    "progress": "\N{HERB}",             # 🌿
    "near-win": "\N{TULIP}",            # 🌷
    "win": "\N{SUNFLOWER}",             # 🌻
    "loss": "\N{WILTED FLOWER}",        # 🥀
}

# ASCII fallback for each growth stage (SPEC section 10 + 6.6/6.7 sense).
STAGE_ASCII = {
    "start": "*",
    "progress": "*",
    "near-win": "*",
    "win": "*",
    "loss": "x",
}

# Win / loss screen headers (SPEC 6.6 / 6.7).
WIN_HEADER = "Bloom!"
LOSS_HEADER = "The garden ran out of water."

# Symbols for the water / weed gauges.
WATER_GLYPH = "\N{DROPLET}"            # 💧
WEED_GLYPH = "\N{HERB}"               # 🌿
WATER_ASCII = "*"
WEED_ASCII = "-"


# ---------------------------------------------------------------------------
# Growth stage
# ---------------------------------------------------------------------------

def growth_stage(state: GameState) -> str:
    """Classify the garden's growth into a SPEC section 10 stage.

    Terminal states win outright: a won game is ``"win"`` and a lost game is
    ``"loss"`` regardless of how many letters happen to be revealed. For
    in-progress games the stage is driven by *progress* — the fraction of
    distinct secret letters revealed:

    * nothing revealed yet -> ``"start"``
    * almost everything revealed -> ``"near-win"``
    * anything in between -> ``"progress"``
    """
    if state.won:
        return "win"
    if state.game_over and not state.won:
        return "loss"

    distinct = set(state.secret_word)
    revealed = distinct & state.guessed_letters
    if not revealed:
        return "start"
    if len(revealed) >= len(distinct) - 1:
        return "near-win"
    return "progress"


def _plant_glyph(state: GameState, ascii_mode: bool) -> str:
    stage = growth_stage(state)
    return STAGE_ASCII[stage] if ascii_mode else STAGE_GLYPHS[stage]


# ---------------------------------------------------------------------------
# Gauges (water / weeds) — always label + count + symbols
# ---------------------------------------------------------------------------

def _water_line(state: GameState, ascii_mode: bool) -> str:
    glyph = WATER_ASCII if ascii_mode else WATER_GLYPH
    symbols = glyph * max(state.remaining_water, 0)
    count = f"{state.remaining_water}/{state.max_water}"
    return f"{LABEL_WATER} {count} {symbols}".rstrip()


def _weeds_line(state: GameState, ascii_mode: bool) -> str:
    glyph = WEED_ASCII if ascii_mode else WEED_GLYPH
    symbols = glyph * max(state.weed_count, 0)
    count = str(state.weed_count)
    return f"{LABEL_WEEDS} {count} {symbols}".rstrip()


# ---------------------------------------------------------------------------
# Full turn display
# ---------------------------------------------------------------------------

def render(state: GameState, ascii_mode: bool = False) -> str:
    """Return the full turn display (SPEC section 9).

    Lines, in order: title (with plant glyph), masked word, guessed letters,
    water gauge, weeds gauge, and — when present — the previous turn's
    ``status_message``. The trailing prompt is added by :mod:`main`, not here.
    """
    plant = _plant_glyph(state, ascii_mode)
    guessed = " ".join(sorted(state.guessed_letters))

    lines = [
        f"{plant} {TITLE}",
        "",
        f"{LABEL_WORD}     {game.display_word(state)}",
        f"{LABEL_GUESSED}  {guessed}".rstrip(),
        _water_line(state, ascii_mode),
        _weeds_line(state, ascii_mode),
    ]
    if state.status_message:
        lines += ["", state.status_message]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Win / loss screens
# ---------------------------------------------------------------------------

def win_screen(state: GameState, ascii_mode: bool = False) -> str:
    """Return the victory screen (SPEC 6.6), revealing the solved word."""
    glyph = STAGE_ASCII["win"] if ascii_mode else STAGE_GLYPHS["win"]
    return "\n".join([
        f"{glyph} {WIN_HEADER}",
        "",
        f"You guessed the word: {state.secret_word}",
        "The garden is thriving.",
    ])


def loss_screen(state: GameState, ascii_mode: bool = False) -> str:
    """Return the defeat screen (SPEC 6.7), revealing the secret word."""
    glyph = STAGE_ASCII["loss"] if ascii_mode else STAGE_GLYPHS["loss"]
    return "\n".join([
        f"{glyph} {LOSS_HEADER}",
        "",
        f"The word was: {state.secret_word}",
        "Try again and grow a new garden.",
    ])
