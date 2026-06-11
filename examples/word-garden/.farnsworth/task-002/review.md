# Task-002 Review (UI, main loop, packaging)

## Blind sketch (written before reading candidates)

### Module layout
- `word_garden/ui.py` — pure, no I/O. `render`, `win_screen`, `loss_screen`, plus
  small private helpers (`_growth_stage`, `_water_line`, `_weeds_line`). Reuse the
  engine `MSG_*` constants and `display_word` rather than re-deriving strings.
- `word_garden/main.py` — only I/O module. `main(argv=None, *, input_fn=input,
  output_fn=print) -> int`.
- `word_garden/__main__.py` — `from .main import main; raise SystemExit(main())`.
- `tests/test_ui.py` — render (both modes), stages, screens, e2e win+loss.
- `README.md`.

### Growth-stage logic (SPEC §10, driven by progress)
Map a single state -> stage glyph, in priority order:
1. win -> 🌻 / ASCII fallback
2. loss -> 🥀
3. near-win: word almost revealed (e.g. <=1 or <=2 unrevealed letters) -> 🌷
4. progress: at least one correct guess made -> 🌿
5. start: no guesses yet -> 🌱
ASCII fallback for plant: `*` (per §10), water `[******]`, weeds `[---]`.

### render structure (SPEC §9 order)
title; blank; plant/garden status line; Word: <display_word>; Guessed: <sorted,
space-joined>; Water: `N/max` + symbols (label+count ALWAYS, §18); Weeds: `N` +
symbols; blank; previous status_message (if any). The prompt itself belongs to
main.py (render returns the board; main prints prompt). Accessibility: never
symbols-only — `Water:  4/6 💧💧💧💧`. ASCII output must contain zero non-ASCII.

### win/loss screens (§6.6/6.7)
- win_screen: `🌻 Bloom!` + `You guessed the word: WORD` + thriving message.
- loss_screen: `🥀 The garden ran out of water.` + `The word was: WORD` +
  try-again message. MUST reveal secret word.
- ASCII variants swap glyphs for ASCII.

### main-loop shape
parse args (argparse: `--difficulty {easy,normal,hard}` default normal, `--ascii`).
`state = new_game(difficulty)`; loop while not state.game_over: output(render);
read via input_fn(prompt); validate_guess; if invalid -> output(message), continue
(no turn consumed); else state = apply_guess(state, letter). After loop: output
win_screen or loss_screen; return 0. Wrap input in try/except EOFError &
KeyboardInterrupt -> friendly goodbye, return 0, no traceback. Use returned value
of apply_guess (round-1 tip: do not assume in-place).

### test plan
- render emoji: asserts "Water:" + "4/6" + a 💧 present (positive).
- render ascii: assert output.isascii() True; contains labels+counts.
- stages: build GameState directly (round-1 tip — no new_game-then-overwrite) at
  start/mid/near-win/win/loss, assert the right glyph.
- win_screen/loss_screen: assert secret word present; ascii pure.
- e2e: main(argv=[], input_fn=scripted, output_fn=collector) with a seeded/forced
  word — drive a win sequence and a loss sequence, assert final screen text in
  captured output. Also test invalid input does not consume water (count outputs
  or check no extra weed). Test EOF -> returns 0.

## Candidate reviews (after empirical verification)

All three: gate green (A 80 / B 55 / C 56 tests; compileall clean), ui.py has
zero `print()`/`input()`, main.py is the only I/O module, exact file set added,
engine/SPEC/farnsworth untouched, both modes run a full game, `--ascii` output
verified pure-ASCII across start/progress/near-win/win/loss + both screens, and
`--difficulty` changes water (easy 8 / normal 6 / hard 4). EOF and Ctrl-C exit
cleanly with a friendly goodbye, code 0. Differences below.

### Candidate A — GOOD
- Clean separation; named `_STAGES_EMOJI`/`_STAGES_ASCII` dicts; `_GOODBYE`
  constant. argparse delegated correctly: `--help` exits 0, bad `--difficulty`
  exits 2 (standard CLI contract). Largest, most granular suite (80) with
  positive assertions, per-character ASCII-purity checks, a distinct e2e win,
  loss, EOF, invalid-input-doesn't-consume-turn, and ascii-e2e test.
- ASCII stages are all DISTINCT (`[.] [*] [+] [#] [x]`) — the §10 stage table
  is faithfully representable in ASCII mode, the best of the three on that axis.
- Sample rendered screen (emoji, mid-game):
  ```
  🌱 Word Garden

  🌿

  Word:     G A R D E _
  Guessed:  A D E G R Z
  Water:  5/6 💧💧💧💧💧
  Weeds:  1 🌿
  ```
- BAD / watch:
  - The TITLE glyph is hard-coded `🌱` and never changes; the actual growth
    stage is shown on a SEPARATE bare-glyph line below it. So the seedling in
    the title is decorative/misleading once the garden has grown, and the stage
    line carries NO text label (only B's title-merge avoids the redundancy; C's
    `Garden:` line adds the missing text label). The bare stage glyph is the one
    spot where A leans on a symbol without an accompanying word (§18 spirit) —
    water/weeds themselves are correctly labelled+counted.
  - `Weeds:  0 ` (and `Guessed:  ` at start) emit a trailing space — cosmetic.
  - e2e tests monkeypatch `wgm.new_game` (module attribute) rather than seeding;
    works and is restored in `finally`, but heavier than C/B's approach.

### Candidate B — GOOD (with a CLI defect)
- Cleanest growth-stage presentation: the stage glyph IS the title prefix
  (`🌿 Word Garden`), no redundant second line. Minimal, readable render.
  Richest README (full example game transcript). 55 tests, positive assertions,
  explicit EOF + KeyboardInterrupt + invalid-input tests, accessibility class.
- BAD (real defect): wraps `parser.parse_args` in `try/except SystemExit:
  return 1`. This breaks the CLI contract — `--help` exits 1 (should be 0) and
  a bad `--difficulty` exits 1 (should be argparse's 2). Verified empirically.
  A and C both get this right by not swallowing SystemExit.
- BAD (accessibility): in ASCII mode EVERY growth stage renders the same `*`
  (start/progress/near-win/win/loss are indistinguishable), and the loss/win
  screens also use `*` rather than a distinct marker. The §10 stage information
  is effectively LOST in ASCII mode with no compensating text label. This is the
  weakest §10/§18 story of the three.
- Watch: near-win threshold 0.66 is fine but its test comments say "66%+";
  trailing space on `Weeds:     0 `; imports `StringIO` unused in the test file.

### Candidate C — GOOD (strongest accessibility)
- Best §18 story: a dedicated `Garden: <glyph>  <text label>` line means the
  growth stage ALWAYS carries words ("Almost in bloom!", "The garden has
  wilted.") regardless of emoji/ASCII — the only candidate where stage info
  survives ASCII mode in human-readable form. ASCII loss marker `x` is distinct
  from the `*` used elsewhere. `growth_stage` is a public, directly-tested
  helper (missing<=2 => near-win). Cleanest main.py (split `_parse_args`/`_play`,
  keyword-only injected I/O, `PROMPT`/`GOODBYE` constants). argparse delegated
  correctly (help 0, bad-diff 2).
- Sample rendered screen (emoji, mid-game):
  ```
  🌱 Word Garden

  Garden: 🌷  Almost in bloom!

  Word:     G A R D E _
  Guessed:  A D E G R Z
  Water:  4/6  💧💧💧💧
  Weeds:  2/6  🌿🌿
  ```
- 56 tests: positive assertions, a POSITIVE emoji-has-non-ASCII assertion
  (nice — proves emoji mode actually uses glyphs), e2e win/loss/EOF, invalid-
  input-doesn't-consume-water under `--ascii` (also asserts whole run is ASCII).
  Direct `GameState(...)` fixtures via `_state` helper (round-1 tip honoured).
- BAD / watch:
  - Weeds meter denominator is `max_water` (`Weeds:  2/6`): weeds are NOT bounded
    by water, so "2/6" is a conceptually wrong fraction (weeds can exceed... no,
    they can't exceed max_water in practice since each weed costs a water, but
    the SHARED denominator still misrepresents weeds as "out of water"). §18's
    example is `Weeds: 2 🌿🌿` (a bare count) — A and B use a bare count, C
    over-formats it. Minor but the only spec-fidelity nit on the weeds line.
  - Title glyph hard-coded `🌱` / `* Word Garden *`; mildly redundant with the
    Garden line, but harmless since the Garden line is the real stage indicator.
  - test docstring in `test_end_to_end_win` is a long stream-of-consciousness
    comment block — the test itself is clean (monkeypatches `new_game`).

## Verdict

**adopt — Candidate A.**

A is the most complete and defensible UI base: the most rigorous test suite
(80, all positive, e2e win/loss/EOF/invalid-input/ascii, per-character purity),
correct CLI exit codes (`--help` 0, usage error 2), and the only candidate whose
§10 growth-stage table survives ASCII mode as five distinct glyphs. Its water and
weeds lines follow §18 exactly (text label + count, bare weed count). Its
shortcomings are cosmetic — a static decorative title seedling, a bare unlabelled
stage glyph line, and a couple of trailing spaces — none of them spec or contract
violations.

**Runners-up:**
- **C** — very close. Best accessibility of the field: a `Garden: <glyph> <text
  label>` line keeps the growth stage human-readable in both emoji and ASCII
  mode, plus a distinct ASCII loss marker and the cleanest `main.py`. Held just
  below A by its `Weeds: N/max_water` mis-formatting (weeds aren't a fraction of
  water; §18's example is a bare count) and a slightly redundant title glyph. If
  per-stage text labels are later wanted, graft C's `Garden:` line onto A.
- **B** — third. Cleanest single-glyph title, richest README, but two real
  defects: it swallows argparse `SystemExit` (so `--help` and usage errors exit
  1 instead of 0/2), and its ASCII mode collapses all five growth stages and both
  end screens to a single `*`, discarding §10 stage information with no text
  fallback — the weakest §10/§18 story.
