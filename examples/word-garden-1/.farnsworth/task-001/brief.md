# Task 001 — Word Garden core: game logic, words, tests (no UI)

## Goal

Implement the engine of the Word Garden game described in `SPEC.md`
(sections 6–8, 12–14, 16): pure, importable game logic with unit tests.
NO terminal UI in this task — no `input()`, no `print()`, no main loop.
The UI is task-002 and will be built on top of whatever this task ships,
so the module boundaries below are a contract, not a suggestion.

## Hard requirements

1. **Stdlib only, Python 3.11+.** Package layout:
   ```
   word_garden/__init__.py
   word_garden/game.py
   word_garden/words.py
   tests/__init__.py
   tests/test_game.py
   tests/test_words.py
   ```
   (Tests may be one file or several, but live in `tests/` as a package.)
2. **`word_garden/words.py`:**
   - `WORDS`: the 10-word list from SPEC.md section 8, uppercase.
   - `select_word(difficulty="normal", rng=None) -> str`: returns a random
     word filtered by the difficulty table in SPEC.md section 7
     (easy: water 8, length 4–6; normal: water 6, length 5–8;
     hard: water 4, length 7+). `rng` is an injectable `random.Random`
     instance for deterministic tests; default uses the module-level
     `random` functions. Unknown difficulty raises `ValueError`.
   - `water_for(difficulty="normal") -> int`: starting water per the table.
3. **`word_garden/game.py`:**
   - `GameState` dataclass exactly per SPEC.md section 12:
     `secret_word, guessed_letters, remaining_water, weed_count, max_water,
     status_message="", game_over=False, won=False`.
   - `new_game(difficulty="normal", rng=None) -> GameState`: picks the word
     via `words.select_word`, uppercases it, full water, zero weeds.
   - `validate_guess(input_text) -> tuple[str | None, str]`: returns
     `(letter, "")` for valid input (trimmed, uppercased, exactly one
     alphabetic character) or `(None, message)` with a specific, helpful
     message per SPEC.md section 14. Validation does NOT consult game
     state; repeated-guess detection belongs to `apply_guess`.
   - `apply_guess(state, letter) -> GameState`: applies one already-validated
     uppercase letter per SPEC.md sections 6.3–6.5: correct guess reveals
     (no water/weed change), wrong guess costs 1 water and adds 1 weed,
     repeated guess changes nothing but the message. Sets `status_message`
     to friendly text per the spec, and updates `game_over`/`won` when the
     guess ends the game. Guessing after `game_over` is a no-op with a message.
   - `display_word(state) -> str`: masked word, space-separated, e.g.
     `G _ R _ E _`.
   - `is_won(state) -> bool`, `is_lost(state) -> bool`: win = all letters of
     the secret word guessed; loss = water at 0 before that.
4. **Purity:** `game.py` and `words.py` must not read stdin, write stdout,
   or import anything beyond the stdlib. Game logic must be fully testable
   without a terminal (SPEC.md section 16).
5. **Tests:** cover at least the ten cases in SPEC.md section 16 (UI-free
   ones — case 9 means `display_word`, case 10 means `select_word` for every
   difficulty). Assert the POSITIVE outcome, not just the absence of the
   negative (e.g. a wrong guess test asserts water went down by exactly 1
   AND weeds went up by exactly 1 AND the letter was recorded).
   `python3 -m unittest discover -s tests` must pass from the repo root.
6. **Hygiene:** commit all work to your branch with clear messages. Never
   commit `__pycache__`/`*.pyc` (a `.gitignore` already exists). Never write
   or commit `.code-tips.md`. Do not modify `SPEC.md`, `farnsworth.json`,
   or `tasks/`.

## Acceptance criteria

- [ ] `python3 -m unittest discover -s tests` green from repo root, with the
      SPEC section 16 cases covered and positive assertions.
- [ ] `python3 -m compileall -q word_garden` green.
- [ ] No UI: zero `input()`/`print()` in `word_garden/`.
- [ ] `GameState` field names exactly as SPEC section 12.
- [ ] Wrong guess: water -1, weeds +1, letter recorded, friendly message.
- [ ] Repeat guess: no water/weed change, message says already guessed.
- [ ] Invalid input never mutates state and yields a specific message.
- [ ] Win and loss are both detected and set `game_over`/`won` correctly.
- [ ] Stdlib only; no committed bytecode.

## Out of scope

UI rendering, emoji/ASCII modes, `main.py`/`__main__.py`, CLI flags,
difficulty selection UI, README, play-again loop. (All task-002.)
