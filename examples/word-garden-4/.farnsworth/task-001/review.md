# Review — Task 001 (Word Garden core)

All five candidates **pass both gates** in a clean worktree at base `712c2a9`:
`python3 -m unittest discover -s tests` green and `python3 -m compileall -q
word_garden` green. None call `input()`/`print()` and none import beyond the
stdlib (verified by reading the full new files in each diff). So the mechanical
gate does not separate them — the differences are in spec faithfulness, the
end-of-game `status_message`, DRY of the difficulty table, and test hygiene.

Test counts: A=46, B=51, C=49, D=31, E=50 — all green.

## Empirical probe (identical script run against each worktree)

The discriminating finding is the **status_message on a winning / losing
guess**. SPEC §6.6/6.7 specify distinct end-of-game text (a "Bloom!" win that
names the word; a "ran out of water / the word was: X" loss). The task body for
`apply_guess` requires "friendly text per the spec … when the guess ends the
game."

| Candidate | Win-guess `status_message` | Loss-guess `status_message` |
|---|---|---|
| A | `Good guess! The garden grows.` ❌ generic | `No match. A weed appears.` ❌ generic |
| B | `Bloom! You've revealed the whole word!` ✓ | `The garden ran out of water.` ✓ (no word echo) |
| C | `You guessed the word: GO. The garden is thriving.` ✓ §6.6 | `The garden ran out of water. The word was: GARDEN.` ✓ §6.7 |
| D | `Bloom! You guessed the word: GO. The garden is thriving.` ✓ | `The garden ran out of water. The word was: GARDEN. Try again…` ✓ |
| E | `Good guess! The garden grows.` ❌ generic | `No match. A weed appears.` ❌ generic |

All five were otherwise correct on the probed behaviours:
- Terminal-state priority: a correct final guess at `water=1` → `won=True,
  game_over=True, is_lost()=False` (win never misread as loss). ✓ all.
- Loss at `water→0`: `game_over=True, won=False, is_lost()=True`. ✓ all.
- Repeated **wrong** guess: no second water/weed drain, "already guessed"
  message. ✓ all (the classic double-penalty bug is absent everywhere).
- Guess after `game_over`: pure no-op, letter not added, only message changes. ✓ all.
- `validate_guess` matrix (`a`,`  b  `,``,`   `,`apple`,`7`,`!`,`Z`): every
  candidate returns the same correct `(letter|None, message)` pairs, with the
  two specific messages ("Please enter a single letter." for empty/multi,
  "That is not a letter." for digit/symbol). ✓ all.
- `select_word` over an 80-seed sweep for every difficulty yields only
  in-band words (easy len 6 only — no len-4/5 words exist; normal 6–8; hard
  7–8) and `water_for` returns 8/6/4. Unknown difficulty raises `ValueError`. ✓ all.

## Per-candidate

### Candidate C — strongest (ADOPT)
**Strengths:** Most spec-faithful of all five. Win text mirrors §6.6 ("You
guessed the word: X. The garden is thriving."); loss text mirrors §6.7 ("The
garden ran out of water. The word was: X."). Both echo the word, which a
task-002 UI needs. Message strings are module-level constants (incl. `{word}`
/`{letter}` templates) and the tests import them rather than re-typing literals.
Difficulty table encoded once (`_DIFFICULTY_CONFIG`) and shared by `water_for`
and `select_word`; empty pool raises `ValueError` (never a silent fallback);
`rng=None` defaults to module `random`. `apply_guess` is purely functional via
`dataclasses.replace`, and two tests positively assert the original state is not
mutated (on both correct and wrong guesses). Fixtures are built directly with
pinned values (`_make_state`). Covers a single-letter-word display edge.
**Weaknesses:** `replace(state, status_message=…)` in the repeat/game-over
branches shares the original `guessed_letters` set by reference (shallow copy) —
harmless here because those branches never mutate the set, but worth noting.
Word-pool tests are lighter than D's (no explicit "easy excludes long words").
GameState matches SPEC §12 field names/order/defaults exactly.

### Candidate D — also fully correct, runner-up
**Strengths:** Correct and complete; full spec-faithful win and loss messages
(echoes the word). Message constants imported by tests. Difficulty table encoded
once. **Best word-selection test rigor**: 50-seed pool sweeps plus positive
exclusion assertions (`easy` pool excludes VINEYARD/ORCHARD; `hard` excludes
GARDEN/FLOWER). Good purity/`__init__` docstrings. GameState fields exact.
**Weaknesses:** `apply_guess` **mutates the input state in place** and returns
the same object (a legitimate choice — `GameState` is a mutable dataclass and
the signature only promises a returned `GameState` — but a behavioural fork from
A/C/E, and a task-002 author expecting functional purity could be surprised).
Consequently has no non-mutation test. Fewest total game-state scenarios (31).

### Candidate B — correct, most defensive
**Strengths:** Correct and complete; distinct win/loss messages; message
constants; single difficulty table; empty-pool `ValueError`. Most defensive:
`validate_guess` tolerates non-`str` input (`None`/`int` → "single letter"
message) and `apply_guess` re-`upper()`s the letter and clamps water with
`max(new_water, 0)` so it can never display negative. Largest suite (51),
including non-str input rejection. **Weaknesses:** Win/loss messages are friendly
but **do not echo the secret word**, where SPEC §6.6/6.7 explicitly show it —
slightly less faithful than C/D. The defensive non-`str` handling is mild
scope-creep (input only ever arrives from `input()`), though harmless.

### Candidate A — passes gates, contract gap on end-of-game message
**Strengths:** Clean immutable `apply_guess`; single `DIFFICULTY_CONFIG` shared
by both functions; empty-pool `ValueError`; direct-construction fixtures;
non-mutation test; good positive assertions on wrong-guess (water−1 ∧ weed+1 ∧
letter recorded). **Weaknesses:** On a winning or losing guess the
`status_message` stays the **generic** "Good guess! The garden grows." /
"No match. A weed appears." (empirically confirmed) — it never produces the
Bloom / ran-out text of SPEC §6.6/6.7, so a UI cannot distinguish a game-ending
turn from an ordinary one by message. Also defines all user-facing strings as
**inline literals** rather than module constants, against the established
project rule that messages live once as constants imported by other modules and
tests. GameState adds default values to every field (spec defaults only the last
three) — harmless but a small contract drift.

### Candidate E — weakest
**Strengths:** Correct core logic; gates green; reasonable length-band sweeps in
word tests. **Weaknesses (several, compounding):**
1. Same end-of-game message gap as A — win/loss leave the generic guess text
   (confirmed empirically); plus inline string literals, not constants.
2. **Difficulty table duplicated**: length bands live in an `if/elif/else` in
   `select_word` while water lives in a separate `levels` dict in `water_for` —
   two independent encodings of the same difficulty set, exactly the
   divergence-prone duplication the project rule forbids.
3. **Test-fixture anti-pattern**: most game tests call `game.new_game()` (a
   randomized constructor) and then overwrite `secret_word`/`guessed_letters`/…,
   instead of constructing `GameState` directly with pinned values.
4. Several word tests (`test_select_word_returns_uppercase`,
   `…_from_list`) and the `new_game()` fixtures use the **global RNG** with no
   seeded `random.Random` injected — non-deterministic per the project rule.
5. Looser assertions (`assertIn("Good guess", …)`) rather than exact equality.

## Comparative ranking

1. **C** — correct, complete, most spec-faithful win+loss messages, immutable
   and non-mutation-tested, constants + DRY table. Adopt as-is.
2. **D** — equally correct with the best word-pool tests; loses only on the
   in-place-mutation design fork and lighter game-state coverage.
3. **B** — correct and most defensive, but win/loss messages omit the word echo.
4. **A** — gates pass, but generic end-of-game message (spec gap) and literals
   instead of message constants.
5. **E** — gates pass, but duplicated difficulty table, fixture anti-pattern,
   non-deterministic tests, and the same end-of-game message gap.

## Verdict
**ADOPT C.** It is correct and complete against every acceptance criterion,
is the most faithful to SPEC §6.6/6.7 end-of-game text, and best satisfies the
project's standing rules on message constants, single-source difficulty config,
seeded RNG, and direct-construction fixtures. No synthesis is needed: a fully
adequate candidate exists.
