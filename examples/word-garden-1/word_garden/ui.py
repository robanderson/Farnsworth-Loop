"""Word Garden terminal rendering — pure output, zero I/O.

All public functions accept a GameState and return a string. Nothing in this
module calls print() or input(). See SPEC.md sections 9, 10, 15, 18, 20.
"""

from __future__ import annotations

from .game import GameState, display_word

# ---------------------------------------------------------------------------
# Growth-stage glyphs (SPEC.md section 10)
# ---------------------------------------------------------------------------

_STAGES_EMOJI = {
    "start":    "🌱",
    "progress": "🌿",
    "near_win": "🌷",
    "win":      "🌻",
    "loss":     "🥀",
}

_STAGES_ASCII = {
    "start":    "[.]",
    "progress": "[*]",
    "near_win": "[+]",
    "win":      "[#]",
    "loss":     "[x]",
}

# Title glyphs
_TITLE_EMOJI = "🌱 Word Garden"
_TITLE_ASCII = "Word Garden"


def _growth_stage(state: GameState) -> str:
    """Return the stage key based on game progress (win/loss/near-win/etc)."""
    if state.won:
        return "win"
    if state.game_over:
        return "loss"
    total_letters = len(set(state.secret_word))
    guessed_correct = len(set(state.secret_word) & state.guessed_letters)
    if total_letters == 0:
        return "start"
    ratio = guessed_correct / total_letters
    if ratio >= 0.75:
        return "near_win"
    if ratio > 0:
        return "progress"
    return "start"


def render(state: GameState, ascii_mode: bool = False) -> str:
    """Return the full turn display string (SPEC.md section 9).

    Order: title, plant stage, masked word, guessed letters, water, weeds,
    previous status message.  Water and weeds always carry a text label AND a
    count for accessibility (SPEC.md section 18).

    No I/O — caller is responsible for printing.
    """
    stage_key = _growth_stage(state)

    if ascii_mode:
        stage_glyph = _STAGES_ASCII[stage_key]
        title = _TITLE_ASCII
        water_sym = "~"
        weed_sym = "-"
    else:
        stage_glyph = _STAGES_EMOJI[stage_key]
        title = _TITLE_EMOJI
        water_sym = "\U0001f4a7"   # 💧
        weed_sym = "\U0001f33f"    # 🌿

    word_line = display_word(state)
    guessed_sorted = " ".join(sorted(state.guessed_letters))

    # Accessibility: label + fraction + symbols (SPEC.md section 18)
    water_count = state.remaining_water
    water_max = state.max_water
    water_symbols = water_sym * water_count
    water_line = f"Water:  {water_count}/{water_max} {water_symbols}"

    weed_count = state.weed_count
    weed_symbols = weed_sym * weed_count
    weed_line = f"Weeds:  {weed_count} {weed_symbols}"

    lines = [
        title,
        "",
        f"{stage_glyph}",
        "",
        f"Word:     {word_line}",
        f"Guessed:  {guessed_sorted}",
        water_line,
        weed_line,
    ]

    if state.status_message:
        lines.append("")
        lines.append(state.status_message)

    return "\n".join(lines)


def win_screen(state: GameState, ascii_mode: bool = False) -> str:
    """Return the win screen string (SPEC.md section 6.6)."""
    if ascii_mode:
        glyph = _STAGES_ASCII["win"]
        header = f"{glyph} Bloom!"
    else:
        glyph = _STAGES_EMOJI["win"]
        header = f"{glyph} Bloom!"

    lines = [
        header,
        "",
        f"You guessed the word: {state.secret_word}",
        "The garden is thriving.",
    ]
    return "\n".join(lines)


def loss_screen(state: GameState, ascii_mode: bool = False) -> str:
    """Return the loss screen string (SPEC.md section 6.7)."""
    if ascii_mode:
        glyph = _STAGES_ASCII["loss"]
        header = f"{glyph} The garden ran out of water."
    else:
        glyph = _STAGES_EMOJI["loss"]
        header = f"{glyph} The garden ran out of water."

    lines = [
        header,
        "",
        f"The word was: {state.secret_word}",
        "Try again and grow a new garden.",
    ]
    return "\n".join(lines)
