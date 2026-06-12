# Task 001 Review — Word Garden (complete game in one shot)

Reviewer round: all five candidates passed the six mechanical gate checks
and all hygiene checks (confirmed independently: no candidate touches
`SPEC.md`/`GOAL.md`/`farnsworth.json`/`tasks/`/`.code-tips.md`, none commits
bytecode, all add the same clean 11-file layout). The gate saturated, so
this review is decided on empirical behavioral probing.

## Method

For each candidate: `git apply`, run the suite, `compileall`, the four
play/help/usage gates, then direct engine probing via `python3 -c` —
win/loss sessions with a pinned word, ASCII purity across whole sessions
**including the final screen**, the five growth stages in **both** emoji and
ASCII modes, the `is_lost`-on-won-at-zero-water boundary, and `select_word`
for every difficulty. Reset with `git reset --hard && git clean -fd -e
.farnsworth` between candidates.

## The discriminating signal: ASCII growth-stage collapse

The SPEC (section 10) and GOAL semantic half require **five observable,
distinct growth stages**, and `--ascii` must swap *every* emoji for its
fallback while keeping the stages observable. Probing each candidate's
growth glyph across the five stages in ASCII mode:

| Cand | Emoji stages distinct | **ASCII stages distinct** | ASCII glyphs |
|------|----------------------|---------------------------|--------------|
| A    | 5                    | **1**                     | all `*` |
| B    | 5                    | **2**                     | `*`×4, `x` (loss only) |
| C    | 5                    | **5**                     | `*` `+` `@` `X` `~` |
| D    | 5                    | **4**                     | `*` `**` `***` `***` `###` (near-win == win) |
| E    | 5                    | **5**                     | `*` `+` `^` `@` `x` |

This is invisible to the gate (`plays-ascii` only checks exit 0 on empty
input; ASCII purity holds for all five). But it is a real spec deviation:
in ASCII mode A's plant never changes, B's plant only changes at loss, and
D collapses near-win into win. Only **C and E** keep all five stages
observable in ASCII. This is the primary discriminator of the round.

## Per-candidate findings

### Candidate A — clean, faithful engine; weak end screens; ASCII stage total-collapse
- **Good:** clear immutable-ish `apply_guess` (returns fresh GameState);
  `is_lost` correctly guarded (`water<=0 and not is_won`); tip-10 honored;
  message constants single-sourced in game.py and imported by `test_game`;
  EOF/interrupt friendly; signatures exact; 75 tests pass.
- **Bad (display faithfulness):** A has **no dedicated win/loss screens**.
  It re-renders the full game board with a swapped title glyph and appends
  the message, producing `🌻 Word Garden` + body — **not** the SPEC 6.6
  `🌻 Bloom!` header, and the loss screen reads `🥀 Word Garden` + "The word
  was: …" with **no "ran out of water" text** (SPEC 6.7 requires that
  sense; the glyph carries it weakly, the text does not). Tip-1 partial
  miss.
- **Bad (growth collapse):** all five ASCII stage glyphs are `*` — **1
  distinct**. ASCII plant is static.
- Tests assert win via hand-typed substrings ("thriving","PYTHON") in
  `test_main` rather than the imported constant; would not catch the
  missing-water-sense or the header divergence.

### Candidate B — excellent structure and faithfulness; ASCII stages collapse to 2
- **Good:** dedicated `render_win`/`render_loss` matching SPEC 6.6/6.7
  exactly (`🌻 Bloom!`, `🥀 The garden ran out of water.`); terminal loss
  status message names the word AND keeps the water sense; all message
  strings (incl. `WIN_HEADER`/`LOSS_HEADER`) single-sourced and imported by
  ui.py AND tests — **tip-7 clean**; explicit `is_lost` not-won guard with
  a dedicated `test_is_lost_false_when_won_at_zero_water` (tip-10 directly
  exercised); `select_word` raises on unknown/empty pool; rng default not
  fresh-seeded. The most readable candidate.
- **Bad (growth collapse):** `GROWTH_ASCII` maps start/progress/near_win/win
  all to `*`; only loss differs (`x`). **2 distinct** ASCII stages — the
  in-game plant only changes once, at game over. Direct spec-10 deviation
  under `--ascii`.
- Minor: invalid input sets `status_message` then `continue`s without an
  immediate echo (message appears on next render) — acceptable.

### Candidate C — fully faithful, very thorough tests; one tip-7 violation
- **Good:** 5 distinct ASCII stages (`* + @ X ~`) AND 5 emoji; win/loss
  screens exact (`render` returns them on `game_over`); `is_lost` guarded +
  directly tested on won-at-zero-water; defensive `apply_guess` raises
  `ValueError` loudly on a non-uppercase/non-single letter (a contract
  *addition* — harmless since main only feeds validated letters); 98 tests,
  the largest suite; loss e2e asserts "ran out of water"; `select_word`
  raises correctly. Status message bodies name the word.
- **Bad (tip-7 violation):** game.py defines `MSG_WIN_TITLE = "Bloom!"` and
  `MSG_LOSS_TITLE = "The garden ran out of water."` but **ui.py re-types
  both as literals** (`f"{glyph} Bloom!"`, `f"{glyph} The garden ran out of
  water."`). The TITLE constants are **dead** (referenced nowhere) and the
  screen header text now lives in two places that can drift — the exact
  "re-typed string literals rot silently" defect the seed flags three
  times. The loss e2e test also asserts the header via a hand-typed
  "ran out of water" substring rather than a constant.

### Candidate D — faithful screens; ASCII near-win/win collapse; weak ASCII stage test
- **Good:** dedicated `render_win_screen`/`render_loss_screen` with correct
  SPEC 6.6/6.7 headers; `is_lost` guarded; immutable `apply_guess`; EOF/
  interrupt friendly; 85 tests; loss e2e asserts "ran out of water".
- **Bad (growth collapse):** `_get_growth_stage_ascii` returns `***` for
  both near-win (`fraction < 1.0`) and win (`won`) — **4 distinct** ASCII
  stages, near-win and win indistinguishable. The ASCII growth test only
  asserts presence of `*` and *absence of emoji* (a negative-only
  assertion, tip-2 violation) so it never checks distinctness and lets the
  collapse through.
- Minor: win/loss screens render `state.status_message` as the body, so the
  screen text is coupled to the message set by `apply_guess` (works, but
  brittle if called on an arbitrary state).

### Candidate E — fully faithful, tip-7 clean, 5 ASCII stages; one inert smell
- **Good:** 5 distinct stages in BOTH emoji (`🌱🌿🌷🌻🥀`) and ASCII
  (`* + ^ @ x`); win/loss screens exact, with the TITLE constants
  (`MSG_WIN_TITLE`/`MSG_LOSS_TITLE`) and BODY templates **single-sourced in
  game.py and imported by ui.py AND tests** — **tip-7 clean**, the only
  candidate to import the screen-header constants into the renderer;
  `is_lost` guarded + a dedicated standalone test citing tip-10; e2e win/
  loss with a pinned word using try/finally restoration (tip-5/8 style);
  the **win e2e test explicitly asserts zero non-ASCII chars** in
  `--ascii`; `select_word` raises correctly; EOF/interrupt friendly;
  signature exact. 88 tests.
- **Smell (not a bug):** `apply_guess` stores the win/loss **title (which
  contains an emoji)** as `status_message` (e.g. `"🌻 Bloom!"`). This is
  inert because `render`'s game-over branch builds the screen from the body
  templates and ignores `status_message`, so no emoji ever leaks into ASCII
  output (verified empirically across full win+loss ASCII sessions: zero
  non-ASCII). But putting an emoji in a state field is fragile, and the
  terminal `status_message` does not itself name the word (the screen body
  does). Tip-1 is met at the screen level, partially at the field level.
- **Minor spec nit:** `_growth_glyph` derives win/loss from the `is_won`/
  `is_lost` **predicates** rather than the `won`/`game_over` **flags** as
  SPEC 10 phrases it. In all reachable states the predicates and flags
  agree (verified across full sessions), so there is no observable bug; it
  is a literal-wording deviation only.

## Acceptance criteria summary

All five: tests green, compiles, EOF/ASCII-EOF exit 0 friendly, help 0,
usage 2, exact signatures, wrong-guess/repeat-guess/invalid-input accounting
correct, water `n/max`+symbols, weeds count+symbols, full session winnable
and losable, stdlib only, no committed bytecode, base files untouched.

Differentiators:
- **Five distinct growth stages under `--ascii`:** only **C** and **E** pass;
  A (1), B (2), D (4) collapse.
- **SPEC 6.6/6.7 end screens (header + body, "ran out of water"):** B, C, D,
  E pass; **A fails** (no dedicated screens, missing water-sense text).
- **Tip-7 single-source for screen text:** B and **E** pass; **C violates**
  (dead title constants + duplicated literals); A/D keep screen text only in
  ui.py so no cross-module drift, but A has no header screens at all.

## Seed-entry audit (did the field honor each of the 10 seed tips?)

1. **Terminal contract — flags AND message/text together.** *Partial.*
   B/C/D set faithful end SCREENS and terminal messages; E sets a faithful
   screen but a title-emoji `status_message` that does not name the word;
   **A violates the screen contract** (loss text omits "ran out of water").
2. **Tests assert the positive outcome, not absence of the negative.**
   *Partial.* C/E strongest (combined positive asserts). **D's ASCII growth
   test is negative-only** (`assertNotIn` emoji) and hid its own collapse.
3. **E2E success path forces a known scenario and asserts the artifact.**
   *Universally honored.* All pin/monkeypatch a word and assert the win/loss
   screen text. C/E use try/finally restoration.
4. **No `try/except SystemExit` around argparse.** *Universally honored.*
   A/D wrap in a bare `try/except SystemExit: raise` (a re-raise no-op that
   preserves 0/2) — ugly but compliant; B/C/E do not wrap at all (cleaner).
5. **Filter functions raise on unknown/empty pool, tests force it.**
   *Universally honored.* All raise `ValueError` for unknown difficulty and
   empty pool; tests cover the unknown path.
6. **Injectable I/O and rng; default rng is module-level, not seeded.**
   *Universally honored.* All use `rng or random` (module functions), verified
   to vary across calls; logic modules are terminal-free.
7. **Single-source message constants, imported in source AND tests.**
   *Violated by C* (dead `MSG_WIN_TITLE`/`MSG_LOSS_TITLE`; ui.py re-types the
   header literals). *Honored by B and E* (ui.py imports the header/body
   constants). A/D keep screen text solely in ui.py (no second copy) and
   import in-game message constants — partial.
8. **Build fixtures by constructing state directly, not factory+overwrite.**
   *Universally honored.* All tests use direct `GameState(...)`/helper
   constructors with pinned values.
9. **Hygiene: never write `.code-tips.md`, never commit bytecode, never edit
   base files.** *Universally honored.* Verified across all five diffs.
10. **Standalone predicate correct for every reachable state; exact closed
    signatures.** *Universally honored for `is_lost`* (all include the
    `not is_won` guard and test the won-at-zero-water boundary directly);
    signatures exact (no candidate added params to `main`/`select_word`).
    C *adds* a loud `ValueError` guard inside `apply_guess` — a defensive
    contract addition, not a signature change.

## Ranking

1. **E** — fully faithful screens, 5 distinct stages in both modes, tip-7
   clean (only renderer importing the header constants), rigorous tests with
   explicit ASCII e2e purity. One inert smell (emoji in `status_message`)
   and one literal-wording nit (predicate-driven glyph). No behavioral
   defect found.
2. **C** — equally faithful and the most thorough suite, 5 distinct ASCII
   stages, but carries a genuine tip-7 violation (dead title constants +
   duplicated header literals) — the round's most-repeated seed defect.
3. **B** — the most readable, tip-7 clean, faithful screens, but ASCII
   growth collapses to 2 stages (spec-10 deviation under `--ascii`).
4. **D** — faithful screens, but ASCII near-win/win collapse (4 stages) and
   a negative-only ASCII growth test that hid it.
5. **A** — clean engine but no dedicated end screens and ASCII stage total
   collapse (1 glyph); also the loss text drops the "ran out of water" sense.
