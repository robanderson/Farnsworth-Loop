# Proposal: Improvement Rounds (the bounded Ralph)

Status: RATIFIED & IMPLEMENTED 2026-06-13 — PRD Section 2.7 is the
normative form; shipped as `goal.improvement_rounds` + the
`farnsworth improve` verb (briefing / `--apply` ratchet validation),
the `farnsworth-improver` role, the workflow's Improve phase, and
`tests/test_improve.py`. This document is kept for the design
rationale and the pattern mapping. Deltas from this draft: round
preconditions are read from the committed done/attestation artifacts
(no new state), proposed checks live in the round dir's
`done-checks.json`, and `done --json` carries
`improvement_rounds: {configured, completed, remaining}`.

## The idea

Today the loop's termination contract has exactly one success exit:
attestation passes → DONE → stop. Improvement rounds re-import the
Ralph loop's one genuine virtue — it keeps going — but bounded and
self-evaluating, the Farnsworth way:

- At ignition, alongside fleet confirmation, the run asks ONE more
  question: **how many improvement rounds?** (default 0 = today's
  behavior).
- When both halves of done pass and improvement rounds remain, the
  loop does not exit. The orchestrator spawns a new role — the
  **Improvement Agent (`farnsworth-improver`)** — which reviews the
  apparently-complete deliverable, asks and answers *"how can this be
  improved?"*, and AMENDS the goal contract with its answer. The loop
  then cycles again toward the amended goal.
- DONE is reached only when attestation passes with zero improvement
  rounds remaining — or earlier, if the improver honestly reports
  nothing worth a round (see the early-out rule).

Ralph persists blindly; Karpathy hill-climbs a number; Farnsworth with
improvement rounds persists **on purpose, against a contract it keeps
raising, a bounded number of times**.

## Why it fits the existing architecture cleanly

Every piece of the design maps onto a pattern the project already has:

| New piece | Existing pattern it mirrors |
|---|---|
| Improver amends `GOAL.md` (additive only) | Reviewer owns `.code-tips.md`; roles own artifacts |
| Improvements routed: mechanizable → `goal.done` checks, semantic → attestation criteria | Distillation routing: mechanical lessons → gate extensions, semantic → tips (PRD 2.6) |
| CLI writes `improvement-briefing.md`; agent follows it | Review briefing and attestation briefing: "a protocol traveling inside an orchestrator prompt is a protocol that drifts" |
| "Nothing worth improving" early-out carries the burden of proof | `adopt-final`'s inverted burden of proof (PRD 2.2) |
| Rounds counted from committed artifacts, not hidden state | Section 4.4: every decision reconstructible from git history |
| Improver's premise can be wrong → judge can still escalate the derived brief; attestor can refuse | The premise engine: nothing trusts the Professor blindly |

## The contract changes (PRD Section 2.4 amendment + new Section 2.7)

1. **Ignition gains one question.** The Fleet phase already confirms
   the field per run; it now also confirms `improvement_rounds`
   (default 0). Recorded in the orchestrator log like the fleet.
2. **The four exits are unchanged.** DONE simply moves to "attestation
   passes AND no improvement rounds remain". ESCALATED / STOPPED /
   STALLED apply inside improvement rounds exactly as in goal rounds —
   an improvement round that stalls is an automatic escalation, never
   silent spinning. The iteration budget (`maxIterations`) is GLOBAL
   across goal and improvement rounds.
3. **GOAL.md becomes append-only across rounds.** The original
   objective section is immutable; each round appends a labeled
   `## Improvement round N` section with provenance (improver, date,
   evidence pointer) — the same provenance discipline as tips entries.
   The improver may never weaken or remove an existing criterion.
4. **The early-out.** An improver that finds nothing attestable worth
   a round writes `improvement: none` with its reasoning, and the loop
   exits DONE with rounds unspent. Skipping a round carries the burden
   of proof, mirroring `adopt-final`. This keeps improvement rounds
   from degenerating into make-work — the Ralph failure mode this
   project exists to fix.

## The new role: `.claude/agents/farnsworth-improver.md`

Shape mirrors the attestor (tools: Bash, Read, Write, Glob, Grep):

- Spawned by the loop conductor only after attestation returns
  `goal_met: true` with rounds remaining; prompted with the CLI-written
  `.farnsworth/improvement-briefing.md` verbatim.
- Reads `GOAL.md`, the orchestrator log, `.code-tips.md`, and the
  merged code; **probes the deliverable empirically as a user** (runs
  it, plays it, feeds it hostile input) — never proposes from reading
  alone, the same empiricism rule every other role carries.
- Proposes a SMALL, coherent set of improvements (suggested 2–5) that
  are each attestable and gateable, within the spirit of the original
  objective: quality, UX, robustness, performance, features the goal
  implies. Not speculative scope explosion.
- Writes `.farnsworth/improvement-NNN/proposal.md` (what, why,
  evidence from probing), appends the `## Improvement round N` section
  to `GOAL.md`, and writes proposed mechanical checks to
  `.farnsworth/improvement-NNN/done-checks.json` for the trust layer
  to validate and install.
- Never writes project code. Improvements enter the codebase only
  through tournament tasks like every other change.

## Trust-layer changes (the Python CLI)

Smallest mechanical surface that keeps the loop honest:

1. **`config.py`:** parse optional `goal.improvement_rounds`
   (int ≥ 0, default 0) — the project default, confirmable per run
   like the fleet.
2. **New verb `farnsworth improve`:**
   - Bare: preconditions (done checks green, `attestation.json` with
     `goal_met: true`, rounds remaining counted from committed
     `.farnsworth/improvement-*/` dirs) → writes
     `.farnsworth/improvement-briefing.md`, exits 3 (awaiting
     delegation — improver agent next), same phase-boundary idiom as
     `run`/`gate`.
   - `--apply .farnsworth/improvement-NNN/`: validates the proposal
     mechanically — `GOAL.md` amended additively (prior content
     preserved verbatim as a prefix), proposed checks parse through
     the existing `_parse_check_list`, proposal.md non-empty — then
     merges the checks into the config's `goal.done` and reports the
     new round count. Exit 1 on a malformed proposal: the improver
     failed its artifact contract; re-spawn, never hand-patch.
3. **`farnsworth done --json`** gains an `improvement_rounds`
   object (`configured / completed / remaining`) so conductors never
   count state themselves.
4. **Tests:** config parsing, briefing writer, apply-validation
   (additive-only enforcement, check parsing, round counting from
   git-visible artifacts), and the done-payload extension — alongside
   the existing `test_goal.py` patterns.

## Conductor changes

- **`.claude/workflows/farnsworth-loop.js`:** `args.improvementRounds`
  (confirmed at launch with the fleet); after
  `attestation.goal_met === true`, if rounds remain: new `Improve N`
  phase — run `farnsworth improve` (exit 3), spawn the improver agent
  with the briefing verbatim, then a haiku agent runs
  `farnsworth improve --apply ...` and commits
  `"Good news, everyone! improvement round N armed: <one line>"`. The
  attestor's next refusal/pass measures the round. Exit DONE only when
  `goal_met` and no rounds remain.
- **`.claude/skills/farnsworth-loop/SKILL.md`** and the portable
  **`skills/farnsworth/SKILL.md`:** the ignition question and the
  improvement branch in the Attestation section, same wording.

## Docs

- **README:** the loop diagram gains the improvement arc
  (`DONE? → improvement rounds remain? → IMPROVE → go again`), and the
  Ralph/Karpathy/Farnsworth table gains the line: Farnsworth keeps
  going *on purpose* — bounded, self-directed improvement rounds
  against a contract it raises itself.
- **PRD:** amend Section 2.4 (exits unchanged, DONE definition
  extended), add Section 2.7 (this design), add the milestone
  (Section 9) — including the open question below.

## Open questions (deliberately not resolved here)

1. **Who judges the improver?** v1: nobody directly — the existing
   valves (judge can escalate a brief derived from a bad improvement;
   attestor can refuse an unmeetable criterion; STALLED bounds the
   damage) are the safety net, and the improvement proposal is a
   committed, diffable artifact a human can audit. v2 option: run the
   improvement itself as a design-task tournament (PRD 2.3 already
   blesses design tasks) — N improvers, anonymized, judged — when the
   deliverable is high-stakes.
2. **Budget shape.** One global iteration cap, or per-round caps?
   Proposed: global cap (simplest honest STOPPED), revisit after the
   first recorded run.
3. **Metrics.** Tag iterations with their round number in
   `done-checks.json` history and the orchestrator log so
   `farnsworth metrics` can later chart goal-round vs
   improvement-round economics.

## Suggested implementation order (each its own small slice)

1. PRD amendment + this proposal ratified.
2. `farnsworth-improver.md` role.
3. CLI: config parse → `improve` verb → `done` payload → tests.
4. Conductors: workflow, both skills.
5. README.
6. Dogfood: re-run a small example (the hangman-1 test project is
   sitting mid-tournament and would make a fine first recorded
   improvement-round subject) with `improvement_rounds: 1`.
