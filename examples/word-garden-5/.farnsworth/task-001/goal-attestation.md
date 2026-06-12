# Task-001 Goal Attestation — Semantic Half

Reviewer attestation of the MERGED state on `main` (post-verdict: adopt).
Each GOAL.md "Done — semantic half" bullet verified empirically against the
merged tree: full suite run (88 tests, OK), modules probed directly with
`python3 -c`, and scripted win/loss sessions driven through the real CLI
(`python3 -m word_garden`) with words pinned via `select_word`.

## Semantic-half bullets

- **All ten SPEC §16 cases covered with positive assertions** — MET: each
  case maps to a positive-assertion test — (1) `TestCorrectGuess`, (2)
  `test_water_decreases_by_exactly_one`, (3)
  `test_weed_count_increases_by_exactly_one`, (4) `TestRepeatedGuess`, (5)
  `TestValidateGuess` (empty/multiple/digit/symbol), (6)
  `test_lowercase_normalised`, (7) `TestWinCondition`, (8)
  `TestLossCondition`, (9) `TestDisplayWord`, (10) `test_words.py::TestSelectWord`.

- **Full session: random word, masking, one-letter guesses, validation,
  guessed tracking, water/weed accounting, win/loss detection with spec end
  screens, clean exit** — MET: a pinned-CAT CLI win session revealed letters
  turn by turn, ended on "🌻 Bloom! / You guessed the word: CAT / The garden
  is thriving." exit 0; a pinned-CAT 6-wrong-guess session decremented water
  6→0 and weeds 0→6, ended on "🥀 The garden ran out of water. / The word was:
  CAT / Try again..." exit 0; invalid ("7") and repeated guesses cost no water.

- **§18 accessibility: text labels + numeric counts alongside symbols;
  `--ascii` makes entire output ASCII** — MET: render shows `Water: 4/6 💧💧💧💧`
  and `Weeds: 2 🌿🌿` with the Word/Guessed/Water/Weeds labels always present;
  whole `--ascii` win and loss sessions contained zero non-ASCII chars
  (`ord(c)>127` set empty).

- **§10 five growth stages observable and distinct** — MET: `_growth_glyph`
  yields five distinct glyphs in both modes — emoji 🌱/🌿/🌷/🌻/🥀 and ASCII
  `*`/`+`/`^`/`@`/`x`; start→progress→near-win transitions are visible in the
  live CLI title line, and win/loss screens carry their dedicated titles.

- **Difficulty selection per §7 table (`--difficulty easy|normal|hard`,
  default normal)** — MET: water is 8/6/4 and length windows are easy 4–6
  (pool len 6), normal 5–8 (lens 6–8), hard 7+ (lens 7–8); `--difficulty`
  defaults to normal and the flag is accepted by the CLI.

- **No criterion met by accident of the word list (forced-scenario tests pin
  words)** — MET: `test_main.py` pins CAT/IT via `_pin_word` for win, loss,
  invalid-input, and repeated-guess paths; engine tests construct GameState
  directly with pinned secrets, so win/loss paths never rely on randomness.

## Residual gaps

None blocking. Minor, non-blocking observation: on the rendered win/loss
*screens* the dedicated end-screen titles are used (🌻/🥀 emoji, "Bloom!" /
text in ASCII), so the `@`/`x` win/loss values from `_growth_glyph` surface
only via the glyph function and the in-game title line, not on the final
screen — this is by design (dedicated end screens) and the five stages remain
observable and distinct. No further loop iteration required.

ATTESTATION: GOAL MET
