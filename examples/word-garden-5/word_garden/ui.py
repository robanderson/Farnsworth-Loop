"""Terminal rendering for Word Garden.

All functions return strings — zero print() or input() here.
The caller (main.py) is responsible for all I/O.
"""

from __future__ import annotations

from word_garden.game import (
    GameState,
    MSG_WIN_TITLE,
    MSG_WIN_BODY_TEMPLATE,
    MSG_LOSS_TITLE,
    MSG_LOSS_BODY_TEMPLATE,
    display_word,
    is_won,
    is_lost,
)

# ---------------------------------------------------------------------------
# Emoji / ASCII symbol tables
# ---------------------------------------------------------------------------

_EMOJI = {
    "water_drop": "\U0001f4a7",   # 💧
    "weed":       "\U0001f33f",   # 🌿
    "stage_start":    "\U0001f331",  # 🌱
    "stage_progress": "\U0001f33f",  # 🌿
    "stage_near_win": "\U0001f337",  # 🌷
    "stage_win":      "\U0001f33b",  # 🌻
    "stage_loss":     "\U0001f940",  # 🥀
}

_ASCII = {
    "water_drop": "*",
    "weed":       "-",
    "stage_start":    "*",
    "stage_progress": "+",
    "stage_near_win": "^",
    "stage_win":      "@",
    "stage_loss":     "x",
}


def _sym(key: str, ascii_mode: bool) -> str:
    return _ASCII[key] if ascii_mode else _EMOJI[key]


# ---------------------------------------------------------------------------
# Growth-stage glyph
# ---------------------------------------------------------------------------

def _growth_glyph(state: GameState, ascii_mode: bool) -> str:
    """Return the single glyph that represents the current growth stage.

    Five distinct, observable stages (SPEC.md section 10):
      1. Loss    — the game is over and the player lost.
      2. Win     — the game is over and the player won.
      3. Near-win — ≥ 2/3 of the distinct secret letters have been revealed.
      4. Progress — any correct guess has been made (1 ≤ revealed < near-win).
      5. Start   — no letters revealed yet.
    """
    if is_lost(state):
        return _sym("stage_loss", ascii_mode)
    if is_won(state):
        return _sym("stage_win", ascii_mode)

    distinct_letters = set(state.secret_word)
    revealed = distinct_letters & state.guessed_letters
    fraction = len(revealed) / len(distinct_letters) if distinct_letters else 0.0

    if fraction >= 2 / 3:
        return _sym("stage_near_win", ascii_mode)
    if fraction > 0:
        return _sym("stage_progress", ascii_mode)
    return _sym("stage_start", ascii_mode)


# ---------------------------------------------------------------------------
# Win / Loss screens
# ---------------------------------------------------------------------------

def _win_screen(state: GameState, ascii_mode: bool) -> str:
    title = MSG_WIN_TITLE if not ascii_mode else "Bloom!"
    body = MSG_WIN_BODY_TEMPLATE.format(word=state.secret_word)
    return f"{title}\n\n{body}"


def _loss_screen(state: GameState, ascii_mode: bool) -> str:
    title = MSG_LOSS_TITLE if not ascii_mode else "The garden ran out of water."
    body = MSG_LOSS_BODY_TEMPLATE.format(word=state.secret_word)
    return f"{title}\n\n{body}"


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render(state: GameState, ascii_mode: bool = False) -> str:
    """Return a complete render of *state* as a multi-line string.

    SPEC.md section 9 field order:
      1. Title with growth glyph
      2. Masked word
      3. Guessed letters (sorted, space-separated)
      4. Water line  — ``n/max`` + symbols
      5. Weeds line  — count + symbols
      6. Status message (omitted when empty)

    Win / loss screens replace the normal layout (SPEC sections 6.6–6.7).
    """
    glyph = _growth_glyph(state, ascii_mode)

    if state.game_over and state.won:
        return _win_screen(state, ascii_mode)

    if state.game_over and not state.won:
        return _loss_screen(state, ascii_mode)

    # --- Normal in-game render -----------------------------------------
    title = f"{glyph} Word Garden"

    word_line = f"Word:     {display_word(state)}"

    guessed_str = " ".join(sorted(state.guessed_letters)) if state.guessed_letters else ""
    guessed_line = f"Guessed:  {guessed_str}"

    water_sym = _sym("water_drop", ascii_mode)
    water_symbols = water_sym * state.remaining_water
    water_line = f"Water:    {state.remaining_water}/{state.max_water} {water_symbols}"

    weed_sym = _sym("weed", ascii_mode)
    weed_symbols = weed_sym * state.weed_count
    weed_line = f"Weeds:    {state.weed_count} {weed_symbols}"

    parts = [title, "", word_line, guessed_line, water_line, weed_line]

    if state.status_message:
        parts += ["", state.status_message]

    return "\n".join(parts)
