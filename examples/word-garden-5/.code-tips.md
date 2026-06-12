# Code Tips — Word Garden 5

Durable, rent-paying lessons for workers on this project. Every entry
carries provenance `[date, origin]`. Entries are contracts: imperative
language, explicit scope (source, tests, or both).

## Cross-project seed (curated by the orchestrator, 2026-06-12)

These entries are DOMAIN-GENERAL lessons distilled by reviewers on prior
Farnsworth projects (word-garden-1/2/3 and the loop's own dogfooding) and
seeded into this fresh project before round 1. They carry their original
provenance. Entry 10 is the first product of the "generalize while
distilling" rule: the general form of a lesson that previously existed
only as another project's project-scoped tip — and which, scoped that
way, failed to prevent the same defect recurring in a fresh project.
From here on, only the reviewer writes this file.

1. When an action TERMINATES a process (game over, job done, connection
   closed), you MUST update every adjacent piece of the contract — status
   message, summary text, final state — not just the boolean flags. The
   recurring defect shape across projects is "flags right, message wrong":
   `won`/`game_over` set correctly while `status_message` still reads as a
   mid-game message. Applies to source AND tests: end-of-process tests MUST
   assert the terminal message/text, not only the flags.
   [2026-06-12, seed; orig. word-garden-2 task-001]
2. Tests MUST assert the POSITIVE outcome, not the absence of the negative.
   A "wrong input costs one unit" test asserts the counter went down by
   exactly 1 AND the side effect happened AND the input was recorded — in
   combined assertions. Negative-only assertions have hidden real bugs in
   two prior projects. Applies to all test code.
   [2026-06-12, seed; orig. loop dogfooding task-002, word-garden-1 task-001]
3. An end-to-end "success path" test MUST force a known scenario
   (monkeypatch the factory, inject a fixed state or seeded rng) and assert
   the success artifact actually appeared. Asserting only `exit code == 0`
   or `A or B` proves nothing — prior candidates shipped "win" tests that
   never reached a win. Applies to tests.
   [2026-06-12, seed; orig. word-garden-1 task-002]
4. Do NOT wrap `argparse.parse_args` in `try/except SystemExit`. `--help`
   must exit 0 and a usage error must exit 2; swallowing `SystemExit` to
   "exit cleanly" turns usage errors into success. This exact defect has
   shipped in two separate projects. Applies to source.
   [2026-06-12, seed; orig. word-garden-1 task-002, word-garden-2 task-002]
5. Functions that select or filter from a pool MUST raise (`ValueError`)
   when the pool is empty or the key is unknown. NEVER fall back silently
   to the unfiltered pool — that hides a broken filter behind plausible
   output. Applies to source; tests MUST cover the raising path by FORCING
   it (e.g. shrink the pool in try/finally), not merely by asserting a
   message constant exists. [2026-06-12, seed; orig. word-garden-2 task-001,
   word-garden-3 task-001]
6. All I/O and randomness MUST be injectable: `input_fn=input`,
   `output_fn=print`, `rng=None` (module-level `random` when None — never a
   freshly seeded `Random` as the default, which would be deterministic).
   Logic modules stay terminal-free so the suite runs hermetically. Applies
   to source AND tests (tests use the injection points, not patching of
   builtins). [2026-06-12, seed; orig. word-garden-1/2, both tasks]
7. Define user-facing message strings ONCE as named module-level constants
   and import them everywhere they are needed — in other source modules AND
   in tests. Re-typed string literals rot silently when wording changes.
   Tests MUST import the constant and assert against it (full-string
   equality where practical), never a re-typed literal of the same text:
   importing a constant and then asserting a hand-typed substring is the
   violation that recurred in three prior rounds. Applies to source AND
   tests. [2026-06-12, seed; orig. word-garden-1 task-002, word-garden-2
   task-002, word-garden-3 task-002]
8. Build test fixtures by constructing the state object directly with
   pinned values. Do NOT call the random factory and then overwrite fields.
   Applies to tests. [2026-06-12, seed; orig. word-garden-1 task-001]
9. Hygiene contract: never write or commit `.code-tips.md` (the reviewer
   owns it); never commit bytecode (`__pycache__/`, `*.pyc`); never modify
   `SPEC.md`, `GOAL.md`, `farnsworth.json`, or `tasks/`. Commit all
   deliverable work to your assigned branch.
   [2026-06-12, seed; orig. loop dogfooding task-001]
10. A standalone PREDICATE must not rely on a caller's check ordering: any
    function answering "is X true of this state?" MUST return the correct
    answer for EVERY reachable state, including states where a sibling
    predicate is also (or instead) true. The recurring instance: a loss
    check that omits the not-won guard, correct only because one caller
    happens to test win first — wrong the moment anything calls it
    directly. Required signatures are EXACT and CLOSED contracts: do not
    add parameters or reorder them to serve your tests; propose changes via
    escalation, never silently in the diff. Applies to source; tests MUST
    exercise each predicate DIRECTLY on terminal/boundary states, not only
    through the orchestrating caller. [2026-06-12, seed; generalized from
    word-garden-1/3 task-001 `is_lost` defect and word-garden-3 task-002
    signature deviation]

## Project-scoped (Word Garden 5)

11. The `--ascii` fallback MUST PRESERVE STAGE DISTINCTNESS, not merely
    avoid emoji. SPEC section 10 requires five observable, distinct growth
    stages; `--ascii` swaps every emoji for its fallback but the five
    fallbacks MUST still be mutually distinct glyphs. The recurring defect
    this round: candidates mapped multiple stages (start/progress/near-win/
    win) to the SAME ASCII glyph (`*`), so the plant became static or
    near-static in ASCII while passing every gate — the gate only checks
    ASCII purity and exit 0, never distinctness. The `plays-ascii` gate
    will NOT catch this. Applies to source. Tests MUST assert the five
    stage glyphs are pairwise distinct in BOTH emoji AND ASCII mode (e.g.
    `len({glyph(s) for s in the five stages}) == 5` per mode), POSITIVELY —
    a test that only asserts "contains `*`" and "contains no emoji" (a
    tip-2 negative-only assertion) lets the collapse through.
    [2026-06-12, task-001]
12. Render the win/loss END SCREENS as DEDICATED screens matching SPEC
    sections 6.6/6.7 exactly: a header line carrying the stage glyph and
    the spec header text (`🌻 Bloom!`, `🥀 The garden ran out of water.`),
    then the body (win: `You guessed the word: <WORD>` + `The garden is
    thriving.`; loss: `The word was: <WORD>` + retry line). Do NOT reuse
    the in-game board with only a swapped title glyph — that drops the
    `Bloom!` header and the "ran out of water" sense. The loss screen MUST
    contain the out-of-water TEXT, not lean on the 🥀 glyph alone (in
    `--ascii` the glyph is gone). Applies to source. Tests MUST assert both
    the header AND the body of each end screen against imported constants.
    [2026-06-12, task-001]
13. Keep state-field values RENDER-NEUTRAL: `status_message` and other
    GameState fields MUST NOT embed presentation glyphs (emoji or ASCII
    art). Store the plain message/word; let `ui.py` add the glyph at render
    time from the `ascii_mode` flag. Embedding an emoji in `status_message`
    (e.g. setting it to `"🌻 Bloom!"`) is a latent `--ascii` leak that is
    only inert as long as the end-screen renderer happens to ignore the
    field — one refactor away from a non-ASCII bug. Applies to source.
    [2026-06-12, task-001]
14. Derive the win/loss render branch from the terminal STATE FLAGS
    (`won`, `game_over`) as SPEC section 10 specifies, not by recomputing
    `is_won`/`is_lost` inside `ui.py`. The flags are the authority once a
    turn has resolved; recomputing predicates in the renderer duplicates
    logic and can diverge from the flags under any future state that sets
    flags without re-satisfying the predicate. In-progress stage selection
    (start/progress/near-win) is correctly driven by the revealed-letter
    fraction; only the win/loss override should read the flags. Applies to
    source. [2026-06-12, task-001]
15. The win/loss SCREEN TEXT (`Bloom!`, `The garden ran out of water.`,
    the thriving/retry/word-reveal lines) is user-facing message text and
    falls under tip 7: define it ONCE as named constants in one module and
    IMPORT it into `ui.py` and the tests. The recurring instance this
    round: title constants defined in `game.py` but left DEAD while
    `ui.py` re-typed the same header strings as literals — two copies that
    drift. Applies to source AND tests. [2026-06-12, task-001]
