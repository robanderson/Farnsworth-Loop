# Wine Stock Report Generator 1 — the cross-domain run

The Farnsworth Loop's first subject outside the Word Garden family
(2026-06-12): a realistic small-business CLI from a wine-industry PRD —
warehouse stock-on-hand CSV in, human-readable Markdown stock report out,
with 9-litre-equivalent (9LE) totals, grouping summaries, low-stock
warnings, dry-goods handling, and data-quality warnings. The PRD
(`PRD.md`, with its embedded real fixture extracted to
`examples/stock_sample.csv`) is itself written as an agent benchmark;
this run used it to test whether the loop's machinery and accumulated
memory GENERALIZE beyond word games. Nothing in the loop was modified
for this subject.

Run shape (no new experimental variables): goal-driven (PRD 2.4,
`GOAL.md` + 7 mechanical done checks, budget 4 iterations),
whole-program grain (the entire program as task-001), the 12-entry
cross-project seed as `.code-tips.md`, focus-diversified 5-worker fleet
(2×Haiku 4.5, 2×Sonnet 4.6, 1×Opus 4.8), Opus reviewer — and the first
live use of **delegate dispatch** (PRD 4.1b): `farnsworth run` → host
session spawns worker subagents → `farnsworth gate` → reviewer subagent
→ `farnsworth finalize` → `farnsworth adopt --clean` → `farnsworth
done` → attestation subagent.

Exit: **DONE at 1 iteration**.

| Metric | task-001 (12 seed tips, 5 workers, whole-program grain) |
|---|---|
| First-pass gate rate | 5/5 (seven checks) |
| Behavioral bugs in field | 1 (parser over-rejection) |
| Spec-deviation defects in field | 1 (conditional Data Warnings section) |
| Test-quality defects in field | 2 (untested prompt seam; handle leaks) |
| Defects in seed-covered classes | **0** of 12 entries |
| Verdict | adopt |
| Winning model (focus) | **Opus 4.8** (report faithfulness) |
| Worker agent tokens | ~397k clean (+~124k recovery overhead) |
| Reviewer tournament tokens | ~108k (resumed dispatch) |
| Goal attestation tokens | ~82k |
| Iterations to goal (emergent) | **1** |

What the run added to the loop's evidence base:

1. **Cross-domain transfer of the seed pile, both directions again.**
   Zero defects in classes the 12 seed entries cover (no SystemExit
   swallow, no terminal-coupled logic, no silent filter fallbacks); all
   four field defects in classes no tip yet covered (conditional section
   rendering, tolerant-parser over-rejection, unexercised injection
   seams, test resource hygiene). Same signature as word-garden-5, in a
   domain the seed had never seen. Three new GENERALIZED entries
   distilled (`.farnsworth/task-001/seed-tips.next.md`).
2. **A new dispatch-failure class: worker self-delegation.** One worker
   spawned a nested agent and ended its turn "complete" with zero
   commits. The artifact rule caught it (commit log empty), the worker
   was re-dispatched with a do-not-delegate instruction, and its
   orphaned nested agent later finished in the same worktree — a
   duplicate absorbed, as ever, by commits-are-the-artifact.
3. **The review protocol's cleanup breaks on greenfield — found via a
   hung reviewer.** `git reset --hard` cannot remove an applied
   candidate made of NEW (untracked) files, and naive `git clean -fd`
   would destroy the untracked served diffs and reviewer notes. The
   resumed reviewer ran with `git clean -fd -e .farnsworth`; the CLI
   briefing fix is queued. The stalled dispatch's blind sketch was
   reused per the artifact rule.
4. **Focus-alignment ≠ advantage, from both directions in one round.**
   The verdict's discriminator was test rigor: the test-rigor-focused
   Haiku lost partly for an entirely untested prompt path, while the
   report-faithfulness-focused Opus won ON test rigor (the only
   candidate that hermetically drives the interactive contract).
5. **Preflight has a greenfield blind spot.** `gate-at-base` is red by
   design on a round-1 seed (the gate describes the deliverable), and
   one exit-code check passed at base for the wrong reason
   (module-not-found also exits 1). Queued: a greenfield-aware
   preflight diagnosis.
6. **Delegate dispatch works end-to-end.** First live run of the
   phased `run`/`gate`/`finalize` flow: worktrees, briefings, ledger,
   commit-as-artifact enforcement, hygiene gate, constructed review
   env, and verdict validation all CLI-mechanical; only the two agent
   phases (workers, reviewer) ran as host-session subagents. Two
   dispatch incidents (self-delegation, hung reviewer) — both absorbed
   without losing the round.

Run it:

```bash
cd examples/wine-stock-report-generator-1
python3 -m wine_stock_reporter examples/stock_sample.csv --no-interactive
python3 -m wine_stock_reporter examples/stock_sample.csv   # interactive
python3 -m unittest discover -s tests   # 73 tests
```

Read the run, in order: `PRD.md` → `GOAL.md` → `tasks/task-001.md` →
`.farnsworth/task-001/` (dispatch.json, briefings/, candidates/,
blind-sketch.md, review.md, verdict.json, run.json, summary.md,
code-tips.next.md, seed-tips.next.md) → `.code-tips.md` (seed + tips
13–18) → `.farnsworth/attestation.md` → `.farnsworth/orchestrator-log.md`
(process findings) → `.farnsworth/git-log.txt`.
