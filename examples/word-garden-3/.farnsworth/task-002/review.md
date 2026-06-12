# Review — task-002 (UI / main loop / packaging)

Empirical: each diff applied to the clean d8482866 checkout, reverted fully
between candidates. Engine files byte-identical for all three. All suites
green (A 105, B 145, C 119). All exercised beyond their own tests (scripted
win/loss, whole-game `--ascii` `.isascii()`, emoji-not-ascii, five growth
stages, invalid/repeat no-water, argparse exit codes, EOF + KeyboardInterrupt).

Engine reminder (read-only contract): `MSG_WIN`/`MSG_LOSS` are single-line
status-message strings; SPEC §6.6/6.7 want a multi-line *screen*. So writing
fresh screen text in ui.py is correct; the live tip is "define YOUR screen
strings once as named constants and import them in tests."

---

## Candidate A

Scorecard vs acceptance criteria — all PASS:
- unittest green (105), compileall green, engine byte-identical. PASS.
- Full game playable; `--ascii` pure ASCII (verified `.isascii()` over a
  whole game incl. win + loss screens); `--difficulty` changes water/pool. PASS.
- Invalid input ("", "ab", "7", "!") re-prompts, no water consumed; repeated
  guess consumes nothing (verified: one wrong -> 5/6, repeat stays 5/6). PASS.
- Win screen shows the word; loss screen reveals word AND keeps "ran out of
  water" sense (`LOSS_HEADER`). PASS.
- EOF and Ctrl-C: friendly `GOODBYE`, code 0, no traceback. PASS.
- ui.py zero I/O (all functions return str); main.py only I/O module. PASS.
- SPEC §9 order correct; §18 water `4/6 💧…`, weeds standalone `2 🌿…`
  (NEVER n/max). PASS.

Good:
- Cleanest separation: `_play` helper, `_build_parser`, `_final_screen`.
  Readable and maintainable.
- Growth stage driven by *fraction of distinct letters revealed*; five
  observable stages with five distinct glyphs (🌱🌿🌷🌻🥀) — verified.
- Named constants for every label, header, glyph table, prompt, and
  `GOODBYE`; tests import them (`ui.TITLE`, `ui.WIN_HEADER`, `game.MSG_*`,
  `main.GOODBYE`). Strongest constants-discipline in the field.
- Tests assert glyph *counts* (`out.count(WATER_GLYPH) == 4`) — positive,
  not negative.
- e2e win/loss via injected I/O + monkeypatched `new_game`, asserting the
  actual win/loss artifact appeared (honors the seed e2e tip). Invalid-input
  e2e asserts `6/6` survived (water untouched) AND a win still reached.

Bad / nits:
- `main(argv=None, *, input_fn=input, output_fn=print)` — the `*` makes
  input_fn/output_fn **keyword-only**. The brief's required signature has
  them positional-or-keyword. Benign in practice (every caller uses kwargs)
  but a literal deviation from a REQUIRED signature; minor deduction.
- One re-typed literal: `assertIn("You guessed the word: GO", out)` — A has
  no constant for that win body line (it's an inline f-string in ui.py).
  Small lapse; the header/word are still constant-checked elsewhere.
- e2e tests reassign `game.new_game` directly rather than via an injection
  point (works, but mutates a module global in try/finally).

## Candidate B

Scorecard — all functional criteria PASS (verified win/loss/ascii/stages/
invalid/repeat/argparse/EOF/KI), with one signature concern:
- **Signature deviation (the notable one):** `main(argv=None, input_fn=input,
  output_fn=print, new_game_fn=None)`. The brief marks
  `main(argv, input_fn, output_fn) -> int` REQUIRED. `new_game_fn` is an
  extra parameter. Judgment: this is a **contract deviation, not a benign
  extension**, because B's own e2e suite *depends* on it — the tests call
  `main(..., new_game_fn=fixed_new_game)`. A clean alternative existed
  (inject `rng`, or monkeypatch `select_word`, as C does) that needs no
  signature change. Adding API surface that only the tests consume is the
  kind of drift the "required signature" line guards against. Costs B.
- Extra `try/except ValueError -> output + return 1` around `new_game`.
  Unspecified behavior (brief only enumerates win/loss/EOF/KI -> 0). Harmless
  and arguably nice, but it is invented contract; the empty-pool raise is
  unreachable with shipped WORDS anyway.

Good:
- Most thorough suite (145). Win, loss, ascii-final, longer-word win, invalid
  -> still-win, water-not-consumed-under-water=1, EOF + KI, all positive.
- Best constants *infrastructure* in source: `WIN_LINE2`/`LOSS_LINE2`/
  `WIN_HEADER`/`LOSS_HEADER`/`MSG_GOODBYE`, asserted via
  `WIN_LINE2.format(word=...)` — exactly the rot-guard the tips want.
- §18 correct: water `n/max`, weeds standalone count. §9 order correct.
- Growth: ratio `>= 2/3` -> near_win; five distinct stages verified.
- ASCII weeds-zero handled (`Weeds: 0`, no empty bracket).

Bad / nits:
- Two re-typed engine literals: `assertIn("Good guess! The garden grows.")`
  and `assertIn("No match. A weed appears.")` — both exist as
  `game.MSG_CORRECT_GUESS` / `MSG_WRONG_GUESS` and should have been imported.
- e2e tests build fixtures from `_state(secret_word="GO"/"CAT"/"AB")` (words
  outside the pool). Fine because fully injected, but slightly less faithful
  than forcing a real pool word.
- Ascii title uses `[~] Word Garden` (bracketed glyph) — cosmetic, fine.

## Candidate C

Scorecard — all functional criteria PASS (verified win/loss/ascii/stages/
invalid/repeat/argparse/EOF/KI):
- **Best signature compliance:** `main(argv=None, input_fn=input,
  output_fn=print) -> int` — exactly the brief. No extra params.
- §9 order correct; §18 water `4/6 💧…`, weeds standalone `2 🌿…`. PASS.
- `--ascii` whole game pure ASCII incl. screens (verified). PASS.
- Five distinct growth stages (near-win via `remaining <= max(1, total//4)`).
- EOF/KI -> "Thanks for playing!", code 0. argparse exit codes correct.

Good:
- Honors the required signature most faithfully.
- A `TestMainRenderingOrder` test asserts §9 field ordering by position —
  nice explicit coverage no other candidate has.
- Two forced-word e2e wins (GARDEN, FLOWER) via monkeypatched
  `words.select_word` — uses real pool words, reaches an actual win.

Bad / nits (the field's heaviest tips violation):
- **No named message constants anywhere in C's own source.** ui.py win/loss
  screen lines ("Bloom!", "You guessed the word:", "The garden ran out of
  water.", "Try again…") are inline literals; main.py's goodbye is the inline
  `"\nThanks for playing!"`. Directly violates "define user-facing strings
  ONCE as named module-level constants."
- **Tests assert by re-typed substring literals**, even though C *imports*
  `MSG_CORRECT_GUESS`, `MSG_WIN`, etc.: `assertIn("Bloom!")`,
  `assertIn("ran out of water")`, `assertIn("thriving")`, `assertIn("Thanks
  for playing")`, `assertIn("That is not a letter")`. Imported constants are
  imported and then ignored. Violates both the "import don't retype" tip and
  the "full-string equality, not substring" style tip. This is the silent-rot
  shape the tips exist to prevent.
- `_growth_stage` returns a `(emoji, ascii)` tuple instead of a stage name;
  works but couples the two representations and is the least clean of the
  three. The "loss" branch in render relies on `is_lost`; the final-screen
  dispatch uses `if is_won: … elif is_lost: …` — safe given engine
  invariants (a game_over+not-won state always has water<=0 -> is_lost True),
  but it is the one place a future engine change could silently print no
  final screen; A and B branch on `state.won` directly, which cannot.
- Loss e2e (`TestMainEndToEndLoss`) accepts ANY of the ten pool words via an
  `any(...)` membership test rather than forcing a known word — weaker than
  C's own forced-word win tests, and exactly the "didn't pin the scenario"
  shape the e2e tip warns about (it still reaches a real loss, so it is not a
  false pass, just under-pinned).
- Ascii weeds-zero renders `Weeds:    0 []` (empty brackets) — cosmetic.

---

## Defects found in gate-passing code (primary learning metric)

No correctness defects (wrong water/weed math, swallowed SystemExit, n/max
weeds, non-ascii leak in ascii mode, missed win/loss artifact) were found in
ANY candidate. All three are functionally correct. The differentiators are
contract-faithfulness and test-rigor, not bugs. Specifically:

1. **B — signature contract deviation (real defect against the brief):**
   `main` carries an extra `new_game_fn` parameter that the brief's REQUIRED
   signature does not include, and B's tests *depend* on it. Not a runtime
   bug, but a deviation from an explicitly-required interface where a
   no-signature-change path existed.
2. **C — constants/rot-guard violation (real tips defect):** zero named
   message constants in C's own source; tests assert re-typed substring
   literals despite importing the constants. High silent-rot risk.

(B's extra `return 1` on ValueError is unspecified-but-benign, not counted as
a defect.)

## Test-rigor assessment

- A: strong. Positive assertions, glyph counts, forced e2e win/loss asserting
  the artifact, invalid-input keeps `6/6`. Minor: one re-typed win-body line;
  fixtures via `game.new_game` reassignment.
- B: broadest coverage and best constant-based screen assertions, but two
  re-typed engine literals and fixtures on non-pool words.
- C: has a unique §9-order positional test, but leans on substring literals
  throughout and an under-pinned `any(...)` loss test. Weakest rot-resistance.

## Tips-compliance audit (23 entries) — by candidate

Honored by ALL three: end-of-process message asserted (win/loss screens
reach the artifact); e2e forces a known scenario and asserts the artifact;
`argparse.parse_args` NOT wrapped in try/except SystemExit (verified --help=0,
bad flag=2); I/O injectable via input_fn/output_fn and tests use them; pinned
fixtures built directly (A/B/C all construct GameState, not factory+overwrite);
hygiene (no bytecode, no .code-tips.md, engine untouched); is_lost/is_won
precedence is engine-owned and untouched; loss text retains "ran out of water";
difficulty single-source table is engine-owned and untouched.

Violations:
- **Constants — "define once, import everywhere; full-string equality not
  substring":** VIOLATED by **C** (no source constants + substring literals
  in tests). PARTIALLY by **B** (two engine literals re-typed) and **A** (one
  win-body line re-typed). A is cleanest, C is worst.
- **Required signature contract (project Testing tip lists the task-002
  signatures; brief restates `main(argv,input_fn,output_fn)`):** VIOLATED by
  **B** (`new_game_fn` added) and, mildly, by **A** (`*` makes the two I/O
  params keyword-only). **C** fully compliant.

## Comparative conclusion

All three are shippable and bug-free. The decision rides on the round's
diversified focuses against the brief:
- **C** nails the required signature but is the worst on the readability/
  maintainability AND test-rigor axes precisely where the tips are explicit
  (no named constants, substring-literal tests, under-pinned loss e2e). Two
  named-tip violations.
- **B** has the best test breadth and the best screen-constant infrastructure,
  but pays for it with a signature the brief marked REQUIRED — and the
  extension exists only to serve its own tests, the exact drift the contract
  guards against.
- **A** is the most balanced: faithful display contracts (§9/§10/§18),
  five-stage growth, thorough constants discipline, positive count-based and
  forced-scenario tests, cleanest structure. Its only blemishes are the
  keyword-only `*` (cosmetic, every caller already uses kwargs) and a single
  re-typed win-body line — strictly smaller than B's signature drift or C's
  constants violation.

Winner: **A**.
