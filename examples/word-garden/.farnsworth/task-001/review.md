# Task-001 Review

## Blind sketch (written before reading candidates)

### Layout
`word_garden/{__init__.py,game.py,words.py}` + `tests/{__init__.py,test_game.py,test_words.py}`. Stdlib only. No `input()`/`print()` in `word_garden/`.

### words.py
- `WORDS`: the 10 SPEC §8 words, uppercased, module-level list. Keep order; easy to extend.
- Difficulty table as dict: `{"easy": (8, 4, 6), "normal": (6, 5, 8), "hard": (4, 7, None)}` → (water, min_len, max_len). `7+` = no upper bound.
- `water_for(difficulty="normal") -> int`: table lookup, `ValueError` on unknown key.
- `select_word(difficulty="normal", rng=None) -> str`: validate difficulty (ValueError), filter WORDS by length window, choose with `(rng or random).choice(filtered)`. Inject `random.Random`. Verify each difficulty non-empty against the 10-word list.

### game.py
- `GameState` dataclass EXACT field names/order from §12: `secret_word, guessed_letters, remaining_water, weed_count, max_water, status_message="", game_over=False, won=False`. `guessed_letters: set[str]`.
- `new_game(difficulty="normal", rng=None)`: word=select_word(...).upper(); water=water_for(diff); empty set; weeds=0; max_water=water; flags False.
- `validate_guess(input_text) -> tuple[str|None, str]`: strip; empty/len>1 → "Please enter a single letter."; non-alpha → "That is not a letter."; else (char.upper(), ""). NO state access. Order: length check before alpha so "ab" → length msg, "7" → not-a-letter.
- `apply_guess(state, letter) -> GameState`:
  - game_over → no-op + message.
  - letter already guessed → "already guessed" message, no water/weed change.
  - else add letter; in secret → "Good guess! The garden grows."; else water-=1, weeds+=1, "No match. A weed appears."
  - recompute: win check FIRST (all secret letters guessed → won=True, game_over=True, bloom msg); elif water<=0 → game_over=True, loss msg.
- `display_word(state)`: `" ".join(c if c in guessed else "_" for c in secret_word)`.
- `is_won`: all secret letters in guessed. `is_lost`: water<=0 and not won.

### Edge cases to nail
- Repeated WRONG guess: no second penalty (guard `in guessed` first).
- Guess after game_over: no mutation.
- Win-on-last-water: correct final guess at water==1 → won, not lost (win check first).
- display masks only non-guessed letters.

### Test plan
All 10 §16 cases, POSITIVE assertions: wrong guess asserts water==before-1 AND weeds==before+1 AND letter in guessed. Injected `random.Random(seed)` for determinism. validate for empty/multi/number/symbol/lowercase. win sets won&game_over; loss sets game_over&not won. display masking explicit. select_word for all three difficulties within length window; unknown → ValueError.

## Candidate reviews

All five: tests green (`unittest discover`), `compileall` clean, zero `input()`/`print()` in `word_garden/`, stdlib-only, exact package layout, exact `GameState` field names/order/defaults per §12. Differences below.

### Candidate A — GOOD
- Cleanest module structure. Named message constants (`MSG_*`) exported from `game`, so tests assert exact strings and task-002 can reuse them — best message discipline of the field.
- `select_word` uppercases result defensively; `new_game` uppercases too. Difficulty table is a single dict (`min_len/max_len`, `None`=unbounded) shared by `water_for`/`select_word` — DRY, no duplicated length logic.
- `validate_guess`: most specific messages (distinct multi-char message), `None`-safe on input. Order length-before-alpha is correct.
- `is_lost` correctly guards `and not is_won` → won-at-zero-water returns False (verified).
- Tests: 39, all positive assertions incl. the combined water-1/weeds+1/letter-recorded check; deterministic via injected `Random`; covers all ten §16 cases; multi-occurrence reveal (BANANA) tested.
- BAD / watch: `apply_guess` MUTATES `state` in place and returns the same object (`ret is state`). Faithful to the `-> GameState` contract but differs from B/C/D/E; task-002 must not rely on the old reference being preserved. This is the only notable divergence and it is a documented design choice, not a defect.

### Candidate B — GOOD
- Immutable style via `dataclasses.replace`; original never mutated (verified). Good `__init__.py` is minimal; `_state` test helper is clean.
- `is_lost` correctly guarded (won-at-zero → False). Win-checked-before-loss ordering correct. Rich win/loss messages include the word.
- Tests: 66, thorough, positive assertions, explicit no-mutation tests, multi-occurrence reveal, single-char word edge.
- BAD / watch: empty-input message is `"Please enter a letter."` (drops the word "single") — still specific/helpful and spec-acceptable, but inconsistent with its own multi-char message. Couples tests to immutability (`assertIsNot`), which is a legitimate but not contractually-required choice. Imports `Optional` from typing while also using `set[str]` builtin generics — minor stylistic mix.

### Candidate C — GOOD (with a test smell)
- Correct logic; `is_lost` guarded properly; immutable (returns new object). Messages exact-match the spec examples.
- Tests: 47, positive assertions, exact field-set check via `dataclasses.fields`.
- BAD / watch: several tests do `state = new_game("normal"); state.secret_word = "GARDEN"; state.guessed_letters = set()` — i.e. spin up a RANDOM game then overwrite fields. Works (dataclass is mutable) but is fragile and conceptually muddled; a direct `GameState(...)` fixture (as in its own display tests) is cleaner. `apply_guess` is very verbose (full `GameState(...)` re-construction in every branch) — correct but high-noise.

### Candidate D — CORRECTNESS BUG
- Structure and apply_guess flow are fine; immutable; messages spec-faithful.
- BAD (real defect): `is_lost(state)` returns `state.remaining_water <= 0` WITHOUT `and not is_won(...)`. A won state that happens to sit at 0 water reports `is_lost() == True` (verified: returns True where A/B/C/E return False). The brief defines loss as "water at 0 BEFORE that [win]". `apply_guess` masks the bug internally because it checks `is_won` first, so flags end up correct and the gate passes — but the public helper is contractually wrong and task-002 will call it directly. No test exercises won-at-zero-water for `is_lost`, which is exactly why the gate missed it.
- Other minor: `select_word` uses `float('inf')` as max_len for hard (works, but stringly/float in an int-length context); `new_game` passes `rng` positionally and does not `.upper()` the selected word (harmless — WORDS already uppercase). Tests: 44, decent but the `is_lost` coverage gap is the headline.

### Candidate E — GOOD (most tests; minor logic oddities)
- Immutable; `is_lost` guarded (`== 0 and not is_won`, won-at-zero → False, verified). `None`-safe validate. Largest, best-organised suite (77 tests) with section-mapped docstrings, multi-occurrence reveal, deterministic rng.
- BAD / watch: terminal logic computes `won = all_revealed and new_water >= 0` — the `>= 0` is dead/always-true (a correct guess never lowers water; all_revealed can't arise on a wrong guess). Harmless but confusing. `is_lost` and `apply_guess` use `water == 0` rather than `<= 0`; safe only because water never goes below 0 under the game_over guard — slightly more brittle than `<= 0` if a future caller bypasses the guard. Win/loss messages are inlined string literals (no shared constants), so UI/tests can't reuse them as cleanly as A.

## Verdict

**adopt — Candidate A.**

A is the only candidate that is simultaneously correct, complete, and best-aligned with the cross-task contract:
- `is_lost` is correctly guarded (`and not is_won`) — D fails this in its public helper.
- Single shared difficulty table feeding both `water_for` and `select_word` (no duplicated length windows to drift).
- Exported `MSG_*` constants — the cleanest message contract for task-002's UI and for exact-string test assertions.
- Most specific validation messages; `None`-safe; correct length-before-alpha ordering.
- 39 deterministic tests, all positive assertions, all ten §16 cases including multi-occurrence reveal.

Its sole divergence — `apply_guess` mutates and returns the same object rather than a fresh one — is faithful to the `-> GameState` signature and is now captured as a project truth in `.code-tips.md` so task-002 does not assume the old reference is preserved.

**Runners-up:**
- **B** and **E**: both fully correct and complete with immutable (`replace`/reconstruct) semantics and larger suites. Either is adoptable; ranked just below A only on contract polish (B's slightly inconsistent empty-input message and typing-mix; E's dead `>= 0` clause, `== 0` instead of `<= 0`, and inlined message strings). If immutability is later preferred over A's in-place style, B is the cleanest immutable base.
- **C**: correct logic but a fragile test idiom (construct a random `new_game` then overwrite `secret_word`/`guessed_letters`); verbose branch-by-branch `GameState(...)` reconstruction.
- **D**: not adoptable as-is — `is_lost` omits the `not is_won` guard, so a win achieved at exactly 0 water is mislabelled a loss. The gate passed only because `apply_guess` checks `is_won` first and no test covers won-at-zero-water for the helper directly.
