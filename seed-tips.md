# Cross-Project Seed Tips (the seed pile)

The M3 cross-project memory artifact: DOMAIN-GENERAL lessons distilled
by reviewers across Farnsworth projects, curated here by the
orchestrator. Seed a NEW project's `.code-tips.md` with these entries
before round 1 (copy the file, keep every provenance tag, then let that
project's reviewer take ownership). Project-scoped lessons do NOT
belong here — when a reviewer distills a project lesson that
instantiates a general class, the GENERAL form is written here and the
specific form stays in the project's tips (the "generalize while
distilling" rule, validated in word-garden-3 and word-garden-5: a
lesson prevents exactly what its scope covers, nothing more).

Curation rules: imperative contract language; explicit scope (source,
tests, or both); provenance on every entry; entries must pay rent in
any project's briefing, not just the one that birthed them.

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
   violation that recurred in three prior rounds — and in word-garden-5 a
   candidate lost the round for defining constants and leaving them DEAD
   while re-typing the literals at the call site: defining is not
   single-sourcing; the constant must be the only copy. Applies to source
   AND tests. [2026-06-12, seed; orig. word-garden-1 task-002, word-garden-2
   task-002, word-garden-3 task-002, word-garden-5 task-001]
8. Build test fixtures by constructing the state object directly with
   pinned values. Do NOT call the random factory and then overwrite fields.
   Applies to tests. [2026-06-12, seed; orig. word-garden-1 task-001]
9. Hygiene contract: never write or commit `.code-tips.md` (the reviewer
   owns it); never commit bytecode (`__pycache__/`, `*.pyc`); never modify
   the spec, goal, fleet config, or task briefs. Commit all deliverable
   work to your assigned branch.
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
    signature deviation; honored 5/5 in word-garden-5 round 1]
11. A FALLBACK or degraded output mode (ASCII instead of emoji, no-color,
    plain-text instead of rich markup) MUST preserve the SEMANTIC
    DISTINCTIONS of the primary mode, not merely satisfy the character-set
    constraint. If the primary mode shows N observably different states,
    the fallback shows N observably different states. The recurring
    instance: five emoji growth stages collapsed to one or two ASCII
    glyphs while passing every "output is pure ASCII and exits 0" check.
    Applies to source; tests MUST assert the distinction count POSITIVELY
    in EVERY supported mode (e.g. the set of N state markers has size N
    per mode), never only purity or exit codes.
    [2026-06-12, seed; generalized from word-garden-5 task-001]
12. Keep DATA fields presentation-neutral: state objects and other data
    contracts MUST NOT embed presentation glyphs, emoji, color codes, or
    markup. Store the plain value; the rendering layer owns presentation
    and applies it from the active mode at render time. An embedded glyph
    in a data field is a latent fallback-mode leak that stays inert only
    while every renderer happens to ignore the field. Applies to source.
    [2026-06-12, seed; generalized from word-garden-5 task-001]
