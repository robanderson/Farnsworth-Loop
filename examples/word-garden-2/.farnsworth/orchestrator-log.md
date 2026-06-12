# Orchestrator Log — Word Garden 2 (replication run)

Process findings from the Farnsworth Loop's first REPLICATION: the same
Word Garden spec, task briefs, fleet mix, and gate as `word-garden-1`,
re-run from a fresh seed with an empty tips file on 2026-06-12. The point
was to see which of run 1's findings reproduce. Per-task forensics live in
`.farnsworth/task-001/` and `.farnsworth/task-002/`; durable engineering
lessons live in `.code-tips.md`. This file is about the PROCESS.

Dispatch mode: MANUAL AGENT DISPATCH (orchestrator and reviewer as agents,
workers as parallel sub-agents pinned to git worktrees), same as run 1 and
for the same reason — nested headless `claude -p` cannot authenticate in
this managed sandbox. Blindness, anonymization, gate, and verdict mechanics
follow the CLI's implementation; `farnsworth.json` records the emulated fleet.

---

## task-001 — Core engine (2026-06-12)

**Setup.** Full 5-worker fleet: 2x Haiku 4.5, 2x Sonnet 4.6, 1x Opus 4.8,
blind, parallel, one worktree each. `.code-tips.md` did not exist yet.
Gate: unittest + compileall. Brief byte-identical to run 1's.

**Gate.** 5/5 first-pass. Identical file footprints (low divergence; no
round-2 trigger) — same as run 1.

**Verdict.** ADOPT A -> unsealed to the OPUS worker (replicates run 1's
round-1 result exactly). The reviewer found a real defect in TWO
gate-passing candidates (both Haiku): on the guess that ends the game,
`won`/`game_over` are set correctly but `status_message` still reads
"Good guess!"/"No match" — the UI would render the wrong feedback at the
decisive moment. It passed the gate because every suite asserted only the
boolean flags. A third candidate (a Sonnet) carried a latent risk:
`select_word` silently falls back to the full word list on an empty pool.

**Findings.**
1. Run 1 round 1 replicated: empty tips file -> strongest model wins.
2. The defect CLASS changed (run 1: `is_lost` missing the not-won guard;
   run 2: terminal-guess message) but its SHAPE is identical — correct
   flags, wrong adjacent contract, invisible to flag-level tests. The
   "assert the full outcome, not just the flag" lesson generalizes.
3. Haiku again spent the most motion for the weakest results (52k tokens /
   51 tool calls vs the winner Opus's 50k / 28).

**Cost.** Workers ~218k agent tokens (w1 haiku 52k, w2 haiku 35k, w3
sonnet 42k, w4 sonnet 39k, w5 opus 50k); reviewer ~118k (~54% of worker
spend).

**Distilled.** 21 lessons into `.code-tips.md` (terminal-message contract,
is_lost guard, single difficulty table, no silent fallbacks, MSG_*
constants, positive assertions, force-a-known-word testing).

---

## task-002 — UI, main loop, packaging (2026-06-12)

**Setup.** TRIAGED fleet (routine, well-specified): 1x Haiku, 1x Sonnet,
1x Opus, every briefing carrying the 21 task-001 lessons. Gate: unittest +
compileall + the two run-1 extensions (piped EOF exits 0; engine files
byte-identical to base).

**Gate.** 3/3 first-pass, extensions included.

**Verdict.** ADOPT C -> unsealed to the OPUS worker. **This is where the
replication BROKE run 1's pattern:** run 1's tips round was won by Sonnet
over Opus; here Opus won both rounds. The field still had one real
gate-passing defect — the Haiku candidate wraps `parse_args` in
`try/except SystemExit: return 0`, so usage errors exit 0 instead of 2.
The winning Opus candidate was the only one to honor the MSG_*-reuse tip
at test level, shipped a public unit-tested `growth_stage()`, and had the
highest test rigor despite the smallest suite (61 vs 70/80 tests).

**Findings.**
1. **The headline pattern did not reproduce.** Three consecutive prior
   rounds (loop dogfooding + word-garden-1) had the win move down the cost
   ladder when tips entered the briefing; this round Opus won with tips in
   play. At one round per cell, "cheaper model wins once tips exist" looks
   like noise around the real effect — which is the FLOOR, not the winner:
   defects-in-field went 2 -> 1 here (run 1: 1 -> 0).
2. **Project-scoped memory re-learns old lessons.** The exact argparse
   defect this round's Haiku committed is already a distilled tip in
   word-garden-1's `.code-tips.md` — but this fresh project started with
   empty memory, and round 1 (an engine task) produced no CLI tips. The
   error class predicted by the OTHER project's memory recurred precisely
   where this project's memory was blank. Tips work; their scope is the
   problem. Cross-project seed tips are the obvious loop extension.
3. **Tip absorption was partial and scope-sensitive, replicating run 1's
   phrasing finding at the next level.** The MSG_* tip was written
   imperatively (run 1's fix) but didn't say it applied to TESTS; 2 of 3
   candidates string-matched literals in tests anyway. Imperative voice is
   necessary but not sufficient — tips must state their scope explicitly.
   The reviewer re-sharpened the entry.
4. **Duplicate-dispatch signature reproduced, harmlessly.** Several
   background workers in both rounds reported finding the work "already
   present" on their branches (infrastructure retry re-entering the same
   worktree). The artifact-is-the-phase-boundary rule absorbed it again:
   committed branches faced the gate; agent claims were ignored.
5. **Reviewer share stayed ~54-55% in BOTH rounds** (run 1 saw 50% -> 68%
   under triage). The difference: this run's workers were heavier per
   attempt, so the fixed review depth was a smaller fraction. Reviewer
   dominance tracks worker economy, not just field size.

**Cost.** Workers ~193k agent tokens (haiku 74k/79 calls, sonnet 59k/45,
opus 60k/35); reviewer ~106k (~55% of worker spend).

**Distilled.** 5 UI/CLI entries added, 2 amended (MSG_* scope sharpened,
force-a-known-word rule).

---

## Cumulative metrics (after 2 merged tasks)

| Metric                      | task-001 (no tips) | task-002 (21 tips) |
|-----------------------------|--------------------|---------------------|
| Fleet                       | 5 (2H/2S/1O)       | 3 (1H/1S/1O) triaged |
| First-pass gate rate        | 5/5                | 3/3                 |
| Correctness bugs in field   | 2 (gate-passing)   | 1 (gate-passing)    |
| Verdict                     | adopt              | adopt               |
| Winning model               | Opus 4.8           | Opus 4.8            |
| Worker agent tokens         | ~218k              | ~193k               |
| Reviewer agent tokens       | ~118k (54%)        | ~106k (55%)         |
| Round 2 triggered           | no                 | no                  |

Verdict distribution: adopt 2 / synthesize 0 / escalate 0.
Win rate by model: Opus 2, Sonnet 0, Haiku 0.

## What this replication changes about the loop

1. **Demote the winner-identity claim; promote the floor claim.** The
   reproducible effect of tips across both runs is defect REDUCTION
   (run 1: 1 -> 0; run 2: 2 -> 1 with a different defect class), not
   "a cheaper model wins." Per-model win rate needs many more rounds
   before it means anything; defects-per-round in gate-passing candidates
   is the loop's real early learning signal.
2. **Cross-project seed tips.** Domain-general lessons (argparse exit
   codes, assert-the-positive, injected I/O) are being re-learned per
   project at the cost of one shipped defect each time. The loop should
   maintain a small curated cross-project tips seed, distinct from
   project-scoped tips, injected into round 1 of any NEW project.
3. **Tips must declare scope.** Distillation rule upgraded: imperative
   contract language AND an explicit statement of where the tip binds
   (source, tests, both). Two runs have now each spent a round discovering
   a narrower version of this rule.
4. **Housekeeping held.** Ledger + artifact-boundary + sweep-before-reuse
   absorbed duplicated dispatches in both rounds with zero damage; the
   per-task gate extensions ran at zero marginal cost.
