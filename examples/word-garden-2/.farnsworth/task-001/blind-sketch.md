# Blind Sketch — task-001 (Word Garden core engine)

Written BEFORE reading any candidate diff. This is "candidate 6".

## Module layout
```
word_garden/__init__.py   # maybe re-export GameState, new_game, etc.
word_garden/words.py
word_garden/game.py
tests/__init__.py
tests/test_game.py
tests/test_words.py
```

## words.py
```python
WORDS = ["GARDEN", "FLOWER", "PLANET", "PYTHON", "TERMINAL",
         "MEADOW", "ORCHARD", "VINEYARD", "SEEDLING", "HARVEST"]  # all uppercase

_DIFFICULTY = {
    "easy":   {"water": 8, "min": 4, "max": 6},
    "normal": {"water": 6, "min": 5, "max": 8},
    "hard":   {"water": 4, "min": 7, "max": None},  # 7+
}

def water_for(difficulty="normal") -> int:
    if difficulty not in _DIFFICULTY: raise ValueError(...)
    return _DIFFICULTY[difficulty]["water"]

def select_word(difficulty="normal", rng=None) -> str:
    if difficulty not in _DIFFICULTY: raise ValueError(...)
    spec = _DIFFICULTY[difficulty]
    pool = [w for w in WORDS if spec["min"] <= len(w) and (spec["max"] is None or len(w) <= spec["max"])]
    chooser = rng if rng is not None else random
    return chooser.choice(pool)
```
Subtle: hard filter must be 7+ (VINEYARD=8, SEEDLING=8, TERMINAL=8, ORCHARD=7, HARVEST=7 qualify). Must ensure each difficulty pool is non-empty against the real word list. Verify length bounds inclusive.

## game.py
```python
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

def new_game(difficulty="normal", rng=None) -> GameState:
    word = words.select_word(difficulty, rng).upper()
    w = words.water_for(difficulty)
    return GameState(word, set(), w, 0, w)

def validate_guess(input_text) -> tuple[str|None, str]:
    s = input_text.strip().upper()
    if s == "": return (None, "Please enter a single letter.")
    if len(s) != 1: return (None, "Please enter a single letter.")
    if not s.isalpha(): return (None, "That is not a letter.")
    return (s, "")
    # NOTE: must NOT consult state; repeated-guess is apply_guess's job.

def apply_guess(state, letter) -> GameState:
    # mutate-or-return: I'd mutate state in place and return it (signature returns GameState).
    if state.game_over:
        state.status_message = "The game is over."
        return state
    if letter in state.guessed_letters:
        state.status_message = f"You already guessed {letter}. Try another letter."
        return state
    state.guessed_letters.add(letter)
    if letter in state.secret_word:
        state.status_message = "Good guess! The garden grows."
    else:
        state.remaining_water -= 1
        state.weed_count += 1
        state.status_message = "No match. A weed appears."
    # resolve end-of-game AFTER applying:
    if is_won(state):
        state.won = True; state.game_over = True
        state.status_message = f"Bloom! You guessed the word: {state.secret_word}"
    elif is_lost(state):
        state.game_over = True
        state.status_message = f"The garden ran out of water. The word was: {state.secret_word}"
    return state

def display_word(state) -> str:
    return " ".join(c if c in state.guessed_letters else "_" for c in state.secret_word)

def is_won(state) -> bool:
    return all(c in state.guessed_letters for c in state.secret_word)

def is_lost(state) -> bool:
    return state.remaining_water <= 0 and not is_won(state)
```

## Subtle edge cases I'd guard
1. **Win/loss interaction at water 0**: the win that empties the last water on a CORRECT guess can't happen (correct guesses don't cost water). But a *wrong* guess that drops water to 0 could coincide with the word already being complete — impossible since wrong letter isn't in word. The real subtlety: `is_lost` MUST yield to `is_won` (check won first). I order win check before loss check, and is_lost ANDs `not is_won`.
2. **A win achieved at exactly 0 water**: if water is already 0 but word completes via a correct guess — guard so won wins. is_lost must return False when is_won is True.
3. **Repeated guess after it was wrong**: must not double-penalize; guarded by membership check before mutation.
4. **Guess after game_over**: no-op + message, no state change.
5. **Multi-occurrence letter** (e.g. "L" in... none here, but "E" in GARDEN/SEEDLING) — display reveals ALL positions; covered by display_word using membership.
6. **validate_guess must not look at state** — keep it pure on the string.
7. **Invalid input never mutates** — caller convention: invalid input never reaches apply_guess.

## Tests I'd write
- correct guess reveals all matching positions; water/weeds unchanged; letter recorded.
- wrong guess: water -1 EXACTLY, weeds +1 EXACTLY, letter recorded, message.
- repeat guess: water/weeds unchanged, message says already guessed.
- validate_guess: empty, multichar, digit, symbol, lowercase->upper, spaces trimmed.
- win detection sets won+game_over; is_won True.
- loss detection: drive water to 0, game_over True, won False.
- is_lost False when is_won True even at water 0 (direct call probe).
- display_word masks unguessed, space-separated.
- select_word for easy/normal/hard returns word matching length+in WORDS; deterministic with seeded rng; unknown difficulty raises ValueError.
- apply_guess after game_over is a no-op.

## Open ambiguity to flag
The exact status_message strings are not pinned by the brief beyond "friendly"/"per spec". I'd match SPEC section 6 example strings closely but tests should assert on state, not brittle message equality (except maybe substring for "already guessed").
