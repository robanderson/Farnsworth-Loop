# Task 002 Review — Word Garden UI, main loop, packaging

Reviewer protocol: blind sketch written first (`blind-sketch.md`), then context
(SPEC.md, .code-tips.md, adopted engine), then anonymized candidates A/B/C,
then empirical verification in detached scratch worktrees at base commit
`61b16c8`. Candidate→worker/model mapping was never inspected.

## Gate results (all run against the base commit, engine read-only)

| Gate | A | B | C |
|---|---|---|---|
| `unittest discover -s tests` | **75 pass** | **66 pass** | — |
| `compileall -q word_garden` | OK | OK | — |
| piped-EOF `python3 -m word_garden` | exit 0, clean goodbye | exit 0, clean goodbye | — |
| engine `game.py`/`words.py` byte-identical | yes | yes | — |

Both A and B pass every mechanical gate. C is an **empty diff (0 bytes)** — a
non-submission. It delivers no `ui.py`, `main.py`, `__main__.py`, tests, or
README, so it cannot be adopted and is excluded from further comparison.

## Behavioural probes (injected I/O, scripted games)

Run via in-process harness with a pinned secret word and a print-compatible
recorder for `output_fn`:

| Probe | A | B |
|---|---|---|
| scripted WIN → win screen + word | PASS | PASS |
| scripted LOSS → loss screen + word | PASS | PASS |
| leading invalid input (`""`,`7`,`!`,`$$`) then win → no water consumed | PASS | PASS |
| `--ascii` whole WIN game pure ASCII (incl. end screen) | PASS | PASS |
| `--ascii` whole LOSS game pure ASCII (incl. end screen) | PASS | PASS |
| `--difficulty easy` → water 8 / `hard` → water 4 in first frame | PASS | PASS |
| `--help` exits 0 / bad `--difficulty` exits 2 | PASS | PASS |
| growth stage changes with progress (**emoji**) | PASS | PASS |
| growth stage changes with progress (**ascii**) | **PASS** | **FAIL — constant `*`** |
| robust to a minimal single-arg `output_fn(text)` | **PASS** | **FAIL — `TypeError`** |

Both candidates are *functionally* complete and playable. The two right-column
failures are the discriminators, detailed below.

---

## Candidate A

Rendered mid-game frame (emoji):

```
🌱 Word Garden

Garden:  🌿  The garden is growing.
Word:    G A R _ _ _
Guessed: A G R
Water:   4/6 💧💧💧💧
Weeds:   2 🌿🌿

Good guess! The garden grows.
```

ASCII mode of the same state renders `Garden:  **  ...`, `Water:   4/6 [****  ]`,
`Weeds:   2 [--]` and is verified pure-ASCII across full win and loss games.

### Strengths

- **Faithful to SPEC §9 element order**: title → dedicated `Garden:` plant/
  status line (growth glyph + friendly label) → masked word → sorted guessed
  letters → water → weeds → previous `status_message` (omitted when empty).
  Every enumerated §9 element is present as its own line.
- **§18 accessibility done correctly in both modes**: water and weeds each
  carry a text label AND an `n/max` (water) / count (weeds) AND symbols —
  never symbols alone.
- **Single source of truth** for growth visuals: one `GROWTH_STAGES` table maps
  each stage → emoji glyph, ASCII glyph, and label; `render`, `win_screen`, and
  `loss_screen` all read from it. ASCII growth stages are *distinct*
  (`*` / `**` / `***` / `\o/` / `x_x`), so progress is legible without emoji —
  the one place B regresses.
- **`growth_stage` uses distinct-letter sets** (`secret_letters - guessed <= 1`
  → near-win), so it is correct for words with repeated letters.
- **Idiomatic I/O contract**: prompt passed to `input_fn(PROMPT)`; `output_fn`
  is only ever called as `output_fn(text)`. Robust to any drop-in `output_fn`.
  `parse_args` is not wrapped in try/except (—help=0, usage error=2 confirmed);
  EOF and KeyboardInterrupt both caught → friendly goodbye → 0.
- **`__main__.py` propagates the return code** (`raise SystemExit(main())`).
- **Exemplary test rigor (75 tests, all deterministic)**: fixtures built by
  constructing `GameState(...)` directly with pinned values (no RNG leak);
  message/glyph/screen constants are imported, never re-typed; the e2e win and
  loss tests **pin the secret word** (`mock.patch word_garden.words.select_word`)
  and **positively assert the specific terminal screen** appeared; ASCII purity
  is asserted with `.isascii()` over whole render AND over both end screens;
  `--help`/usage-error exit codes, EOF, KeyboardInterrupt, and the prompt string
  are all asserted. This matches every relevant entry in `.code-tips.md`.

### Weaknesses

- The growth stage is shown on a `Garden:` line while the title keeps a fixed
  `🌱`; SPEC §5/§9 examples put the stage glyph in the title. This is within
  "exact visual design is flexible" (§10) and arguably *more* faithful to §9's
  separate "plant/garden status" element, but it is a deviation from the
  literal example screen. Cosmetic only.
- ASCII win glyph `\o/` contains a backslash — harmless and ASCII, but slightly
  noisy. Cosmetic.

No correctness defects found in gate-passing code.

---

## Candidate B

Rendered mid-game frame (emoji):

```
🌿 Word Garden

Word:     G A R _ _ _
Guessed:  A G R
Water: 4/6 💧💧💧💧
Weeds: 2 🌿🌿

Good guess! The garden grows.
```

### Strengths

- Source is clean, short, and readable; all message text matches SPEC §6.6/§6.7
  and the masked-word/guessed lines match the §9 example spacing closely.
- §18 satisfied: water/weeds carry label + `n/max`/count + symbols.
- EOF and KeyboardInterrupt both caught → goodbye → 0; `parse_args` not wrapped;
  `--help`=0 and usage error=2 confirmed. Engine untouched. Passes all gates.

### Weaknesses (ordered by severity)

1. **Growth stage is invariant in ASCII mode.** `_GROWTH_ASCII` maps *every*
   stage to `"*"`, so start / progress / near-win all render an identical
   `* Word Garden` title and there is no separate status line. A player in a
   non-emoji terminal — exactly the audience the ASCII fallback exists for —
   gets no growth feedback at all until the win/loss screen. Requirement 2 asks
   for "growth stage per the section 10 table" with the ASCII fallback; B
   honours the table only in emoji mode. (Empirically confirmed: `start` and
   `near-win` ASCII frames are byte-identical above the word line.)

2. **The end-to-end "win" test cannot fail.** `test_end_to_end_with_all_alphabet`
   guesses A–Z against a word chosen by the *global* RNG (no `select_word`
   patch, no injected seed) and asserts
   `count("Bloom!") > 0 OR count("ran out of water") > 0`. Every terminating
   game satisfies one disjunct, so the assertion is tautological — it passed
   40/40 repeated runs precisely *because* it proves nothing. This is the exact
   anti-pattern `.code-tips.md` forbids ("an OR of several acceptable outputs
   proves nothing"; "force a known scenario … positively assert the success
   output appeared"). There is **no test that deterministically asserts a win
   screen**.

3. **`test_invalid_then_valid` derives its scenario from a seeded RNG it then
   discards.** It builds a state with `new_game("normal", rng=Random(42))` to
   read a secret word, but `main([])` starts a *fresh* game on the global RNG,
   so the guesses and the asserted `"Good guess!"` are decoupled from the word
   actually in play. It happens to pass (some guessed letter usually hits), but
   it relies on global-RNG luck rather than a pinned scenario — violating the
   "inject a seeded `random.Random`" and "force a known scenario" tips.

4. **`main` couples `output_fn` to `print`'s signature.** It emits the prompt
   via `output_fn("Guess a letter: ", end="")` and calls `input_fn()` with no
   prompt. Injecting a minimal `output_fn(text)` raises
   `TypeError: unexpected keyword argument 'end'`. The brief specifies
   `output_fn=print`, so this is within the letter of the contract, but it is a
   fragile design: the renderer/loop should not assume the sink accepts `end=`.
   A passes the prompt to `input_fn` and never needs `end`.

5. Minor: emoji title morphs (`🌱`→`🌿`→`🌷`) to carry the stage, conflating
   §9's "title" and "plant status" elements into one line.

B is adoptable-with-fixes, not adoptable-as-is: items 1–3 are real gaps against
the acceptance criteria and the standing test-rigor contract.

---

## Comparative ranking

1. **A** — correct, complete, and faithful to §9/§10/§18 in *both* render modes,
   with deterministic, scenario-pinned, positively-asserting tests that satisfy
   every `.code-tips.md` rule. No defects found.
2. **B** — functional and gate-passing, but ASCII growth-stage feedback is
   missing, its success-path e2e test is vacuous, two tests lean on global-RNG
   luck, and the loop couples `output_fn` to `print`. Usable as a fallback or a
   source of the tidy README, but weaker on rigor and accessibility.
3. **C** — empty diff; non-submission.

## Decision

**ADOPT A.** It meets every acceptance criterion empirically, is correct and
complete as-is, and upholds the project's accumulated test-rigor and design
contracts better than B. No synthesis is needed — A requires no changes; B's
only clear edge (a marginally more SPEC-literal sample screen / README prose)
does not outweigh its accessibility and test-rigor gaps, and is not worth
forfeiting A's correctness to merge.
