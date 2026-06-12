# Blind Sketch — Task 002 (UI, main loop, packaging)

Written BEFORE reading any candidate diff. Anchoring defence.

## Fixed contract I am building on (read from engine)

- `GameState`: `secret_word, guessed_letters (set[str]), remaining_water,
  weed_count, max_water, status_message, game_over, won`.
- `new_game(difficulty="normal", rng=None)`, `validate_guess(text) ->
  (letter|None, error_msg)`, `apply_guess(state, letter) -> GameState`
  (returns new state — caller MUST reassign), `display_word(state)`,
  `is_won`, `is_lost`.
- Message constants live in `game.py` (MSG_CORRECT, MSG_INCORRECT,
  MSG_WIN_TEMPLATE, MSG_LOSS_TEMPLATE, etc.). On win/loss the engine ALREADY
  overwrites `status_message` with the terminal text naming the word.
- Difficulty table (water + word-length band) lives once in `words.py`.

## ui.py — pure rendering, zero I/O

Constants (module-level, defined once, imported by tests):
- Glyphs: `WATER_EMOJI="💧"`, `WEED_EMOJI="🌿"`, ASCII water cell `*` in
  `[......]`, weeds `-` in `[---]` (per SPEC §10 fallback block).
- Growth stage tables, emoji and ascii, keyed by a stage enum/string:
  - emoji: start `🌱`, progress `🌿`, near-win `🌷`, win `🌻`, loss `🥀`
  - ascii: a distinct printable token per stage, all pure ASCII (e.g.
    `seedling` / `growing` / `budding` / `bloom!` / `wilted`, or `*`).
- `TITLE = "Word Garden"` with emoji `🌱` prefix in emoji mode, plain in ascii.

Helpers:
- `_stage(state) -> str`: derive stage from progress. Logic:
  - if `state.won` (or is_won): `win`
  - elif `state.game_over` and not won: `loss`
  - else compute fraction of distinct secret letters revealed:
    revealed/total. `start` when 0 (no correct letters yet), `near-win`
    when only 1 letter (or <=1) remains hidden, `progress` otherwise.
  - Edge: a 1-distinct-letter word — guard so "start" vs "near-win" still
    sane; near-win should mean "almost there", so base it on letters
    remaining, not raw count.
- `_water_line(state, ascii_mode)`: label + count + symbols. MUST be
  `Water: <remaining>/<max> ` then `remaining` filled symbols (and per
  SPEC §18 example the count text is always present). Decide whether to
  also show empty slots — show filled = remaining, and the `n/max` count
  carries the rest. Never symbols alone.
- `_weed_line`: `Weeds: <count> ` + count weed symbols.
- `_guessed_line`: sorted, space-separated guessed letters.

Public:
- `render(state, ascii_mode=False) -> str` — assembles, in SPEC §9 order:
  title, plant/garden status (stage glyph + maybe word like "Garden:"),
  `Word: ` + `display_word(state)`, `Guessed: ` + sorted letters,
  water line, weeds line, blank line, previous `status_message`.
  Returns a single string (no trailing prompt — main.py prints the prompt).
- `win_screen(state, ascii_mode=False)` — SPEC §6.6: stage glyph `🌻` /
  ascii, "Bloom!", "You guessed the word: WORD", "The garden is thriving."
- `loss_screen(state, ascii_mode=False)` — SPEC §6.7: `🥀`/ascii, "The
  garden ran out of water.", "The word was: WORD", "Try again...".
  MUST reveal `state.secret_word`.

Critical: in `ascii_mode=True`, EVERY character of EVERY output (render,
win, loss, all stages, water/weed symbols) must be ASCII (`s.isascii()`).
This includes end screens — a common miss.

## main.py — the ONLY I/O module

- `main(argv=None, input_fn=input, output_fn=print) -> int`:
  - argparse: `--difficulty {easy,normal,hard}` default `normal`,
    `--ascii` store_true. NEVER wrap parse_args in try/except SystemExit
    (so --help exits 0, usage error exits 2). `argv` passed to
    `parse_args(argv)`.
  - `state = new_game(args.difficulty)` (production RNG, rng=None).
  - Loop:
    - `output_fn(ui.render(state, ascii))`
    - read with `input_fn("Guess a letter: ")` inside try for EOFError /
      KeyboardInterrupt -> friendly goodbye via output_fn, return 0.
    - `letter, err = validate_guess(raw)`; if err: `output_fn(err)`,
      continue WITHOUT touching state (no water consumed).
    - `state = apply_guess(state, letter)` (reassign!).
    - if `state.game_over`: break.
  - After loop: `output_fn(win_screen if state.won else loss_screen)`,
    return 0.
- `__main__.py`: `from .main import main; raise SystemExit(main())` —
  propagate the return code.

## tests/test_ui.py

Build fixtures by constructing `GameState(...)` directly with pinned
values (no `new_game()` then overwrite — RNG leak). Import message/glyph
constants, don't retype literals.

- render emoji: asserts labels AND counts present ("Water:", "4/6",
  contains 💧) — positive assertion.
- render ascii: assert `out.isascii()` is True (positive, whole-string) AND
  labels/counts present.
- growth stages: construct states at start (no guesses), mid (some), near-
  win (one letter left), win state, loss state; assert correct stage glyph
  appears in render/screens.
- win_screen and loss_screen: assert word revealed, correct headline.
- e2e win: inject `input_fn` returning scripted letters that spell a known
  word (force the word by injecting rng via... but main calls new_game with
  no rng — so monkeypatch `words._random`/select, OR seed; per tips, force
  a known scenario). Assert win screen text appeared in captured output.
- e2e loss: scripted wrong letters until water gone; assert loss screen +
  word appeared. Assert exact terminal message, not just exit code.

Note: main() uses production `new_game` (rng=None) — to make e2e
deterministic, the test must monkeypatch the randomness source (e.g.
`words.WORDS` or `random.choice`) to pin the secret word, then drive
input to a known win/loss. Asserting an OR of outcomes proves nothing.

## Risks / things I will check in candidates

1. ASCII purity in END SCREENS, not just render. Easy to forget the win
   `🌻` / loss `🥀` glyph in ascii mode.
2. Water line must carry BOTH text count and symbol per §18 — not symbols
   only; and not count only.
3. Invalid input must `continue` before apply_guess so no water consumed —
   verify the control flow, not just the message.
4. Reassigning `state = apply_guess(...)` — engine returns new object.
5. argparse: no SystemExit swallowing; usage error exit 2, --help exit 0.
6. EOF AND KeyboardInterrupt both caught; return 0; no traceback.
7. Growth stage thresholds: near-win must actually trigger before win;
   off-by-one on "letters remaining" is the likely bug.
8. e2e tests must pin randomness, not assert an OR of acceptable outputs.
9. No print/input in ui.py; main.py the only stdio module; engine bytes
   untouched.
10. README present with §19 intro, run instructions, rules, sample screen.
