# Blind Sketch — task-002 UI / main loop / packaging

Written BEFORE opening any candidate diff. My own design.

## ui.py (pure, returns strings)

### Glyph tables (single source of truth)
```python
EMOJI = {"start":"🌱","progress":"🌿","near":"🌷","win":"🌻","loss":"🥀",
         "water":"💧","weed":"🌿"}
ASCII = {"start":"*","progress":"*","near":"*","win":"*","loss":"x",
         "water":"*","weed":"-"}  # per SPEC §10 fallback: Plant *, Water [*], Weeds [-]
```
Note SPEC §10 ascii fallback shows `Water: [******]`, `Weeds: [---]` — brackets.
I'd render ascii water as `[****  ]` (filled = remaining, padding = spent) to max_water width,
weeds as `[--]`.

### Growth stage logic (driven by PROGRESS, not water)
- loss: `state.game_over and not state.won`
- win: `state.won`
- else compute fraction = revealed_unique / total_unique letters:
  - 0 revealed -> start
  - near-win -> e.g. only 1–2 letters left (fraction >= ~0.7) -> near
  - otherwise -> progress
"Progress" must be driven by how revealed the word is, per task line ("driven by progress").

### render(state, ascii_mode=False) -> str  (SPEC §9 ORDER)
1. Title: `🌱 Word Garden` (emoji) / `Word Garden` or `* Word Garden` (ascii)
2. Plant/garden status line (growth stage glyph + optional label)
3. `Word:     G _ R _ E _`  (display_word from engine)
4. `Guessed:  A E G R` (sorted, space-separated; empty -> blank after label)
5. `Water:   4/6 💧💧💧💧` — LABEL + COUNT + symbols (SPEC §18). count is `n/max`.
6. `Weeds:   2 🌿🌿` — LABEL + standalone COUNT + symbols (SPEC §18 shows weeds as bare `2`, NOT n/max)
7. blank line + previous turn's `status_message`
No I/O. Emoji output MUST contain non-ascii; ascii output MUST be `.isascii()`.

### win_screen / loss_screen
Reuse engine MSG_WIN / MSG_LOSS constants where sensible, but SPEC §6.6/6.7 want a
multi-line screen:
- win: `🌻 Bloom!\n\nYou guessed the word: GARDEN\nThe garden is thriving.`
- loss: `🥀 The garden ran out of water.\n\nThe word was: GARDEN\nTry again and grow a new garden.`
Loss MUST reveal word AND keep "ran out of water" sense. ascii variants pure-ascii.

## main.py (only I/O module)

### Signature — REQUIRED by brief
`main(argv=None, input_fn=input, output_fn=print) -> int`
I will honor exactly this. Any extra params (e.g. rng) = scrutinize.

### Loop
```
args = parser.parse_args(argv)   # NO try/except SystemExit
state = new_game(args.difficulty)
try:
    while not state.game_over:
        output_fn(render(state, ascii_mode=args.ascii))
        raw = input_fn("Guess a letter: ")
        letter, msg = validate_guess(raw)
        if letter is None:
            output_fn(msg); continue   # no turn consumed
        state = apply_guess(state, letter)
    output_fn(win_screen/loss_screen ...)
    return 0
except (EOFError, KeyboardInterrupt):
    output_fn("\nThanks for visiting the garden. Goodbye!")
    return 0
```
- argparse `--difficulty {easy,normal,hard}` default normal, `--ascii` store_true.
- `--help` exits 0, bad flag exits 2 — argparse handles, do NOT swallow SystemExit.
- repeated/invalid handled correctly because engine apply_guess handles repeats (no water),
  and validate gate handles invalid (continue without apply).

## __main__.py
```python
from word_garden.main import main
import sys
if __name__ == "__main__":
    sys.exit(main())
```

## test_ui.py — e2e strategy I'd DEMAND
- render emoji: assert labels+counts present AND output NOT isascii.
- render ascii: assert `out.isascii()` True (positive), labels present.
- growth stages: construct pinned GameStates (NOT factory+overwrite) at start/mid/near/win/loss,
  assert the right glyph appears.
- win_screen/loss_screen: full-string or assert word + "ran out of water" / "thriving".
- e2e win: monkeypatch/seed so secret known (inject rng or patch new_game), script input_fn to
  feed winning letters via a list iterator, capture output_fn into a list, assert final
  win screen text appeared AND return code 0.
- e2e loss: same, feed wrong letters until water 0, assert loss screen + word revealed.
- ascii whole-game: run e2e with --ascii, join all captured output, assert `.isascii()`.
- EOF: input_fn raises EOFError -> assert goodbye + return 0.
- KeyboardInterrupt: same.
- bad flag: assert SystemExit code 2; --help: SystemExit code 0.
- Import message constants from engine (MSG_WIN etc.), do NOT re-type literals.

## Edge cases I'll probe in candidates
- invalid input ("", "ab", "7", "!") re-prompts, no water consumed.
- repeated guess consumes nothing.
- near-win stage actually distinct from progress.
- §18: weeds shown as standalone count, never `n/max_water`.
- main signature exactly `(argv, input_fn, output_fn)`.
