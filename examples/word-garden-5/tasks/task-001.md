# Task 001 — Word Garden, complete game in one shot

## Goal

Implement the ENTIRE Word Garden game described in `SPEC.md` — engine,
terminal UI, CLI entry point, and tests — in this one task. This is not a
milestone slice: when this task is done, `python3 -m word_garden` is the
finished, playable game and the test suite proves it.

## Hard requirements

1. **Stdlib only, Python 3.11+.** Package layout:
   ```
   word_garden/__init__.py
   word_garden/__main__.py
   word_garden/main.py
   word_garden/game.py
   word_garden/ui.py
   word_garden/words.py
   tests/__init__.py
   tests/...
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
     guess ends the game (the end-of-game message overwrites the turn
     message). Guessing after `game_over` is a no-op with a message.
   - `display_word(state) -> str`: masked word, space-separated, e.g.
     `G _ R _ E _`.
   - `is_won(state) -> bool`, `is_lost(state) -> bool`: win = all letters of
     the secret word guessed; loss = water at 0 BEFORE the win.
   - `game.py` and `words.py` must not read stdin or write stdout; logic is
     fully testable without a terminal (SPEC.md section 16).
4. **`word_garden/ui.py`** — pure rendering, zero `print`/`input`; every
   function returns a string:
   - `render(state, ascii_mode=False) -> str`: SPEC.md section 9 fields in
     order — title (with growth glyph), masked word, guessed letters
     (sorted, space-separated), water, weeds, then the previous turn's
     status message (omit the message block when empty). Section 18
     accessibility shapes: water shows `count/max_water` plus symbols;
     weeds show a standalone count plus symbols — text label AND numeric
     count always present.
   - Growth stages per SPEC.md section 10: five observable, distinct
     stages (start / progress / near-win / win / loss) driven by the
     fraction of distinct secret letters revealed, with win/loss taken
     from state flags.
   - Win and loss screens per SPEC.md sections 6.6–6.7 (the loss screen
     keeps the "ran out of water" sense and names the word).
   - `ascii_mode` swaps every emoji for the section 10 ASCII fallback;
     with it the ENTIRE output of a full game session is ASCII.
5. **`word_garden/main.py`** — the only module touching stdin/stdout, and
   only via injected functions:
   - `main(argv=None, input_fn=input, output_fn=print) -> int`. This
     signature is EXACT and CLOSED: do not add parameters, do not make
     `input_fn`/`output_fn` keyword-only. Deterministic tests inject the
     engine's `rng` or monkeypatch `words.select_word` in try/finally.
   - argparse CLI: `--difficulty {easy,normal,hard}` (default normal) and
     `--ascii`. `--help` exits 0; a usage error exits 2 (never swallow
     `SystemExit`).
   - Game loop: render, prompt (`Guess a letter: `), validate via
     `validate_guess` (invalid input costs nothing), apply via
     `apply_guess`, repeat until game over; then print the win/loss screen
     and return 0.
   - `EOFError` and `KeyboardInterrupt` get a friendly goodbye and
     return 0 — no traceback.
   - `word_garden/__main__.py` makes `python3 -m word_garden` work.
6. **Tests:** cover at least the ten cases in SPEC.md section 16, plus
   end-to-end win AND loss sessions with a pinned word asserting the final
   screens, the no-cost paths (invalid input, repeated wrong guess), the
   five growth stages, whole-session ASCII purity under `--ascii`, EOF and
   interrupt exits, and `select_word` for every difficulty.
   `python3 -m unittest discover -s tests` must pass from the repo root.
7. **Hygiene:** commit all work to the current branch with clear messages.
   Never commit `__pycache__`/`*.pyc` (a `.gitignore` exists). Never write
   or commit `.code-tips.md`. Do not modify `SPEC.md`, `GOAL.md`,
   `farnsworth.json`, or `tasks/`.

## Acceptance criteria

- [ ] `python3 -m unittest discover -s tests` green from repo root.
- [ ] `python3 -m compileall -q word_garden` green.
- [ ] `printf '' | python3 -m word_garden` exits 0 with a friendly goodbye;
      same with `--ascii`.
- [ ] `python3 -m word_garden --help` exits 0; `--bogus` exits 2.
- [ ] A full game is winnable and losable at the terminal per SPEC
      sections 5, 9, 15, with the 6.6/6.7 end screens.
- [ ] `GameState` fields and all signatures above exactly as written.
- [ ] Wrong guess: water -1, weeds +1, letter recorded, friendly message.
- [ ] Repeat guess: no water/weed change, message says already guessed.
- [ ] Invalid input never mutates state and yields a specific message.
- [ ] Water line shows `n/max` + symbols; weeds line shows count + symbols.
- [ ] Five distinct growth stages observable across a game.
- [ ] `--ascii` output is entirely ASCII across a whole session.
- [ ] Stdlib only; no committed bytecode; base files untouched.
