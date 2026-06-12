# Orchestrator Log — Word Garden

Process findings from running the Farnsworth Loop on its first external
project (the loop's own repo is the only prior subject). Per-task forensics
live in `.farnsworth/task-001/` and `.farnsworth/task-002/`; durable
engineering lessons live in `.code-tips.md`. This file is about the PROCESS.

Dispatch mode note: this run used MANUAL AGENT DISPATCH — the orchestrator
and reviewer were Claude agents, and workers were parallel sub-agents pinned
to git worktrees — because the managed sandbox could not authenticate a
nested headless `claude -p` (credentials are host-managed file descriptors
that child processes do not inherit). This is the same mode used to dogfood
tasks 001–002 of the loop itself. The blindness, anonymization, gate, and
verdict mechanics were followed exactly as the CLI implements them;
`farnsworth.json` records the fleet the CLI would have run.

---

## task-001 — Core engine (2026-06-11)

**Setup.** Full 5-worker fleet per PRD section 3: 2x Haiku 4.5, 2x Sonnet
4.6, 1x Opus 4.8, blind, parallel, one worktree each. `.code-tips.md` did
not exist yet. Gate: unittest + compileall.

**Gate.** 5/5 first-pass. File footprints identical across all five
candidates (low divergence; no round-2 trigger).

**Verdict.** ADOPT A -> unsealed to the OPUS worker. The reviewer found a
real contract bug in gate-passing candidate D (a Haiku): `is_lost` missing
the `not is_won` guard, so a win at exactly 0 water reports as a loss —
masked from the gate by a test-coverage gap. Other candidates were correct
with style/test-idiom weaknesses (fragile new-game-then-overwrite fixtures,
dead conditions, inlined message strings).

**Findings.**
1. Empty tips file -> strongest model wins, again (matches the loop's own
   task-001). Opus was also the cheapest worker of the round (~31k agent
   tokens, 12 tool calls vs Haiku's ~76k / 64 calls — fewer wasted motions).
2. The gate-vs-review division reproduced exactly: 5/5 passed mechanics,
   review caught a real semantic bug in a passing candidate.
3. Reviewer empirically verified candidates (applied diffs to scratch
   copies, ran suites, probed the won-at-zero-water edge) — this is where
   the D bug was confirmed, not in diff-reading alone.

**Cost.** Workers ~223k agent tokens total (w1 76k, w2 31k, w3 42k, w4 43k,
w5 31k); reviewer ~112k (~50% of worker spend).

**Distilled.** 21 lessons into `.code-tips.md` (state contract, is_lost
guard, win-before-loss ordering, single difficulty table, message
constants, direct-fixture testing, positive assertions).

---

## task-002 — UI, main loop, packaging (2026-06-11)

**Setup.** TRIAGED fleet per PRD section 8 (routine, well-specified task):
1x Haiku, 1x Sonnet, 1x Opus. Every briefing carried the 21 task-001
lessons. Gate: unittest + compileall + orchestrator smoke test (piped EOF
must exit 0; engine files byte-identical to base).

**Gate.** 3/3 first-pass.

**Verdict.** ADOPT A -> unsealed to the SONNET worker, beating Opus.
Zero correctness bugs in any candidate this round; the verdict turned on
test rigor (80 vs 55/56 tests), CLI exit-code correctness, and spec-faithful
ASCII stage glyphs. Runner-up C (Opus) lost on a single section-18
formatting deviation (weeds rendered as a fraction of water).

**Findings.**
1. The tips thesis held on an external project: with lessons in the
   briefing, a cheaper model beat Opus, and the field's floor rose from
   "one real logic bug" (round 1) to "zero correctness bugs" (round 2).
   The reviewer confirmed round-1 tips visibly shaped all three candidates
   (direct GameState fixtures, positive assertions, injected I/O).
2. One tip was NOT absorbed: none of the three reused the engine's MSG_*
   constants in the UI. Lesson re-distilled in stronger, imperative form —
   advisory ("prefer...") tips read as optional; contract tips need
   contract language.
3. Triage economics: total spend dropped (~206k vs ~335k agent tokens) but
   the reviewer's SHARE rose to ~68% of worker spend (83k vs 122k), since
   review depth is fixed while the field shrank. Triage saves absolute
   cost; it makes reviewer cost dominance worse, not better.
4. Task-type-specific gates earn their keep: the EOF smoke test and the
   engine-files-untouched check are not in `farnsworth.json` but were
   cheap, mechanical, and would have caught whole failure classes.

**Cost.** Workers ~122k agent tokens (haiku 47k, sonnet 39k, opus 36k);
reviewer ~83k (~68% of worker spend).

**Distilled.** 8 new UI-layer entries; 4 task-001 entries amended/tightened.

---

## Cumulative metrics (after 2 merged tasks)

| Metric                      | task-001 (no tips) | task-002 (21 tips) |
|-----------------------------|--------------------|---------------------|
| Fleet                       | 5 (2H/2S/1O)       | 3 (1H/1S/1O) triaged |
| First-pass gate rate        | 5/5                | 3/3                 |
| Correctness bugs in field   | 1 (gate-passing)   | 0                   |
| Verdict                     | adopt              | adopt               |
| Winning model               | Opus 4.8           | Sonnet 4.6          |
| Worker agent tokens         | ~223k              | ~122k               |
| Reviewer agent tokens       | ~112k (50%)        | ~83k (68%)          |
| Round 2 triggered           | no                 | no                  |

Verdict distribution: adopt 2 / synthesize 0 / escalate 0.
Win rate by model: Opus 1, Sonnet 1, Haiku 0 — and the win moved DOWN the
capability/cost ladder exactly when tips entered the briefing.
