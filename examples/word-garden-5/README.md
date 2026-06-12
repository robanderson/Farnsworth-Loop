# Word Garden 5 — the goal-driven run

The fifth Word Garden, and the first project completed under the loop's
goal-driven termination contract (PRD Section 2.4): no pre-planned task
list — a goal brief (`GOAL.md`) plus mechanical done checks in
`farnsworth.json`, one gap-derived task per cycle, and the loop stops
only when `farnsworth done` AND the reviewer's semantic attestation both
pass. It did, after exactly one iteration: task-001 dispatched the
ENTIRE game as a whole-program one-shot to a 5-worker blind tournament,
and the adopted candidate met the goal.

Three firsts in this run:

1. **Goal-driven cycling** (PRD 2.4) — the loop's exit was decided by
   the done probe + attestation, not by finishing a list. Exit: DONE,
   1 iteration.
2. **Seed v2** — the 10-entry cross-project tips seed includes the
   GENERALIZED predicate lesson ("a standalone predicate must not rely
   on a caller's check ordering"), the first product of run 3's
   "generalize while distilling" rule. Result: zero engine-behavior
   bugs in the field — the `is_lost` defect class that shipped in two
   prior empty-seed rounds was absent from all five candidates.
3. **Constructed review environment, CLI-grade** — the reviewer ran in
   a fresh single-commit repo built from base tree + labeled diffs +
   gate notes only (no `farnsworth.json`, no worker-named refs),
   using the review code added to the CLI from run 3's queued
   refinements.

The round's headline finding: **the gate's blind spot got a new
exemplar.** All five candidates passed all six mechanical checks —
including `plays-ascii` — while three of them collapsed SPEC section
10's five growth stages to 1, 2, or 4 distinct glyphs in ASCII mode.
Exit codes and character purity are gate territory; *meaning* (five
observably distinct stages) needed the reviewer. Verdict: ADOPT E
(Sonnet 4.6, readability focus), the only candidate with five distinct
ASCII stages AND single-sourced end-screen text. The
accessibility-focused candidate shipped the worst ASCII display —
fourth round of evidence that foci shape investment, not outcomes.

| Metric | task-001 (10 seed tips, 5 workers, whole-program grain) |
|---|---|
| First-pass gate rate | 5/5 (six checks) |
| Engine-behavior bugs in field | 0 |
| Spec-deviation defects in field | 3 (ASCII stage collapse) |
| Verdict | adopt |
| Winning model (focus) | Sonnet 4.6 (readability) |
| Worker agent tokens | ~256k |
| Reviewer tournament tokens (share) | ~101k (39%) |
| Goal attestation tokens | ~68k |
| Iterations to goal | 1 |

Play it:

```bash
cd examples/word-garden-5
python3 -m word_garden            # emoji mode
python3 -m word_garden --ascii    # ASCII fallback
python3 -m word_garden --difficulty hard
python3 -m unittest discover -s tests   # 88 tests
```

Read the run, in order: `GOAL.md` → `tasks/task-001.md` →
`.farnsworth/task-001/` (candidates, blind-sketch.md, review.md,
verdict.json, goal-attestation.md, run.json, summary.md,
candidate-mapping.json) → `.code-tips.md` (seed v2 + tips 11–15) →
`.farnsworth/orchestrator-log.md` (process findings) →
`.farnsworth/git-log.txt`.
