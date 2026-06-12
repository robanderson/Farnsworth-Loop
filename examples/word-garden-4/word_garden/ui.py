"""Pure rendering for Word Garden.

Every function in this module returns a string. There is deliberately no
``print()``/``input()`` here — all I/O lives in :mod:`word_garden.main`.
Both an emoji display and a pure-ASCII fallback (SPEC §10, §18) are supported.
"""

from .game import GameState, display_word

# ---------------------------------------------------------------------------
# Growth-stage visuals (SPEC §10).
#
# Single source of truth: each stage maps to its emoji glyph, its ASCII
# fallback glyph (no non-ASCII characters), and a friendly text label. The
# render status line, the win screen, and the loss screen all read from here
# so the table is never duplicated.
# ---------------------------------------------------------------------------

STAGE_START = "start"
STAGE_PROGRESS = "progress"
STAGE_NEAR_WIN = "near_win"
STAGE_WIN = "win"
STAGE_LOSS = "loss"

GROWTH_STAGES: dict[str, dict[str, str]] = {
    STAGE_START:    {"emoji": "🌱", "ascii": "*",    "label": "A seedling sprouts."},
    STAGE_PROGRESS: {"emoji": "🌿", "ascii": "**",   "label": "The garden is growing."},
    STAGE_NEAR_WIN: {"emoji": "🌷", "ascii": "***",  "label": "Buds are about to bloom."},
    STAGE_WIN:      {"emoji": "🌻", "ascii": "\\o/",  "label": "Bloom!"},
    STAGE_LOSS:     {"emoji": "🥀", "ascii": "x_x",  "label": "Wilted."},
}

# Resource symbols (SPEC §10).
WATER_EMOJI = "💧"
WEED_EMOJI = "🌿"
WATER_ASCII = "*"
WEED_ASCII = "-"

# Layout: label column width shared by every row of the status block.
_LABEL_WIDTH = 9

# Title (SPEC §5/§9). The title always shows the seedling glyph; the dynamic
# growth stage is shown on its own "Garden:" line below.
TITLE_TEXT = "Word Garden"

# ---------------------------------------------------------------------------
# End-screen message strings (SPEC §6.6 win / §6.7 loss).
#
# These are screen-layout strings owned by the UI, distinct from the engine's
# one-line ``status_message`` constants. Defined once here; tests import them.
# ---------------------------------------------------------------------------

WIN_HEADER = "Bloom!"
WIN_REVEAL_TEMPLATE = "You guessed the word: {word}"
WIN_BODY = "The garden is thriving."

LOSS_HEADER = "The garden ran out of water."
LOSS_REVEAL_TEMPLATE = "The word was: {word}"
LOSS_BODY = "Try again and grow a new garden."


def growth_stage(state: GameState) -> str:
    """Return the growth-stage key for ``state`` (a key of GROWTH_STAGES).

    Driven by progress per SPEC §10: a terminal state is win or loss; before
    that it is start (nothing revealed), near-win (one secret letter left),
    or progress (something revealed but more than one letter remains).
    """
    if state.game_over and state.won:
        return STAGE_WIN
    if state.game_over:
        return STAGE_LOSS
    secret_letters = set(state.secret_word)
    revealed = secret_letters & state.guessed_letters
    if not revealed:
        return STAGE_START
    if len(secret_letters - state.guessed_letters) <= 1:
        return STAGE_NEAR_WIN
    return STAGE_PROGRESS


def _glyph(stage: str, ascii_mode: bool) -> str:
    return GROWTH_STAGES[stage]["ascii" if ascii_mode else "emoji"]


def _label(text: str, value: str) -> str:
    return f"{text:<{_LABEL_WIDTH}}{value}".rstrip()


def _water_line(state: GameState, ascii_mode: bool) -> str:
    """Water row with text label AND count AND symbols (SPEC §18)."""
    count = f"{state.remaining_water}/{state.max_water}"
    if ascii_mode:
        used = state.max_water - state.remaining_water
        symbols = "[" + WATER_ASCII * state.remaining_water + " " * used + "]"
    else:
        symbols = WATER_EMOJI * state.remaining_water
    return _label("Water:", f"{count} {symbols}")


def _weeds_line(state: GameState, ascii_mode: bool) -> str:
    """Weeds row with text label AND count AND symbols (SPEC §18)."""
    count = str(state.weed_count)
    if ascii_mode:
        symbols = "[" + WEED_ASCII * state.weed_count + "]"
    else:
        symbols = WEED_EMOJI * state.weed_count
    return _label("Weeds:", f"{count} {symbols}")


def render(state: GameState, ascii_mode: bool = False) -> str:
    """Return the full turn display (SPEC §9), as a string.

    Order: title, garden/plant status, masked word, guessed letters, water,
    weeds, then the previous turn's ``status_message`` (omitted when empty).
    """
    stage = growth_stage(state)
    if ascii_mode:
        title = TITLE_TEXT
    else:
        title = f"{GROWTH_STAGES[STAGE_START]['emoji']} {TITLE_TEXT}"

    garden_value = f"{_glyph(stage, ascii_mode)}  {GROWTH_STAGES[stage]['label']}"
    guessed = " ".join(sorted(state.guessed_letters))

    lines = [
        title,
        "",
        _label("Garden:", garden_value),
        _label("Word:", display_word(state)),
        _label("Guessed:", guessed),
        _water_line(state, ascii_mode),
        _weeds_line(state, ascii_mode),
    ]
    if state.status_message:
        lines.append("")
        lines.append(state.status_message)
    return "\n".join(lines)


def win_screen(state: GameState, ascii_mode: bool = False) -> str:
    """Return the winning end screen (SPEC §6.6); names the secret word."""
    lines = [
        f"{_glyph(STAGE_WIN, ascii_mode)} {WIN_HEADER}",
        "",
        WIN_REVEAL_TEMPLATE.format(word=state.secret_word),
        WIN_BODY,
    ]
    return "\n".join(lines)


def loss_screen(state: GameState, ascii_mode: bool = False) -> str:
    """Return the losing end screen (SPEC §6.7); reveals the secret word."""
    lines = [
        f"{_glyph(STAGE_LOSS, ascii_mode)} {LOSS_HEADER}",
        "",
        LOSS_REVEAL_TEMPLATE.format(word=state.secret_word),
        LOSS_BODY,
    ]
    return "\n".join(lines)
