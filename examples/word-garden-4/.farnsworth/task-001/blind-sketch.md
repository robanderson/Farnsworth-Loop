# Blind Sketch — Task 001 (Word Garden core)

Written before reading any candidate. My own outline of how I'd build this.

## Module layout
```
word_garden/__init__.py   # may re-export, keep light
word_garden/words.py
word_garden/game.py
tests/__init__.py
tests/test_words.py
tests/test_game.py
```

## words.py

```python
import random

WORDS = ["GARDEN","FLOWER","PLANET","PYTHON","TERMINAL",
         "MEADOW","ORCHARD","VINEYARD","SEEDLING","HARVEST"]  # all uppercase

# Single source of truth for the difficulty table (DRY — code-tips rule).
# (water, min_len, max_len_or_None)
_DIFFICULTY = {
    "easy":   (8, 4, 6),
    "normal": (6, 5, 8),
    "hard":   (4, 7, None),
}

def water_for(difficulty="normal") -> int:
    try:
        return _DIFFICULTY[difficulty][0]
    except KeyError:
        raise ValueError(...)

def select_word(difficulty="normal", rng=None) -> str:
    if difficulty not in _DIFFICULTY: raise ValueError(...)
    _, lo, hi = _DIFFICULTY[difficulty]
    pool = [w for w in WORDS if lo <= len(w) <= (hi if hi is not None else 10**9)]
    if not pool: raise ValueError(...)   # never silently fall back (code-tips)
    chooser = rng if rng is not None else random   # default to module random (code-tips)
    return chooser.choice(pool)
```

### Pool sanity check (lengths)
GARDEN6 FLOWER6 PLANET6 PYTHON6 TERMINAL8 MEADOW6 ORCHARD7 VINEYARD8 SEEDLING8 HARVEST7
- easy 4–6: GARDEN,FLOWER,PLANET,PYTHON,MEADOW (5) — non-empty ✓
- normal 5–8: all 10 ✓
- hard 7+: TERMINAL,ORCHARD,VINEYARD,SEEDLING,HARVEST (5) — non-empty ✓

## game.py

```python
from dataclasses import dataclass, field
from . import words

# Message constants defined ONCE (code-tips: messages as module constants).
MSG_CORRECT = "Good guess! The garden grows."
MSG_WRONG   = "No match. A weed appears."
MSG_REPEAT  = "You already guessed {letter}. Try another letter."
MSG_WON     = ...   # "Bloom!" themed
MSG_LOST    = ...   # ran out of water themed
MSG_OVER    = ...   # guess after game over no-op
# validation messages
MSG_NEED_ONE = "Please enter a single letter."
MSG_NOT_LETTER = "That is not a letter."

@dataclass
class GameState:
    secret_word: str
    guessed_letters: set       # set[str]
    remaining_water: int
    weed_count: int
    max_water: int
    status_message: str = ""
    game_over: bool = False
    won: bool = False
```

Field names MUST match SPEC §12 exactly (acceptance criterion). Order/defaults as given.

### new_game(difficulty="normal", rng=None)
- word = words.select_word(difficulty, rng).upper()
- water = words.water_for(difficulty)
- GameState(secret_word=word, guessed_letters=set(), remaining_water=water,
  weed_count=0, max_water=water, status_message="", game_over=False, won=False)

### validate_guess(input_text) -> (letter|None, message)
- MUST NOT consult game state (no repeat detection here).
- s = input_text.strip().upper()
- empty -> (None, MSG_NEED_ONE)
- len != 1 -> (None, MSG_NEED_ONE)
- not s.isalpha() -> (None, MSG_NOT_LETTER)
- else (s, "")
- Order matters: check length before alpha so "7!" → single-letter message? Actually
  "ab" is len2 → need-one; "7" is len1 non-alpha → not-letter; "!" len1 → not-letter.
  Edge: "  " strips to "" → need-one. Multi like "apple" → need-one.

### apply_guess(state, letter) -> GameState
Assume letter already validated (single uppercase alpha). Mutate-and-return (or copy; spec
says returns GameState — I'll mutate in place and return same object, documenting it).
1. if state.game_over: set status to MSG_OVER, return (no-op).
2. if letter in state.guessed_letters: status = MSG_REPEAT, no water/weed change, return.
3. add letter to guessed_letters.
4. if letter in secret_word:
     status = MSG_CORRECT
     if all letters revealed (is_won): won=True, game_over=True, status=MSG_WON
   else:
     remaining_water -= 1
     weed_count += 1
     status = MSG_WRONG
     if remaining_water <= 0: game_over=True, won=False, status=MSG_LOST
5. return state

### display_word(state) -> str
`" ".join(c if c in guessed_letters else "_" for c in secret_word)` → "G _ R _ E _"

### is_won(state) -> bool
`all(c in state.guessed_letters for c in state.secret_word)`

### is_lost(state) -> bool
`state.remaining_water <= 0 and not is_won(state)`

## Risks / edge cases to guard & test
- **Terminal-state priority**: a correct final guess wins even if water is low; a wrong
  guess that zeroes water loses. The two paths are mutually exclusive (win only via
  correct, loss only via wrong) so no simultaneous win+loss — good, but verify ordering.
- **No double penalty on repeat**: repeated WRONG guess must not drain water again
  (letter already in set → early return). Classic bug.
- **Guess after game_over**: must be a pure no-op except message.
- **validate_guess never mutates state** — it doesn't even receive state. Confirm signature.
- **Lowercase normalization**: "a" → "A" and matches uppercase secret.
- **Whitespace**: " a " → "A".
- **isalpha on unicode**: "é".isalpha() is True in Python — spec says "alphabetic", acceptable;
  but digits/symbols rejected with NOT_LETTER. Don't over-engineer ASCII-only unless spec demands.
- **select_word determinism**: tests MUST inject seeded Random (code-tips).
- **win with repeated letters in word** (e.g. none here have dup? SEEDLING has E,E and
  two... S-E-E-D-L-I-N-G has E twice; guessing E reveals both). Test reveal-all.
- **Purity**: no print/input/non-stdlib import in word_garden/.

## Test plan (SPEC §16, positive assertions)
1. correct guess reveals all matching positions (assert display + letter in set + no water change)
2. wrong guess: water-1 AND weed+1 AND letter recorded AND message
3. (covered by 2) weed+1
4. repeated guess: water unchanged AND weed unchanged AND message says already
5. invalid input rejected: each of empty/multi/digit/symbol → (None, specific msg), state untouched
6. lowercase normalized
7. win detected: game_over & won True, MSG_WON
8. loss detected: drive water to 0, game_over True & won False, MSG_LOST
9. display_word masks unguessed
10. select_word valid word for EVERY difficulty (easy/normal/hard), length within band, ∈ WORDS
- plus: guess-after-over no-op; repeated wrong guess no double drain; ValueError on bad difficulty.
