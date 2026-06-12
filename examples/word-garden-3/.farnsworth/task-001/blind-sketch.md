# Blind Sketch — task-001 (my own implementation outline)

Written BEFORE opening any candidate diff. This is candidate "F" if I synthesize.

## Module responsibilities

### `word_garden/words.py`
- `WORDS: list[str]` — the 10 SPEC §8 words, uppercase, in spec order:
  GARDEN, FLOWER, PLANET, PYTHON, TERMINAL, MEADOW, ORCHARD, VINEYARD,
  SEEDLING, HARVEST.
- Difficulty table as a single source of truth, e.g.
  `DIFFICULTIES = {"easy": (8, 4, 6), "normal": (6, 5, 8), "hard": (4, 7, None)}`
  (water, min_len, max_len). max_len None = no upper bound.
- `water_for(difficulty="normal") -> int`: look up water; unknown -> `ValueError`.
- `select_word(difficulty="normal", rng=None) -> str`:
  - Validate difficulty FIRST (unknown -> `ValueError`) — before touching rng.
  - Filter WORDS by length window.
  - If the filtered pool is EMPTY -> `ValueError` (seed tip: never fall back to
    unfiltered pool). This is the empty-pool path the prompt wants probed.
  - `rng = rng or random` (module-level `random`, NOT a fresh seeded Random —
    seed tip). Return `rng.choice(pool)`.

Length check: GARDEN=6, FLOWER=6, PLANET=6, PYTHON=6, TERMINAL=8, MEADOW=6,
ORCHARD=7, VINEYARD=8, SEEDLING=8, HARVEST=7.
- easy (4–6): GARDEN, FLOWER, PLANET, PYTHON, MEADOW (5 words).
- normal (5–8): all 10.
- hard (7+): TERMINAL, ORCHARD, VINEYARD, SEEDLING, HARVEST (5 words).
All non-empty, good.

### `word_garden/game.py`
- `GameState` dataclass EXACTLY per §12 — field names and order:
  `secret_word, guessed_letters, remaining_water, weed_count, max_water,
   status_message="", game_over=False, won=False`.
  `guessed_letters` is a `set[str]`. Use `field(default_factory=set)` only if a
  default is provided; spec shows no default for the first five, so they are
  required positional.
- Message constants defined ONCE at module level (seed tip: define user-facing
  strings as named constants), e.g.
  `MSG_GOOD`, `MSG_NO_MATCH`, `MSG_ALREADY` (templated on letter),
  `MSG_WIN`, `MSG_LOSS`, `MSG_OVER` (guess after game over),
  plus validation messages `MSG_EMPTY/MULTI/NOT_LETTER`.
- `new_game(difficulty="normal", rng=None) -> GameState`:
  - `word = select_word(difficulty, rng).upper()`
  - `water = water_for(difficulty)`
  - return GameState(secret_word=word, guessed_letters=set(),
    remaining_water=water, weed_count=0, max_water=water).
  - status_message left "" (start state).
- `validate_guess(input_text) -> tuple[str|None, str]`:
  - MUST NOT consult game state (so repeated-guess NOT here).
  - `s = input_text.strip().upper()`
  - empty -> (None, "Please enter a single letter.")
  - len > 1 -> (None, "Please enter a single letter.")
  - not alphabetic (single char but e.g. digit/symbol) -> (None, "That is not a letter.")
  - else (None message empty) -> (s, "")
  - Ordering matters: check empty/length before alpha so "12" gives the
    single-letter message not the not-a-letter message. (Either is defensible;
    I'll treat length-first as canonical but accept candidate variation since
    §14 lists both messages.)
- `apply_guess(state, letter) -> GameState`:
  - Precondition: letter is already validated, single uppercase alpha.
  - If `state.game_over`: set status to MSG_OVER, no mutation of counters,
    return state (no-op except message).
  - If `letter in state.guessed_letters`: set MSG_ALREADY (with letter), no
    water/weed change, return. (Repeated guess.)
  - Add letter to guessed_letters.
  - If letter in secret_word: status = MSG_GOOD. (No water/weed change.)
    Then check win: all letters of secret in guessed_letters -> won=True,
    game_over=True, status=MSG_WIN.
  - Else (wrong): remaining_water -= 1; weed_count += 1; status = MSG_NO_MATCH.
    Then check loss: remaining_water <= 0 -> game_over=True, won=False,
    status=MSG_LOSS.
  - CRITICAL precedence: a correct guess can only ever WIN, a wrong guess can
    only ever LOSE. They are mutually exclusive in a single guess, so there is
    no win-vs-loss tie on the same guess. The subtle case is "win on the last
    correct guess" — must produce WIN message, game_over=True, won=True, NOT a
    lingering "Good guess!". And "wrong guess that drops water to 0" -> LOSS
    message, not lingering "No match."
  - Mutation semantics: I will MUTATE state in place AND return it (return the
    same object). Tests must not assume a fresh copy. I'll document that. The
    return-the-same-object choice keeps `s = apply_guess(s, x)` and in-place
    both correct. (A candidate that returns a copy is also acceptable IF its
    tests use the return value; a candidate that mutates but whose tests assume
    immutability, or vice versa, is a defect.)

- `display_word(state) -> str`: for each char in secret_word, char if in
  guessed_letters else "_", joined by single space. e.g. "G _ R _ E _".
- `is_won(state) -> bool`: all(c in guessed_letters for c in secret_word).
  (Pure predicate over state; should NOT depend on flags so it can be used to
  derive them.)
- `is_lost(state) -> bool`: remaining_water <= 0 and not is_won(state). Loss =
  water 0 BEFORE the word is complete — so win takes precedence: if the word is
  fully revealed it's a win even at water 0. (Edge: win on last unit of water.)

## Subtle edge cases I would guard
1. **Win on last unit of water**: reaching water 0 via wrong guesses, but a
   subsequent correct guess completes the word — but water 0 means... actually
   if water hit 0 the game is already over (loss). The real "win on last water"
   case: water is at 1, player makes the FINAL correct guess (correct guesses
   cost no water) -> WIN. And the trickier framing: is_lost must return False
   when is_won is True even if water==0. Guard: win precedence in is_lost.
2. **Terminal guess status_message**: the last guess sets WIN/LOSS text, not
   "Good guess!"/"No match." (seed tip: flags right, message wrong).
3. **Repeated guess after game over**: game_over check comes FIRST, so a repeat
   after over yields the over-message, not the already-guessed message. Both
   are no-ops on counters either way.
4. **Multi-occurrence letter**: display_word reveals ALL positions (e.g. E in
   SEEDLING). One guess reveals every matching position.
5. **Validation ordering**: empty/multi vs not-a-letter — distinct messages.
6. **select_word unknown difficulty -> ValueError** BEFORE rng use.
7. **Empty pool -> ValueError**, never silent fallback.
8. **rng default = module random**, not a fresh seeded Random.
9. **Repeated wrong guess must not double-penalize**: guessing a wrong letter
   twice — second time is "already guessed", no water loss. Guard via the
   guessed_letters membership check before the wrong-branch.

## Non-negotiable tests
- correct guess reveals all matching positions, no water/weed change, letter
  recorded (positive combined assertion).
- wrong guess: water -1 AND weed +1 AND letter recorded (combined).
- repeat wrong guess: water unchanged, weed unchanged, message = already.
- repeat correct guess: unchanged, message = already.
- invalid input (empty/multi/digit/symbol) each returns (None, specific msg)
  and does NOT mutate state (validate doesn't touch state anyway).
- lowercase normalized: validate("a") -> ("A","").
- win detected: drive to full reveal via seeded rng / pinned state -> won=True,
  game_over=True, status == MSG_WIN (assert the message, seed tip).
- loss detected: drive water to 0 via wrong guesses -> game_over=True,
  won=False, status == MSG_LOSS.
- win on last water: pin a state with water 1, complete word -> won True, NOT
  lost.
- display_word masks unguessed, reveals guessed, space-separated.
- select_word for easy/normal/hard returns a word obeying the length window
  (seeded rng for determinism); unknown difficulty raises ValueError; empty
  pool raises ValueError.
- guess after game_over is a no-op with message.
- Fixtures: construct GameState directly with pinned values (seed tip), do not
  call new_game then overwrite.
