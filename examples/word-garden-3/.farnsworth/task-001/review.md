# Review — task-001 (Word Garden core engine)

Method: each candidate diff applied to a pristine base checkout of
`/home/user/wg3-review`; ran `python3 -m unittest discover -s tests`,
`compileall`, a strict UI-purity grep, and a 31-assertion reviewer probe
(`/home/user/wg3-review-out/probe.py`) exercising edge cases the suites might
miss. All five pass the mechanical gate. The probe found one real defect.

## Acceptance-criterion scorecard

Legend: Y = met, n = met but with a caveat, N = defect.

| Criterion | A | B | C | D | E |
|---|---|---|---|---|---|
| unittest green, SPEC-16 covered, positive assertions | Y | Y | Y | Y | Y |
| compileall green | Y | Y | Y | Y | Y |
| No UI (`input`/`print`) in `word_garden/` | Y | Y | Y | Y | Y |
| `GameState` field names exactly per SPEC §12 | Y | Y | Y | Y | Y |
| Wrong guess: water -1, weeds +1, recorded, message | Y | Y | Y | Y | Y |
| Repeat guess: no water/weed change, "already" message | Y | Y | Y | Y | Y |
| Invalid input never mutates state, specific message | Y | Y | Y | Y | Y |
| Win AND loss detected, flags + terminal message set | Y | Y | Y | Y | Y |
| **`is_lost` = water 0 BEFORE win (win precedence)** | **N** | Y | Y | Y | Y |
| Stdlib only, no committed bytecode | Y | Y | Y | Y | Y |
| `select_word` every difficulty + unknown raises | Y | Y | Y | Y | Y |
| Empty-pool path raises `ValueError` (in source) | Y | Y | Y | Y | Y |

All five implement win-before-loss precedence INSIDE `apply_guess`
(`if is_won: ... elif is_lost: ...`), so the live game loop is correct for every
candidate. The divergence is the standalone `is_lost(state)` predicate that
task-002's UI will call directly.

## Per-candidate notes

### A — GOOD / BAD
GOOD: Clean immutable `apply_guess` via `dataclasses.replace`; win checked before
loss in the flow; distinct game-over messages for already-won vs already-lost
(`MSG_ALREADY_WON`/`MSG_ALREADY_LOST`) — the most expressive game-over handling
in the field; constants exported and imported by tests; 47 focused tests with
positive assertions.
BAD / DEFECT: `is_lost(state)` returns `state.remaining_water <= 0` with **no
`and not is_won(state)` guard**. A fully-revealed word at water 0 reports
`is_lost() == True` — a win misclassified as a loss. The task's own wording is
"loss = water at 0 **before that** [the win]"; A drops the "before that." The
bug is masked in `apply_guess` (win is checked first) and A's suite never calls
`is_lost` on a won state, so the gate passed. This is precisely the win-on-last-
unit-of-water hazard. Also minor: `GameState` gives defaults to the first five
fields (spec shows none); harmless since names/order are correct, but it lets a
caller construct a degenerate state.

### B — GOOD / BAD
GOOD: Mutate-in-place model, clearly documented ("Mutates and returns the same
instance"), and tests are written consistently with it (they mutate `state` and
re-read it, never assuming a copy). Adds a `words_for(difficulty)` helper (clean
separation of filtering from selection) with its own tests. Empty-pool and
unknown-difficulty both raise with message-constant provenance; `EMPTY_POOL_MSG`
/`UNKNOWN_DIFFICULTY_MSG` are asserted to be templates. Explicit
`test_win_takes_precedence_over_water_zero` and an end-to-end play-through win.
`is_lost` correctly guards `not is_won`. Richest message set with `{word}`
interpolation on win/loss. Fewest tests (36) but each is dense and combined.
BAD: Win/loss messages are `.format(word=...)` templates — fine, but a downstream
caller MUST remember to format them; the leading-word phrasing ("Bloom! ...") is
embellished beyond SPEC §6.6 sample text (acceptable — spec calls samples
"flexible"). `validate_guess` accepts `None` defensively (returns MSG_EMPTY),
slightly beyond contract but harmless.

### C — GOOD / BAD
GOOD: Largest suite (84), immutable apply_guess (constructs fresh GameState),
win-before-loss precedence, `is_lost` correctly guarded, empty-pool raises.
Has the exact regression test A lacked: `test_is_lost_water_zero_word_complete`
asserts `is_lost` is False on a fully-revealed water-0 state. Wrong-guess water
is clamped with `max(0, ...)` so water never goes negative (defensive). Loss
message interpolates the word; win message (`MSG_WON`) is a fixed positive string.
BAD: Several tests reference `game.MSG_*` rather than importing the names, and a
few use substring assertions (`assertIn("thriving", ...)`) instead of full-string
equality — weaker than A/D/E on message-rot protection, though message constants
ARE referenced. `MSG_INVALID_INPUT` and `MSG_EMPTY_INPUT` are duplicate strings
(harmless). `new_game` does not `.upper()` the word (relies on WORDS already
upper — true today, fragile if WORDS ever gains a lowercase entry).

### D — GOOD / BAD
GOOD: The most rigorous suite (80 tests) with the broadest edge coverage:
explicit immutability tests (`assertIsNot`, original-not-mutated for both correct
and wrong guesses), single-letter-word display, multi-occurrence reveal (BANANA
-> `_ A _ A _ A`), `test_is_lost_false_when_won` (the precedence guard A missed),
win-on-last-water, length-window stress (50 draws per difficulty), and a
`TestMessageConstants` class that formats each template. `is_lost` correctly
guarded. Constants imported by name; win/loss interpolate `{word}`. Clean
immutable apply_guess. `_DIFFICULTY_PARAMS` imported into tests but only lightly
used.
BAD: One test (`test_correct_guess_display_reveals_letter`) builds its expected
string via a convoluted `.replace()` chain — it evaluates correctly but is hard
to read and is dead-weight next to the cleaner `test_partial_guess_shows_correct_
mix`. `MSG_EMPTY_INPUT` and `MSG_MULTIPLE_CHARS` are duplicate strings (harmless).
No forced empty-pool test (shared gap — see below).

### E — GOOD / BAD
GOOD: 58 tests, immutable apply_guess with a small `_all_revealed` helper,
`is_lost` correctly guarded, win-on-last-water predicate test
(`test_is_lost_false_after_win`), multi-occurrence reveal (SEEDLING), single-
letter-word cases, and the field's only **genuine end-to-end win through the real
factory**: `test_new_game_with_seeded_rng_wins` calls `new_game(rng=...)`, guesses
every letter of the actually-selected word, and asserts `won` + the terminal
message (exactly the seed tip's "force a known scenario, assert the artifact").
Constants imported by name; full-string message equality.
BAD / caveat: `MSG_LOSS = "The word was: {word}\nTry again and grow a new garden."`
**drops the "ran out of water" line** from SPEC §6.7's sample. The terminal
message IS set (so the seed-tip contract is honored — not a defect), but it is
the weakest fidelity to the spec's loss text in the field; a UI built on it would
not tell the player WHY they lost without adding its own prefix. `MSG_INVALID_
EMPTY`/`MSG_INVALID_MULTIPLE` duplicate strings (harmless). `new_game` lacks a
type hint on `rng` (cosmetic).

## Defects found (gate-passing code) — PRIMARY LEARNING METRIC

1. **Candidate A — `is_lost` misclassifies a win as a loss.**
   `is_lost(state)` returns `remaining_water <= 0` without `and not is_won(state)`.
   A state with the word fully revealed and water at 0 returns
   `is_lost() == True`. Confirmed empirically:
   `is_won == True` and `is_lost == True` simultaneously for
   `GameState('GO', {'G','O'}, remaining_water=0, ..., won=True)`.
   Severity: real contract violation. The task defines loss as "water at 0
   **before** [the win]". Masked in `apply_guess` (win checked first) and by an
   absent test, so it passed the mechanical gate. This is the win-on-last-unit-
   of-water hazard the blind sketch flagged. **B, C, D, E all guard correctly.**

Total real defects in gate-passing candidates: **1** (Candidate A).

No other candidate exhibited a behavioral defect under the probe (all 31 probe
assertions passed for B/C/D/E; A failed exactly `is_lost_false_when_won_water0`).

## Test-rigor assessment

- **D** is the most rigorous overall (immutability, single-letter, multi-
  occurrence, precedence, length-window stress, message-template formatting).
- **E** has the single best test in the field: a true end-to-end win driven
  through `new_game` + the real rng + the real `apply_guess`, asserting the win
  artifact — the strongest realization of seed tip #3.
- **C** is broad (84) but leans on a few substring assertions and `game.MSG_*`
  references rather than imported names — slightly weaker rot protection.
- **B** is the leanest (36) yet still covers precedence and an end-to-end win;
  its `words_for` split is the cleanest factoring and its message constants are
  the best-guarded against rot.
- **A** is solid but has the field's only coverage gap that mattered: it never
  exercises `is_lost` on a won state, which is exactly where its bug lives. A
  textbook case of seed tip #2 (assert the positive precedence, not just the
  negative) catching nothing because the test was never written.
- **Shared gap (all five):** none force the empty-pool branch (e.g. temporarily
  shrinking `WORDS`); they only assert the `ValueError` for *unknown difficulty*
  or that the empty-pool message constant exists. The empty-pool raise IS in
  every candidate's source and the reviewer probe confirms it fires, but no
  candidate's own suite would catch a regression that removed it. Worth a tip.

## Seed-tip audit (key experiment data — labels only)

Nine seed entries. For each: did the field honor it?

1. **Terminal action updates message, not just flags** ("flags right, message
   wrong"). HONORED by all five in `apply_guess` (win/loss set
   `status_message`), and B/C/D/E assert the terminal message in tests; A asserts
   it too (`MSG_WIN`/`MSG_LOSS`). **Universally honored.** (Note: this seed is
   about the *message*; A's bug is in the separate `is_lost` predicate, not a
   message regression — so the seed itself held.)
2. **Assert the POSITIVE outcome, combined.** HONORED by all five; A/B/D/E use
   explicit combined assertions (water AND weeds AND letter AND message), C
   mostly so. **Universally honored** — though A shows the limit: a positive
   assertion you never write catches nothing.
3. **End-to-end success path forces a known scenario, asserts the artifact.**
   E does this through the real factory (best). B does a play-through on a pinned
   state. C/D drive multi-guess sequences to a win. A asserts win flags+message
   on a pinned near-win. **Universally honored**, strongest in E.
4. **Do NOT wrap `argparse.parse_args` in try/except SystemExit.** Not applicable
   — no argparse/CLI in this task (UI is task-002). **N/A this round** (no
   candidate violated; none had reason to touch it).
5. **Select/filter from a pool MUST raise on empty/unknown; never silent
   fallback.** HONORED by all five: unknown difficulty raises `ValueError` and
   the empty-pool branch raises (verified by probe). **Universally honored** in
   source. Partial on tests: all cover the unknown-difficulty raise; none force
   the empty-pool raise.
6. **All randomness injectable; `rng=None` -> module `random` (not a fresh seeded
   Random); logic terminal-free.** HONORED by all five: `select_word(rng=None)`
   uses `random.choice`, tests inject `random.Random(seed)`. **Universally
   honored.**
7. **Define user-facing strings ONCE as module-level constants, import
   everywhere.** HONORED by all five (constants defined in `game.py`/`words.py`).
   B/D/E import by name in tests (strongest); A imports by name; C references
   `game.MSG_*` attributes (still single-source, slightly looser). **Universally
   honored**, with C marginally weaker.
8. **Build fixtures by constructing the state object directly with pinned
   values; do not call the factory then overwrite.** HONORED by B/D/E (explicit
   `_make_state`/`_state`/`make_state` helpers, called out in comments) and A/C
   (construct `GameState(...)` inline). **Universally honored.**
9. **Hygiene: never write/commit `.code-tips.md`; never commit bytecode; don't
   modify `SPEC.md`/`farnsworth.json`/`tasks/`.** HONORED by all five (gate
   notes report hygiene clean; diffs touch only `word_garden/` and `tests/`).
   **Universally honored.**

**Headline:** Of 9 seed entries, **7 universally honored** (1, 2, 3, 5, 6, 7, 8,
9 — eight if you count #9; see below), **1 partially honored** (#5 honored in
source by all, but no candidate's own suite forces the empty-pool branch), and
**1 not applicable this round** (#4, argparse — no CLI in task-001). **Zero
violated.** Precise count: entries 1, 2, 3, 6, 7, 8, 9 = 7 fully universal;
entry 5 = partial (source-universal, test-incomplete); entry 4 = N/A. The seed's
first cross-project trial is a success: every applicable durable lesson was
followed by every worker, and the lessons demonstrably shaped the suites
(precedence tests in B/C/D/E, end-to-end win in E, pinned fixtures everywhere).
The one defect that shipped (A's `is_lost`) is NOT a seed-tip violation — it is a
NEW lesson this round teaches (see code-tips).

## Comparative conclusion

A is eliminated by a real defect. Among B/C/D/E (all behaviorally correct on the
probe), the decision is about completeness and downstream ergonomics:

- **D** has the most rigorous and readable test suite and clean immutable source;
  it covers every edge that mattered including the precedence guard A missed.
- **E** has the best end-to-end win test but the weakest spec fidelity in its
  loss message (drops "ran out of water").
- **C** is broad but leans on substring/attribute assertions.
- **B** is the leanest and best-factored (`words_for`) with the best message
  hygiene, but fewest edges.

**D is the strongest single candidate**: correct on every probe, the richest and
cleanest test rigor, immutable transitions, spec-faithful messages with `{word}`
interpolation, and it explicitly tests the exact precedence case that sank A.
Verdict: adopt D.
