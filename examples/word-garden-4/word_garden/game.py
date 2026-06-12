from dataclasses import dataclass, replace

from . import words

# ---------------------------------------------------------------------------
# User-facing message constants.
# Tests MUST import these rather than re-typing string literals.
# ---------------------------------------------------------------------------

MSG_CORRECT = "Good guess! The garden grows."
MSG_INCORRECT = "No match. A weed appears."
MSG_ALREADY_GUESSED_TEMPLATE = "You already guessed {letter}. Try another letter."
MSG_INVALID_NOT_SINGLE = "Please enter a single letter."
MSG_INVALID_NOT_LETTER = "That is not a letter."
MSG_GAME_OVER = "The game is already over."
MSG_WIN_TEMPLATE = "You guessed the word: {word}. The garden is thriving."
MSG_LOSS_TEMPLATE = "The garden ran out of water. The word was: {word}."


@dataclass
class GameState:
    secret_word: str
    guessed_letters: set[str]
    remaining_water: int
    weed_count: int
    max_water: int
    status_message: str = ""
    game_over: bool = False
    won: bool = False


def new_game(difficulty: str = "normal", rng=None) -> GameState:
    """Create and return a fresh GameState for the given difficulty."""
    word = words.select_word(difficulty, rng=rng)
    water = words.water_for(difficulty)
    return GameState(
        secret_word=word.upper(),
        guessed_letters=set(),
        remaining_water=water,
        weed_count=0,
        max_water=water,
    )


def validate_guess(input_text: str) -> tuple[str | None, str]:
    """Validate raw player input without consulting game state.

    Returns (letter, "") on success, or (None, error_message) on failure.
    The returned letter is trimmed and uppercased.
    """
    text = input_text.strip().upper()
    if not text:
        return (None, MSG_INVALID_NOT_SINGLE)
    if len(text) > 1:
        return (None, MSG_INVALID_NOT_SINGLE)
    if not text.isalpha():
        return (None, MSG_INVALID_NOT_LETTER)
    return (text, "")


def apply_guess(state: GameState, letter: str) -> GameState:
    """Apply one already-validated uppercase letter to the game state.

    Returns a new GameState; the original is never mutated.
    Repeated-guess detection and post-game-over no-op are handled here.
    """
    if state.game_over:
        return replace(state, status_message=MSG_GAME_OVER)

    if letter in state.guessed_letters:
        msg = MSG_ALREADY_GUESSED_TEMPLATE.format(letter=letter)
        return replace(state, status_message=msg)

    new_guessed = state.guessed_letters | {letter}

    if letter in state.secret_word:
        new_state = replace(state, guessed_letters=new_guessed, status_message=MSG_CORRECT)
        if is_won(new_state):
            msg = MSG_WIN_TEMPLATE.format(word=new_state.secret_word)
            return replace(new_state, game_over=True, won=True, status_message=msg)
        return new_state

    new_state = replace(
        state,
        guessed_letters=new_guessed,
        remaining_water=state.remaining_water - 1,
        weed_count=state.weed_count + 1,
        status_message=MSG_INCORRECT,
    )
    if is_lost(new_state):
        msg = MSG_LOSS_TEMPLATE.format(word=new_state.secret_word)
        return replace(new_state, game_over=True, won=False, status_message=msg)
    return new_state


def display_word(state: GameState) -> str:
    """Return the secret word with unguessed letters masked as underscores.

    Letters are space-separated, e.g. 'G _ R _ E _'.
    """
    return " ".join(
        ch if ch in state.guessed_letters else "_"
        for ch in state.secret_word
    )


def is_won(state: GameState) -> bool:
    """Return True when every letter of the secret word has been guessed."""
    return all(ch in state.guessed_letters for ch in state.secret_word)


def is_lost(state: GameState) -> bool:
    """Return True when water is exhausted and the word has not been won."""
    return state.remaining_water <= 0 and not is_won(state)
