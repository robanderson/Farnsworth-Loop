"""Pure rendering for Word Garden (SPEC.md sections 5, 9, 10, 18).

This module is **pure**: every function returns a string and performs no I/O
(no ``input`` / ``print``). All terminal interaction lives in
:mod:`word_garden.main`.

Two visual modes are supported:

- emoji mode (default) uses the SPEC.md section 10 glyphs;
- ``ascii_mode=True`` uses a plain-ASCII fallback whose output is guaranteed to
  contain no non-ASCII characters (SPEC.md sections 10 and 18).

Water and weeds always carry a text label *and* a numeric count alongside any
symbols, so the display never relies on symbols alone (SPEC.md section 18).
"""

from __future__ import annotations

from word_garden import game
from word_garden.game import GameState

TITLE_EMOJI = "\U0001F331 Word Garden"  # seedling + title
TITLE_ASCII = "Word Garden"

# Growth-stage glyphs (SPEC.md section 10 table).
_STAGE_EMOJI = {
    "start": "\U0001F331",      # seedling
    "progress": "\U0001F33F",   # herb / sprouting plant
    "near-win": "\U0001F337",   # tulip
    "win": "\U0001F33B",        # sunflower
    "loss": "\U0001F940",       # wilted flower
}
_STAGE_ASCII = {
    "start": ".",
    "progress": "i",
    "near-win": "Y",
    "win": "*",
    "loss": "x",
}

# Friendly one-line caption for each stage.
_STAGE_LABEL = {
    "start": "A fresh seed is planted.",
    "progress": "Your garden is growing.",
    "near-win": "Almost in full bloom!",
    "win": "In glorious bloom!",
    "loss": "The garden has wilted.",
}

# Symbols for the water / weed meters.
_WATER_EMOJI = "\U0001F4A7"  # droplet
_WEED_EMOJI = "\U0001F33F"   # herb
_WATER_ASCII = "*"
_WEED_ASCII = "-"


def growth_stage(state: GameState) -> str:
    """Return the garden growth stage key for ``state`` (SPEC.md section 10).

    The result is one of ``"start"``, ``"progress"``, ``"near-win"``,
    ``"win"`` or ``"loss"``. Win/loss take priority; otherwise the stage is
    driven by how much of the word has been revealed.
    """
    if state.won or game.is_won(state):
        return "win"
    if state.game_over or game.is_lost(state):
        return "loss"

    total = len(state.secret_word)
    if total == 0:
        return "start"
    revealed = sum(
        1 for letter in state.secret_word if letter in state.guessed_letters
    )
    progress = revealed / total
    if revealed == 0:
        return "start"
    if progress >= 0.75:
        return "near-win"
    return "progress"


def _stage_glyph(stage: str, ascii_mode: bool) -> str:
    table = _STAGE_ASCII if ascii_mode else _STAGE_EMOJI
    return table[stage]


def _meter(count: int, symbol: str) -> str:
    """Return ``symbol`` repeated ``count`` times (never negative)."""
    return symbol * max(count, 0)


def _water_line(state: GameState, ascii_mode: bool) -> str:
    symbol = _WATER_ASCII if ascii_mode else _WATER_EMOJI
    symbols = _meter(state.remaining_water, symbol)
    count = f"{state.remaining_water}/{state.max_water}"
    return f"Water:  {count} {symbols}".rstrip()


def _weeds_line(state: GameState, ascii_mode: bool) -> str:
    symbol = _WEED_ASCII if ascii_mode else _WEED_EMOJI
    symbols = _meter(state.weed_count, symbol)
    count = str(state.weed_count)
    return f"Weeds:  {count} {symbols}".rstrip()


def _guessed_line(state: GameState) -> str:
    letters = " ".join(sorted(state.guessed_letters))
    return f"Guessed: {letters}".rstrip()


def render(state: GameState, ascii_mode: bool = False) -> str:
    """Render the full turn display for ``state`` (SPEC.md sections 9, 18).

    Order: title, plant/garden status, masked word, guessed letters, water,
    weeds, and the previous turn's ``status_message`` (when present). Pass
    ``ascii_mode=True`` for the plain-ASCII fallback.
    """
    title = TITLE_ASCII if ascii_mode else TITLE_EMOJI
    stage = growth_stage(state)
    glyph = _stage_glyph(stage, ascii_mode)
    plant_line = f"Plant:  {glyph} {_STAGE_LABEL[stage]}"

    lines = [
        title,
        "",
        plant_line,
        "",
        f"Word:    {game.display_word(state)}",
        _guessed_line(state),
        _water_line(state, ascii_mode),
        _weeds_line(state, ascii_mode),
    ]

    if state.status_message:
        lines.append("")
        lines.append(state.status_message)

    return "\n".join(lines)


def win_screen(state: GameState, ascii_mode: bool = False) -> str:
    """Render the victory screen (SPEC.md section 6.6)."""
    header_glyph = _stage_glyph("win", ascii_mode)
    header = f"{header_glyph} Bloom!"
    return "\n".join(
        [
            header,
            "",
            f"You guessed the word: {state.secret_word}",
            "The garden is thriving.",
        ]
    )


def loss_screen(state: GameState, ascii_mode: bool = False) -> str:
    """Render the defeat screen, revealing the word (SPEC.md section 6.7)."""
    header_glyph = _stage_glyph("loss", ascii_mode)
    header = f"{header_glyph} The garden ran out of water."
    return "\n".join(
        [
            header,
            "",
            f"The word was: {state.secret_word}",
            "Try again and grow a new garden.",
        ]
    )
