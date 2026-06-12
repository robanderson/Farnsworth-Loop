# Orchestrator Log — Wine Stock Report Generator 1

First non-Word-Garden external subject (2026-06-12): a realistic
small-business CLI — warehouse stock CSV in, human-readable Markdown
stock report out — from the wine-stock PRD (`PRD.md`, with its embedded
real fixture extracted to `examples/stock_sample.csv`). The PRD is
itself written as an agent benchmark; this run uses it to test whether
the loop's machinery and accumulated process rules GENERALIZE beyond
the word-game domain. Nothing in the loop was modified for this
subject; the goal is generic process evidence, not a tuned demo.

Run design (all per the Farnsworth PRD, no new variables introduced):

- **Goal-driven** (Section 2.4): `GOAL.md` + 7 mechanical done checks
  seeded up front; one gap-derived task per cycle; exit decided by
  `farnsworth done` + reviewer attestation. Budget: STOPPED at 4
  iterations.
- **Whole-program grain** (Section 2.3 re-shot, attempt 1): the gap
  between seed and goal is the entire program, so task-001 dispatches
  all of it. If the done probe fails, the next gap-derived task may be
  a re-shot or a targeted fix — decided then, never pre-planned.
- **Seed v3** (M3): `.code-tips.md` starts as the current 12-entry
  cross-project seed pile (`seed-tips.md` at Farnsworth HEAD e73ac36),
  unmodified — first outing for entries 11–12 (fallback-mode semantic
  distinctness; presentation-neutral data fields) in a NON-game domain.
- **Focus-diversified dispatch** (Section 2.1): same generic foci as
  prior runs (test rigor / simplicity / readability / defensive
  robustness) plus a report-faithfulness lens for w5.
- **Delegate dispatch** (Section 4.1b), first live use: workers carry
  `model`, `farnsworth run` prepares and exits 3, this host session
  spawns one subagent per briefing (subscription-billed), then
  `farnsworth gate` / reviewer subagent / `farnsworth finalize`.
  Known trade-off: no per-worker `cost_usd` stream; agent token counts
  recorded here instead.

## Preflight (2026-06-12)

`farnsworth preflight`: config PASS (delegate, 5 workers, 7 gate
checks), git PASS, goal PASS, canary SKIP (delegate mode — manual
canary required), **gate-at-base FAIL — expected and accepted**:
4 of 7 checks are red at the seed commit because the package the gate
exercises does not exist yet. Process finding for the loop (generic):

- *Preflight's `gate-at-base` check models brownfield.* On a greenfield
  round-1 seed the gate is red BY DESIGN (it describes the deliverable,
  not the base), so "every candidate would gate against noise" is the
  wrong diagnosis: candidates are gated on their OWN worktrees after
  they implement. Preflight needs a way to distinguish "red base,
  greenfield round 1" (informational) from "red base, brownfield"
  (fatal). Queued as a CLI refinement.
- *A coincidental pass hides in the same blind spot:* the
  `missing-file` check (expects exit 1) passed AT BASE only because
  `python3 -m wine_stock_reporter` exits 1 for module-not-found.
  Exit-code gates can pass for the wrong reason; reviewer empiricism
  remains the backstop.

Manual delegate canary (per preflight's instruction): one Haiku
subagent in a scratch worktree — edit + python + commit all verified by
artifact (commit a86dead on the canary branch), debris swept. ~15k
agent tokens, 4 tool calls.

## task-001 — the whole program, one shot (2026-06-12)

**Derivation.** First cycle: the gap between merged state (seed only)
and GOAL.md is the entire program. Grain: whole-program one-shot.
Full 5-worker fleet — round 1 of a fresh project is the
ambiguous/consequential case the tournament exists for. Brief pins the
interface contracts the PRD leaves open (flat layout, exact CLI flags,
exit codes 0/1/2, EOF-accepts-defaults) and defers all behavior to PRD
sections by reference — the workers must read the PRD in their
worktrees; the brief is deliberately not a restatement of it.

**Dispatch ledger** (delegate mode, PRD 4.1b/4.3): `farnsworth run`
prepared worktrees + briefings and exited 3; five subagents spawned in
parallel, one per briefing, pinned to worktrees at base `1658e78`.
Phase boundary: commits on each worker branch; completion claims are
not the artifact.

**Worker phase events** (both documented dispatch-failure classes
appeared, both absorbed by the artifact rule):

1. **New failure shape: a worker DELEGATED its own attempt.** w3
   (sonnet) spawned a nested implementation agent and ended its turn
   reporting "the implementation agent is running" — zero commits on
   its branch, partial untracked scaffold in the worktree. The
   completion claim was checked against the artifact (commit log),
   found empty, and w3 was re-dispatched with an explicit
   do-not-delegate instruction. Lesson for the loop (generic): the
   worker preamble says commit-or-it-doesn't-exist, but says nothing
   about delegation; a worker that sub-delegates produces a
   plausible-sounding completion claim with no artifact. Queued: add
   "do the work yourself in this session; do not spawn sub-agents" to
   WORKER_PREAMBLE.
2. **Duplicate-dispatch signature, worker phase (5th run).** w5 (opus)
   found "pre-existing untracked scaffold modules" in its worktree it
   had not written — the already-present-scaffolding signature from
   runs 1–3 — reviewed them against the brief, kept them, and built
   the rest on top. w3's orphaned nested agent also completed later,
   in the same worktree as the re-dispatched w3 (duplicate work, one
   branch); whatever was committed is the candidate, the rest is
   noise.

**Workers returned** (agent tokens / tool calls; delegate mode has no
dollar stream):

| id | model | focus | tokens | calls | tests claimed | commit |
|----|-------|-------|-------:|------:|--------------:|--------|
| w1 | haiku-4.5 | test rigor | ~115k | 87 | 26 | a823e41 |
| w2 | haiku-4.5 | simplicity | ~98k | 70 | 23 | 212b8ed |
| w3 | sonnet-4.6 | readability | ~51k + ~100k resume (+~73k orphan) | 24+74 | 100 | 5850015 |
| w4 | sonnet-4.6 | defensive robustness | ~80k | 47 | 97 | 20e6167 |
| w5 | opus-4.8 | report faithfulness | ~104k | 44 | 73 | 17e0da3 |

Haiku-most-motion holds again for clean dispatches (w1 ~115k is the
field's max single-dispatch spend); w3's total including the recovery
is the round's true outlier, the price of the delegation failure.

**Gate.** 5/5 first-pass on all SEVEN checks (tests, compiles,
report-noninteractive, report-interactive-eof, help, usage-error,
missing-file). Hygiene: zero violations. Commit-as-artifact: enforced
mechanically (and it had already caught w3's first turn manually).
Test counts: 26 / 23 / 100 / 97 / 73.

**Divergence (M4 evidence).** Content divergence 0.6447 (mean pairwise
token-Jaccard over candidate diffs, 5 candidates; diffs 1.8k–2.7k
lines). File footprints near-identical again — the brief pins the
layout — so the content metric is doing the discriminating, as
designed. No approach scatter; review proceeds, no round-2 trigger.

**Anonymization.** Labels shuffled by the CLI, mapping sealed in the
dispatch ledger until finalize. Review environment constructed by the
CLI (`_construct_review_env`): base tree minus `farnsworth.json` and
prior artifacts, labeled diffs + gate notes only; the review briefing
was additionally COPIED INTO the env (the briefing references env-
relative paths; serving it inside the env spares the reviewer any read
outside its directory — small protocol refinement worth keeping).

**Review dispatch.** Opus subagent pinned inside the constructed env,
blind-sketch-first protocol per the CLI-written briefing; foci
disclosed sorted and unattributed.

**Review phase events.**

1. **Hung reviewer (documented class, PRD 4.3), stopped by the human
   operator.** The first reviewer dispatch wrote blind-sketch.md, then
   stalled mid-candidate-examination. Recovery per the artifact rule:
   the sketch artifact survives (not re-done), the env was swept back
   to base, the review phase re-dispatched. The verdict cannot be
   partial, so nothing of the stalled dispatch's probing is trusted.
2. **Root-cause candidate, and a generic protocol bug found by the
   stall: `git reset --hard` cannot clean a GREENFIELD candidate.**
   The CLI-written briefing instructs "git apply ... git reset --hard
   between candidates", but on a greenfield project a candidate diff
   creates only NEW files, which `git apply` leaves UNTRACKED — reset
   does not touch them. Forensics of the stalled env showed exactly
   that: an applied candidate sitting untracked on an otherwise clean
   base; the next `git apply` would then fail or stack candidates.
   Worse, the naive fix (`git clean -fd`) would delete the labeled
   diffs and the reviewer's own notes, which the env serves UNTRACKED
   under `.farnsworth/`. The re-dispatch carries the corrected
   procedure (`git reset --hard && git clean -fd -e .farnsworth`).
   Queued CLI refinements (generic): (a) the review briefing's step 2
   must prescribe reset+clean with the `.farnsworth` exclusion; (b)
   better, `init_review_repo` should COMMIT the served `.farnsworth/`
   contents in the review-base commit so plain `git clean -fd` is safe
   and the reviewer's notes survive any cleanup.

**Review returned** (resumed dispatch: ~108k agent tokens, 62 calls;
the stalled first dispatch's sketch was reused per the artifact rule).
All five candidates probed empirically. The gate's blind spot held to
form — every discriminating finding was invisible to the seven
mechanical checks:

- **A** (w1, haiku, test-rigor focus): most faithful report; interactive
  prompt path entirely UNTESTED (imports `prompt_for_options`, never
  calls it) — from the test-rigor-focused worker.
- **B** (w3, sonnet, readability): biggest suite (100 tests); DROPS the
  §19 Data Warnings section when the count is 0 — a conditional-section
  spec deviation on the canonical fixture.
- **C** (w4, sonnet, defensive robustness): faithful structure; its own
  suite leaks file handles (ResourceWarnings).
- **D** (w5, opus, report faithfulness): ADOPTED. Only candidate to
  hermetically test the interactive/EOF contract; §24 examples as named
  tests; assertions against imported message constants.
- **E** (w2, haiku, simplicity): thin suite (~23 tests, two §23
  categories missing); the field's one behavioral parsing bug
  (over-rejects a parseable `750ml/12p` inside an unusual description).

**Defect ledger, seed-attributed** (the run-5 pattern reproduces in a
new domain): zero defects in classes covered by the 12 seed entries
(no SystemExit swallow, no terminal-free violation, no re-typed
literals in the winner, no silent filter fallbacks). All four field
defects sit in classes NO tip yet covered: conditional section
rendering, tolerant-parser over-rejection, import-without-exercise
test seams, resource hygiene in tests. Reviewer distilled project tips
13–18 and three GENERALIZED seed candidates (always render contract
sections unconditionally; tolerant parsers keep-but-flag rather than
over-reject; an injection seam must be EXERCISED by tests, not merely
imported).

**Verdict: ADOPT D** -> unsealed to w5 (OPUS 4.8, report-faithfulness
focus). Focus-alignment ≠ advantage, fifth round of evidence, now from
BOTH directions in one round: the verdict's discriminator was test
rigor — the test-rigor-focused worker lost on an untested code path
while the report-faithfulness worker won on tests.

**Merge + distill.** D merged (`1a0ced8`); tips 13–18 installed from
code-tips.next.md (`94fd4c9`); seed-tips.next.md surfaced for the
cross-project pile. Worktrees + review env swept (`adopt --clean`;
w2's worktree needed `clean --force` for its own scratch reports —
candidate diffs were already archived).

**Done probe, iteration 1.** `farnsworth done`: all SEVEN mechanical
checks PASS. Attestation dispatched against the merged state for the
semantic half.

**Attestation returned: GOAL MET** (~82k agent tokens, 42 calls).
Every semantic-half bullet verified empirically: §24 examples through
the real parser and CLI, all §20 warning classes fired against
constructed bad data, basis/grouping/dry-goods/threshold switches
visibly changing output, Decimal end-to-end, thousands separators, and
the anti-hardcoding probe (truncated copy: 392.00 9LE over 5 rows;
modified copy: total shifts by exactly +156 9LE). No residual gaps.

## Exit: DONE (1 iteration)

Both halves of the termination contract pass. As in word-garden-5, the
whole-program grain met the goal in one iteration, so the re-shot's
attempt-2 measurement did not trigger — the contingent grain priced
correctly again, now in a second domain.

## Cumulative metrics (1 merged task, goal complete)

| Metric | task-001 (12 seed tips, 5 workers, whole-program grain) |
|---|---|
| Fleet | 5 (2H/2S/1O), delegate dispatch (first live use) |
| First-pass gate rate | 5/5 (seven checks) |
| Behavioral bugs in field | 1 (E: parser over-rejection) |
| Spec-deviation defects | 1 (B: conditional Data Warnings section) |
| Test-quality defects | 2 (A: untested prompt path; C: handle leaks) |
| Defects in seed-covered classes | **0** (12 entries audited) |
| Verdict | adopt |
| Winning model (focus) | Opus 4.8 (report faithfulness) |
| Worker agent tokens | ~397k clean + ~124k w3-recovery overhead |
| Reviewer tournament tokens | ~108k resumed (+ stalled dispatch, unmeasured) |
| Goal attestation tokens | ~82k |
| Dispatch incidents | 2 (worker self-delegation; hung reviewer) — both recovered by the artifact rule |
| Round 2 triggered | no (divergence 0.64, recorded) |
| Iterations to goal | **1** — exit DONE |

Verdict distribution: adopt 1 / synthesize 0 / escalate 0.

## What this run changes about the loop (generic, queued for the CLI/PRD)

1. **Worker self-delegation is a new dispatch-failure class.** A worker
   that spawns a sub-agent and ends its turn produces a confident
   completion claim with zero artifact. The artifact rule caught it;
   the preamble should prevent it: WORKER_PREAMBLE gains a
   do-the-work-yourself / never-delegate rule.
2. **The review protocol's cleanup instruction breaks on greenfield.**
   `git reset --hard` cannot remove an applied candidate that consists
   of new (untracked) files, and naive `git clean -fd` would destroy
   the untracked served diffs and reviewer notes. The briefing must
   prescribe `git reset --hard && git clean -fd -e .farnsworth`.
   Likely contributed to the hung first review dispatch.
3. **Preflight needs a greenfield mode for gate-at-base.** On a
   round-1 seed the gate is red BY DESIGN; preflight currently calls
   that fatal. Also observed: an exit-code check passing at base for
   the wrong reason (module-not-found == expected exit 1).
4. **`run`/`prepare` and `adopt` disagree about untracked
   `.farnsworth/` files.** `adopt` tolerates them as expected
   orchestrator state; `prepare` refuses to start. The orchestrator
   log had to be committed mid-flow to proceed — harmless here, but
   the asymmetry is unprincipled.
5. **Serve the review briefing INSIDE the review env.** Copying
   review-briefing.md into the constructed env spares the reviewer any
   read outside its directory; the CLI should do this in `gate`.
6. **The seed-attribution thesis generalizes across domains.** First
   non-game subject: zero defects in seed-covered classes, all four
   defects in uncovered classes — the same both-sides signature as
   word-garden-5, in a CSV/reporting domain the seed had never seen.
