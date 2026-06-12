# Orchestrator Log — Word Garden 5

Fifth Word Garden run (2026-06-12). The first GOAL-DRIVEN run: this
project is seeded with a goal contract (`GOAL.md` + `goal.done` checks in
`farnsworth.json`, PRD Section 2.4), and the loop cycles one
gap-derived task at a time until `farnsworth done` AND the reviewer's
semantic attestation both pass. No task list exists in advance — the
run-4 failure mode (a pre-authored two-task pipeline treated as the job)
is the specific thing this design forbids.

Two further firsts:

1. **Whole-program grain.** task-001 dispatches the ENTIRE game as one
   task (the re-shot grain's attempt 1, queued in examples/README.md
   since run 3). If the loop cycles again, the gap — not a plan — decides
   whether the next task is a re-shot or a targeted fix.
2. **Seed v2.** The 10-entry cross-project seed includes, for the first
   time, the GENERALIZED form of the `is_lost` predicate lesson (entry
   10) — the run-3 refinement "generalize while distilling" going live.
   Hypothesis: the one behavioral defect class that survived run 3's seed
   (standalone predicate relying on caller check order) does not appear
   in this run's field.

Also live for the first time: the CLI's constructed review environment
and protocol-carrying review briefing (implemented today from run 3's
queued refinements — reviewer runs in a fresh single-commit repo built
from base tree + labeled diffs + gate notes, with farnsworth.json and
prior artifacts stripped).

## Dispatch mode

Attempted CLI-native first (`python3 -m farnsworth run`): a smoke test
proved the whole pipeline mechanically — worktrees, parallel dispatch, a
real Haiku worker authenticating, committing, and passing the gate, the
review environment constructed and stripped correctly — but nested
`claude -p` authentication in this managed sandbox turned INTERMITTENT
mid-smoke (host-managed OAuth file descriptor, not inherited by child
shells; the documented PRD Section 8 risk, previously absolute, now
flaky which is worse). Reverted to MANUAL AGENT DISPATCH (orchestrator
and reviewer as agents, workers as parallel background sub-agents pinned
to worktrees) — same mode as all four prior runs — but using the CLI's
own code for the protocol surfaces it now implements: briefings via
`farnsworth.loop.build_briefing`/`focus_briefing`/`build_review_briefing`,
review environment via `_construct_review_env`/`_copy_back_review_artifacts`,
summary via `farnsworth.report`, termination via `farnsworth done`,
debris via `farnsworth clean`. `farnsworth.json` records the emulated
fleet.

---

## task-001 — the whole game, one shot (2026-06-12)

**Derivation.** First cycle: the gap between merged state (seed only) and
GOAL.md is the entire game. Grain: whole-program one-shot (re-shot
attempt 1). Full 5-worker fleet — round 1 of a fresh project is exactly
the ambiguous/consequential case the tournament exists for.

**Dispatch ledger** (manual mode, PRD 4.3): five background sub-agents
dispatched in parallel at base commit `4574249`, one per worktree
(`../task-001-w1..w5`), briefings built by `farnsworth.loop.build_briefing`
+ `focus_briefing` (10-entry seed + brief + focus + precedence sentence).
Foci: w1 test-rigor (haiku), w2 simplicity (haiku), w3 readability
(sonnet), w4 defensive-robustness (sonnet), w5 accessibility/display
(opus). Phase boundary: commits on each worker branch; agent completion
claims are not the artifact.

**Workers returned.** All five completed without hangs — the first run
with NO duplicate-dispatch signature in the worker phase (prior three
runs saw "already present scaffolding" retries every round). Exactly one
clean commit per branch.

**Gate.** 5/5 first-pass on all SIX checks (tests, compiles, plays-eof,
plays-ascii, help, usage-error — the per-task mechanical extensions
runs 1–3 bolted on are first-class gate config in this run). Hygiene:
zero violations across the field. Test counts: w1 85, w2 75, w3 88,
w4 98, w5 59. Worker agent tokens: w1 ~64k/66 calls, w2 ~61k/49,
w3 ~40k/27, w4 ~45k/29, w5 ~46k/22 — the Haiku-most-motion pattern
holds for the fourth run (both Haikus out-spent every Sonnet and the
Opus); leanest attempt was a Sonnet (w3).

**Divergence (M4 evidence, fourth confirmation).** File footprints
IDENTICAL across all five candidates — even at whole-program grain, a
layout-pinning brief makes footprint comparison measure the brief.
Content divergence high: pairwise candidate-diff deltas 2.2k–3.2k lines,
test counts 59–98. No approach scatter; review proceeds, no round-2
trigger.

**Anonymization.** Labels shuffled and sealed outside the repo
(`../task-001-mapping.sealed.json`) until post-verdict. Review
environment constructed by the NEW CLI code (`_construct_review_env`):
base tree, no `farnsworth.json`, no worker refs, labeled diffs +
gate-notes only. First live use of the constructed-env code caught a
real briefing bug: `build_review_briefing` referenced diffs at
`candidates/X.diff` but the env serves them at
`.farnsworth/task-001/candidates/X.diff` — the smoke test's fake
reviewer globbed instead of following the briefing path, so only a live
read could catch it. Fixed in the CLI before reviewer dispatch.

**Review dispatch.** Opus, blind-sketch-first protocol briefing built by
the CLI's `build_review_briefing`, plus a per-seed-entry audit
requirement. Foci disclosed sorted and unattributed.

**Review returned.** Blind sketch written first; all five candidates
applied and probed empirically in the constructed environment. The
reviewer's discriminating signal was one the gate provably cannot see:
SPEC-10 growth-stage DISTINCTNESS under `--ascii`. Distinct ASCII stage
glyphs per candidate: A=1, B=2, C=5, D=4, E=5 — three of five
gate-passing candidates ship a real spec deviation, and the
`plays-ascii` gate (exit 0 + purity) passes all of them. Second
discriminator: tip-7 single-sourcing — C defines win/loss header
constants then leaves them dead while ui.py re-types the literals.

**Verdict: ADOPT E** -> unsealed to w3 (SONNET 4.6, readability focus).
Zero engine-behavior bugs in the field — the seed v2 hypothesis held:
the generalized predicate entry (tip 10) was honored by all five
candidates (every is_lost carries its own not-won guard; reviewer
verified the boundary directly), the defect class that shipped in two
prior projects' empty-tips rounds. The defects that DID appear (ASCII
stage collapse, dead constants) are NEW classes, now distilled as tips
11–15.

**Focus observations.** The focus-aligned candidate lost on its own
dimension again: the accessibility-focused Opus (B) shipped the
2-distinct-glyph ASCII collapse, while readability Sonnet (E) had the
faithful display. Foci shape investment, not outcomes — third
consecutive round of evidence.

**Reviewer cost.** ~101k agent tokens, 58 calls (~39% of the ~256k
worker spend — the lowest reviewer share recorded; the constructed
environment with pre-labeled diffs may be reducing review overhead vs
prior runs' ad-hoc setups).

**Merge + distill.** E merged to main (`c8271d3`); tips 11–15 installed
by the orchestrator from the reviewer's code-tips.next.md ("Good news,
everyone!" commit `861a002`); audit artifacts committed (`a82f67e`).

**Done probe, iteration 1.** `farnsworth done`: all six mechanical
checks PASS. Semantic attestation dispatched to the reviewer against
the merged state — the goal contract requires both halves before the
loop may stop. The whole-program grain means a single iteration CAN
complete the goal; whether it does is the attestation's call, not the
orchestrator's.

**Attestation returned: GOAL MET.** Every semantic-half bullet verified
empirically against the merged state (pinned-word win and loss through
the real CLI, five distinct stages in both modes — emoji 🌱🌿🌷🌻🥀,
ASCII `*`/`+`/`^`/`@`/`x` — accessibility shapes, difficulty table,
no word-list accidents). One non-blocking observation recorded: the
easy pool contains only 6-letter words, a property of the SPEC's
word list, not a filtering defect. The duplicate-dispatch signature
reappeared HERE: the attestation agent found goal-attestation.md
already written by its own duplicated dispatch, verified it against
independent evidence, and left it intact — the artifact-boundary rule
absorbing a duplicate for the fourth run in a row (worker phase stayed
clean this run; the signature moved to the attestation phase).

## Exit: DONE (1 iteration)

Both halves of the termination contract pass. The goal-driven design
ended the loop at one iteration because nothing was left to derive a
task from — the re-shot grain's attempt-2 measurement therefore never
triggered. This is the design behaving correctly (a forced second
iteration would be the run-4 pre-planned-pipeline mistake in reverse),
and it prices the re-shot honestly: it only happens when attempt 1
fails the goal, so it measures learning exactly when there is
something to learn.

## Cumulative metrics (1 merged task, goal complete)

| Metric                       | task-001 (10 seed tips, 5 workers) |
|------------------------------|-------------------------------------|
| Fleet                        | 5 (2H/2S/1O), whole-program grain  |
| First-pass gate rate         | 5/5 (six checks)                   |
| Engine-behavior bugs in field| 0                                  |
| Spec-deviation defects       | 3 (ASCII stage collapse: A,B,D)    |
| Contract/tips defects        | 1 (C: dead constants re-typed)     |
| Verdict                      | adopt                              |
| Winning model (focus)        | Sonnet 4.6 (readability)           |
| Worker agent tokens          | ~256k (w3 leanest at ~40k/27)      |
| Reviewer tournament tokens   | ~101k (39% of worker spend)        |
| Reviewer attestation tokens  | ~68k                               |
| Round 2 triggered            | no                                 |
| Iterations to goal           | 1                                  |

Verdict distribution: adopt 1 / synthesize 0 / escalate 0.

## What this run changes about the loop

1. **Goal-driven cycling works and stops honestly.** First run under
   the PRD 2.4 contract: the gap derived exactly one task, the done
   probe + attestation ended the loop at one iteration. The run-4
   failure mode (finish-the-list-and-stop) is structurally absent when
   the next task is derived post-merge and `farnsworth done` owns
   continuation.
2. **Seed v2 validated the generalization rule.** The generalized
   predicate entry (tip 10) suppressed the `is_lost` defect class in
   all five candidates — the exact class that recurred when the lesson
   was project-scoped. Three data points now: lessons prevent
   precisely what their scope covers; generalizing at distillation
   time widens that scope for free.
3. **The gate's blind spot has a new exemplar.** Three of five
   candidates passed `plays-ascii` while collapsing the five growth
   stages to 1–4 glyphs. Mechanical checks verify exit codes and
   character sets, not meaning; distinctness needed a reviewer. Tips
   11–15 now encode it for every future round.
4. **Constructed review environment + protocol briefing earned their
   keep on first CLI use.** No anonymization leak; the reviewer
   followed the briefed protocol end to end (sketch, per-candidate
   empirical probes, seed audit, distillation, progression-in-verdict).
   First live read of the briefed diff path also caught a path bug the
   fake-reviewer smoke test could not see — live-fire the briefing
   text, not just the plumbing.
5. **Reviewer share fell to ~39%** of worker spend for the tournament
   (101k vs 256k), the lowest recorded — but the goal contract adds an
   attestation dispatch (~68k) per goal completion, a new fixed cost
   the PRD's economics should name.
6. **Focus-alignment is not advantage, fourth round of evidence.** The
   accessibility-focused candidate shipped the round's worst ASCII
   display; readability won on display faithfulness.
7. **Duplicate dispatches: the signature moved phases.** Worker phase
   clean for the first time, but the attestation dispatch duplicated.
   The artifact-boundary rule absorbed it without incident — including
   for a NEW artifact type (goal-attestation.md), which is the rule
   working generically, not by case-handling.
