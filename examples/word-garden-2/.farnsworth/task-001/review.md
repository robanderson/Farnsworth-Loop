# Review — task-001 (Word Garden core engine)

Reviewer: anonymized. Method: each diff applied to a clean base snapshot in
`/tmp/review-001/<L>`, then `compileall`, `unittest discover`, and a battery of
out-of-suite probes (win at 0 water via direct predicates, terminal-guess
messages, repeated guess, None/invalid input, multi-occurrence reveal,
`select_word` x200 per difficulty, post-game-over no-op, set-aliasing).

All five compile clean, pass their own suites, are stdlib-only, commit no
bytecode, contain no `input()`/`print()`, and use the exact `GameState` field
names. They differ on win/loss messaging, input robustness, mutation contract,
and test rigor.

## Summary scoreboard

| | Tests pass | Win/loss MESSAGE | None input | apply_guess contract | Notable risk |
|---|---|---|---|---|---|
| A | 40 ✓ | ✓ distinct, via constants | handled (`or ""`) | mutates in place | win/loss msg omits the word |
| B | 57 ✓ | ✗ leaves "Good guess!"/"No match" | raises AttributeError | copies (but shares set in 2 branches) | **terminal message bug** |
| C | 63 ✓ | ✓ distinct, includes word | handled (None check) | copies (fresh set) | case-folds difficulty (mild) |
| D | 58 ✓ | ✗ leaves "Good guess!"/"No match" | raises AttributeError | copies (fresh set) | **terminal message bug** |
| E | 58 ✓ | ✓ distinct, includes word | raises AttributeError | mutates in place | empty-pool fallback masks bugs |

## Candidate A — GOOD (adopt target)

GOOD:
- Cleanest structure. Messages are module constants (`MSG_CORRECT`, `MSG_WRONG`,
  `MSG_WIN`, `MSG_LOSS`, `MSG_GAME_OVER`) that the UI (task-002) can import
  rather than string-match — the most reusable design of the five.
- Win/loss messaging is correct and distinct on the terminal guess.
- `is_lost` = `remaining_water <= 0 and not is_won(state)` — win strictly beats
  loss; verified `is_won`/`is_lost` directly at 0 water.
- Best edge test in the field: `test_win_on_last_water_is_not_a_loss` exercises
  the subtle win/loss interaction the brief calls out.
- `validate_guess(None)` is tolerated (`(input_text or "")`).
- Rich `__init__` re-exporting the public API.

BAD / minor:
- Win message ("Bloom! The garden is thriving.") and loss message ("The garden
  ran out of water.") do NOT include the secret word, whereas SPEC 6.6/6.7
  example screens name the word. Soft: the UI holds `state.secret_word` and can
  append it. Not a hard-requirement violation.
- `apply_guess` mutates and returns the SAME object; tests rely on this. Fine,
  but the mutate-vs-copy contract is undocumented at the package level.

## Candidate B — GOOD tests, BAD terminal messaging

GOOD:
- Largest, well-organized suite (57). Strong positive assertions, integration
  win/loss playthroughs, duplicate-letter display test.
- `float("inf")` upper bound is a clean way to express "7+".

BAD:
- **Terminal-message defect:** on a winning guess `status_message` stays
  "Good guess! The garden grows."; on a losing guess it stays
  "No match. A weed appears." The win/loss flags are set, but the message — the
  one thing the UI shows at game end — is never updated. Brief explicitly
  requires updating `status_message` when the guess ends the game; SPEC 6.6/6.7
  show distinct end screens. The suite asserts flags only, so it never caught
  this.
- `validate_guess(None)` raises `AttributeError` (no None guard).
- Repeated-guess and game-over branches set `guessed_letters=state.guessed_letters`
  (shared reference) while other branches build a fresh set — inconsistent copy
  semantics, a latent aliasing hazard.

## Candidate C — GOOD (correct and complete)

GOOD:
- Win/loss messages are distinct AND name the word ("...the word: PYTHON! The
  garden is thriving.", "...ran out of water. The word was: GARDEN.") — closest
  to SPEC 6.6/6.7.
- `validate_guess(None)` handled; `validate_guess` coerces via `str(...)` and is
  the most defensive.
- Excellent tests: `win_not_lost_simultaneously`, repeated-letter reveal,
  invalid-input-does-not-mutate-state, per-difficulty length bounds x20.
- Copies state (fresh set each return) — no aliasing leak.

BAD / minor:
- `water_for`/`select_word` lowercase the difficulty, so "EASY"/"Normal" are
  accepted. Not required and not prohibited (unknown still raises). Mild scope
  creep, and it means the ValueError is only raised for truly unknown names.
- Win/loss branches are duplicated inline (four near-identical `GameState(...)`
  constructions) — more verbose than A.

## Candidate D — BAD terminal messaging (same class as B)

GOOD:
- Good suite (58) with explicit per-difficulty water tests and a loss
  playthrough.
- Copies state with `.copy()` consistently (no aliasing leak).

BAD:
- **Same terminal-message defect as B:** win leaves "Good guess!", loss leaves
  "No match. A weed appears." Flags set, message wrong.
- `validate_guess(None)` raises `AttributeError`.
- `test_game.py` defines a module-level `display_word` helper at the BOTTOM of
  the file and also `from ...` — relies on call-time name resolution; works but
  is confusing. Imports `field`/`Optional` partly unused.

## Candidate E — GOOD messaging, BAD latent fallback

GOOD:
- Distinct win/loss messages that name the word.
- Clean `_DIFFICULTY_TABLE`; tidy `display_word`/`is_won`/`is_lost`.

BAD:
- **`select_word` empty-pool fallback:** if the length filter yields nothing it
  silently falls back to the FULL word list (`candidates = list(WORDS)`). For
  the current 10 words every pool is non-empty, so it's dormant — but it would
  mask a future words.py edit that breaks a difficulty band, returning an
  out-of-band word instead of failing loudly. A/B/C/D raise instead. This is the
  most dangerous *latent* behaviour in the field.
- `validate_guess(None)` raises `AttributeError`.
- Case-folds difficulty (same mild note as C).
- Mutates in place (same as A; fine, undocumented).

## Cross-cutting findings

1. **Win/loss message on the terminal guess is the discriminator.** A, C, E set
   it; B, D do not. This is the single most important correctness axis and it is
   invisible to flag-only tests — future suites MUST assert the end-of-game
   `status_message`, not just `won`/`game_over`.
2. **`is_lost` MUST exclude the won state.** All five got this right
   (`water<=0 and not is_won`). Worth locking in as an invariant.
3. **None input:** only A and C tolerate it; the brief/spec do not require it
   (UI feeds strings). Not disqualifying.
4. **Mutate vs. copy is unspecified.** A/E mutate-and-return-same; B/C/D return
   a new object. Task-002 must treat the return value as authoritative and not
   assume the input is left untouched. Worth standardizing.
5. **Empty-pool policy is unspecified.** A/B/C/D raise; E falls back. Raising is
   safer and should be the contract.

## Conclusion

A and C are both correct and complete against every acceptance checkbox. B and D
have a real terminal-message defect; E carries a latent fallback that defeats the
 value of difficulty filtering. Because a correct, complete candidate exists as-is,
the outcome is **adopt**. A is selected for its message-constant design (directly
reusable by task-002), its explicit win-at-0-water edge test, and its overall
clarity. A's only gap — win/loss text omitting the secret word — is cosmetic and
fully recoverable in the UI layer, which holds `state.secret_word`.
