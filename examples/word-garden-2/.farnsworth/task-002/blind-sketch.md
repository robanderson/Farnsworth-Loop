# Blind Sketch — task-002 (Word Garden UI)

Written BEFORE reading any candidate diff. How I would build the UI layer on
the fixed engine (`game.py`, `words.py`).

## ui.py — pure rendering, no I/O

Module-level glyph tables, keyed by mode, NOT magic strings scattered around:

```
EMOJI = {"start":"🌱","progress":"🌿","near":"🌷","win":"🌻","loss":"🥀",
         "water":"💧","weed":"🌿"}
ASCII = {"start":"*","progress":"*","near":"*","win":"*","loss":"x",
         "water":"#","weed":"-"}  # all chars .isascii()
```

(Re-using 🌿 for both "progress" stage and "weed" glyph is fine per SPEC §10.)

### growth-stage logic
A single helper `growth_stage(state) -> str` returning one of
start/progress/near/win/loss, in this precedence:
1. `state.won` -> "win"
2. `state.game_over` (lost) / `is_lost(state)` -> "loss"
3. compute reveal fraction = revealed distinct positions / len(secret).
   - 0 revealed -> "start"
   - >= some near-win threshold (e.g. all but one letter, or >= ~0.8) -> "near"
   - otherwise -> "progress"

Use the engine `is_won`/`is_lost` predicates rather than re-deriving win/loss
from water — honors the task-001 invariant that win beats loss.

### render(state, ascii_mode=False) -> str
Returns a string (no print). Order per SPEC §9:
1. title line: `{stage_glyph} Word Garden`
2. blank line
3. `Word:     ` + `display_word(state)`  (reuse engine `display_word`)
4. `Guessed:  ` + sorted, space-joined `guessed_letters`
5. `Water:    {remaining}/{max} ` + water glyph * remaining  (§18: label+count)
6. `Weeds:    {weed_count} ` + weed glyph * weed_count
7. blank line
8. previous `status_message` (if non-empty)

§18 accessibility: water shows `remaining/max` AND symbols; weeds shows a raw
COUNT (not a fraction of water) AND symbols. Both carry a text label. Pad
labels so columns align. ASCII mode: assert every char `.isascii()`.

### win_screen / loss_screen
- `win_screen`: `🌻 Bloom!` / blank / `You guessed the word: {secret}` /
  `The garden is thriving.`  (ascii: replace 🌻)
- `loss_screen`: `🥀 The garden ran out of water.` / blank /
  `The word was: {secret}` / `Try again and grow a new garden.`
  Loss MUST reveal secret_word.

Prefer importing `MSG_WIN`/`MSG_LOSS` from game.py where the screen text
overlaps, rather than re-typing — but SPEC §6.6/6.7 screen text differs from
MSG_* slightly, so screens may legitimately compose their own lines. At
minimum the UI/tests should import MSG_* constants where they assert engine
feedback messages (the .code-tips.md contract).

## main.py — the only I/O module

```
def main(argv=None, input_fn=input, output_fn=print) -> int:
    args = build_parser().parse_args(argv)   # --difficulty {easy,normal,hard}, --ascii
    state = new_game(args.difficulty)
    try:
        while not state.game_over:
            output_fn(render(state, args.ascii))
            raw = input_fn("Guess a letter: ")
            letter, msg = validate_guess(raw)
            if letter is None:
                state.status_message = msg     # re-prompt, no turn consumed
                continue
            apply_guess(state, letter)
        output_fn(win_screen(...) if state.won else loss_screen(...))
        return 0
    except (EOFError, KeyboardInterrupt):
        output_fn("\nThanks for visiting the garden. Goodbye!")
        return 0
```

- argparse choices enforce valid difficulty; bad value -> argparse exits 2.
- `--help` -> exits 0.
- Invalid input sets the message and `continue`s WITHOUT calling apply_guess,
  so no water consumed (re-render shows the validation message).
- EOF/Ctrl-C -> friendly line, return 0, no traceback.
- Use input_fn/output_fn EXCLUSIVELY (no bare print/input).

### __main__.py
```
from word_garden.main import main
import sys
if __name__ == "__main__":
    sys.exit(main())
```

## tests/test_ui.py
- render emoji mode contains labels `Water:`/`Weeds:` AND counts AND glyphs.
- render ascii mode: `assert rendered.isascii()` over a full game's worth of
  renders (start, mid, near, win, loss) — positive assertion.
- emoji mode: `assert not render(...).isascii()` (proves modes differ).
- growth stage at start (no guesses), mid (some), near-win (all but one),
  win, loss — assert correct glyph appears.
- win_screen contains secret word + "Bloom"; loss_screen reveals secret word.
- scripted end-to-end `main(input_fn=..., output_fn=...)`:
  - WIN: feed correct letters of a deterministic word (inject via new_game rng
    OR script enough letters A-Z); capture output; assert win screen text
    appeared and return code 0.
  - LOSS: feed wrong letters until water gone; assert loss screen + secret.
- invalid input (e.g. "", "ab", "7", "!") does NOT consume water: script an
  invalid then valid sequence and assert water unchanged after the invalid.
- EOF: input_fn raising EOFError -> main returns 0, goodbye printed.
- Reuse engine MSG_* constants in assertions, not retyped literals.

To make the scripted game deterministic, I'd either monkeypatch
`word_garden.words.select_word`/`new_game` to fix the word, or pass a seeded
rng path. Then I know the exact letters to win/lose.

## README.md
SPEC §19 intro paragraph; run instructions (`python3 -m word_garden`,
`--difficulty easy|normal|hard`, `--ascii`); rules summary (guess letters,
wrong guess costs water + weed, win by revealing word, lose at 0 water);
a sample rendered screen; friendly tone.

## Things I expect to be the differentiators / failure points
- §18 weeds rendered as a fraction of water (WRONG) vs a raw count (right).
- ascii test asserting only substring presence, not full `.isascii()`.
- emoji test not proving non-ASCII (no negative assertion).
- invalid-input test missing the "water unchanged" assertion.
- bare print/input leaking into main instead of input_fn/output_fn.
- retyping message strings instead of importing MSG_*.
- KeyboardInterrupt not handled (only EOF), or traceback on Ctrl-C.
