# Review — task-002 (Word Garden UI)

Reviewer workspace: /home/user/wg2. Scratch verification in /tmp/review-002/{A,B,C}
(base 929ebe7 + each diff). All three: unittest green (A 70, B 80, C 61),
`compileall` green, engine `game.py`/`words.py` byte-identical to base, ui.py
genuinely I/O-free (A's grep hit was a docstring).

## Empirical probes (all three PASS unless noted)

- Scripted full game via `main(input_fn=, output_fn=)` for WIN and LOSS: code 0,
  win shows "Bloom!" + word, loss reveals the secret word + "ran out of water".
- `--ascii` output is 100% ASCII over a whole rendered game INCLUDING win and
  loss end screens (`.isascii()` over the full transcript). PASS all.
- Emoji mode is NOT all-ASCII over a whole game. PASS all.
- Invalid input ("apple","7","!","") does not consume water or add weeds
  (asserted `remaining_water` unchanged). PASS all.
- §18: weeds rendered as a standalone count ("Weeds: 2 ...") NOT a fraction of
  water; water carries the "4/6" fraction + label + symbols. PASS all.
- §9 display order title -> Word -> Guessed -> Water -> Weeds -> status. PASS all.
- Repeated-letter word (LEVEL) wins correctly. PASS all.
- EOF (Ctrl-D) and KeyboardInterrupt (Ctrl-C): clean exit 0 with a friendly
  message, no traceback. PASS all.
- argparse: `--help` exits 0 (all). Bad `--difficulty`/unknown flag exits 2 for
  B and C; **A exits 0 — DEFECT** (see below).

## Candidate A

GOOD: clear render with stage glyph folded into the TITLE line (🌱→🌿→🌷, a valid
§10 layout); correct §18 water-fraction + weeds-count; thorough README; handles
EOF and Ctrl-C; most tests by structure count.

BAD: **Real defect** — `main()` wraps `parser.parse_args()` in
`try/except SystemExit: return 0`, so a usage error (bad `--difficulty`, unknown
flag) exits 0 instead of argparse's 2, swallowing the error signal the task asks
for. Weakest tests: `test_main_win_scenario` never forces a known word and only
asserts `code==0 and ("Bloom!" or "ran out" or "Goodbye")` — it does not prove a
win path. No MSG_* reuse (tests hardcode engine strings). No emoji-non-ASCII
negative assertion. No dedicated `growth_stage` function (stage only observable
via render substrings). ASCII win/loss headers both use `*` (cosmetic).

## Candidate B

GOOD: argparse correct (usage error -> 2). Clean `_STAGE_EMOJI`/`_STAGE_ASCII`
glyph dicts and a `_growth_stage` helper using unique-letter fraction (0.75
near-win threshold); separate `Plant:` line carries the stage glyph; §18 correct;
deterministic monkeypatched win/loss tests; ASCII purity asserted per-char.

BAD: title glyph is hardcoded to `glyphs['start']` (always 🌱) regardless of
stage — the stage shows only on the Plant line. `test_scripted_win_shows_win_
screen` is effectively a no-op (comment admits it cannot guarantee the word; only
asserts code 0). No MSG_* reuse (tests + screens use literals). `_growth_stage`
is private (tested only via render substrings, not directly).

## Candidate C  (ADOPT)

GOOD: public `growth_stage(state)` unit-tested DIRECTLY across start/progress/
near-win/win/loss AND the win-beats-loss-at-zero-water invariant; reuses engine
`game.is_won`/`is_lost` rather than re-deriving from water (honors task-001
invariant). Only candidate to honor the MSG_* contract — tests assert against
`game.MSG_CORRECT`/`MSG_WRONG` and a shared `GOODBYE` constant imported from
main, not re-typed strings. Emoji glyphs are `\U....` escapes so the source file
itself is ASCII-safe (no stray literal emoji to leak). Combined
`except (EOFError, KeyboardInterrupt)` handler. `NoIoInUiTest` asserts ui source
has no `print(`/`input(`. Positive `remaining_water == 6` assertion in the
invalid-input test. Captioned Plant line ("Plant: 🌿 Your garden is growing.")
is the most accessible §18 rendering. argparse correct (usage -> 2).

BAD: fewest tests (61) — though highest per-test rigor; no per-stage ASCII-glyph
assertion in render (covered indirectly by whole-game purity). Minor.

## Decision

Adopt C. No correctness defect found in C; it best satisfies the spec and the
.code-tips.md contracts. A's swallowed-SystemExit is a genuine bug; B is correct
but less rigorous and ignores the MSG_* tip. Synthesis is unnecessary — at most,
backfill C with a few of B's render-substring tests, which is optional polish.
