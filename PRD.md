# Farnsworth Loop: Reference Implementation PRD

> The project's public face lives in [README.md](README.md); this
> document is the specification of record and the lab notebook — every
> design decision, every recorded run, every distilled lesson.

**Author:** Rob Anderson
**Date:** 12 June 2026
**Status:** Draft v2.1 (v1.1 revised 11 June 2026 after dogfooding tasks 001–002 — yes, the loop shipped a day before its own PRD date; v1.2 folds in the 12 June hardening pass: preflight, metrics, adopt, recorded divergence, mechanical hygiene gate, cost capture, goal artifacts; **v2.0, 12 June 2026 evening,** adopts the two-phase explore→rebuild task loop, gate-1 as evidence, the champion mechanism, Phase-0 objectives interview, smallest-gateable-slice derivation, and requirements grammars — Sections 2, 2.2, 2.3, 2.5, 2.6 — distilled from the wine-stock run, Section 17, and the operator design review that followed it. The CLI implements the v1 flow until M7. **v2.1, same day:** delegate dispatch is now the default and the only sanctioned mode for Anthropic models — the June 2026 subscription caps on `claude -p` make subprocess dispatch wrong for parallel fleets; `claude -p` is repositioned as the future third-party adapter (GLM, MiniMax, Qwen, local). Sections 3, 4.1/4.1b, 8; the CLI's built-in default fleet is delegate.)
**Repo:** farnsworth-loop

-----

## Quickstart

```bash
cd your-project                  # a clean git repo with farnsworth.json
python3 -m farnsworth preflight  # canary the fleet config BEFORE spending
python3 -m farnsworth run tasks/task-001.md   # worktrees + briefings (exit 3)
# spawn one subagent per briefing from the orchestrating Claude Code
# session (delegate dispatch -- subscription-billed, Section 4.1b)
python3 -m farnsworth gate task-001           # gate, anonymize, review briefing (exit 3)
# spawn the reviewer subagent pinned to the constructed review environment
python3 -m farnsworth finalize task-001       # validate verdict; run.json + summary
python3 -m farnsworth report task-001         # the thirty-second table
python3 -m farnsworth adopt task-001 --clean  # merge winner, install tips, sweep
python3 -m farnsworth done       # goal probe: exit 0 done / 1 keep looping
python3 -m farnsworth metrics    # cross-run health table from all run.json
```

From a Claude Code session the whole sequence ships as a packaged
workflow (Section 4.1c): `/farnsworth-task tasks/task-001.md` runs one
tournament round end-to-end — the orchestrating session spawns the
`farnsworth-coder` and `farnsworth-judge` subagents at the two exit-3
boundaries itself — and `/farnsworth-loop` cycles tasks until the goal
is done, dispatching the `farnsworth-attestor` for the semantic half.

(Subprocess `command` fleets — the third-party adapter, Section 4.1 —
collapse the first three steps into one: `farnsworth run` dispatches,
gates, and reviews end-to-end.)

Sections 1–2 are the why and the protocol; Section 5 is the CLI's scope;
the `examples/` directory holds complete forensic records of real runs.

-----

## 1. Thesis

Agent loops differ on one axis: what flows through the feedback path.

- **Ralph Loop:** no feedback. Same prompt, fresh context, persistence as strategy. Open-loop control.
- **Karpathy Loop:** scalar feedback. Keep or discard against a metric. A thermostat. Requires a cheap, evaluable metric, which most software work does not have.
- **Farnsworth Loop:** semantic feedback. An intelligent review phase distills verbal lessons from every attempt (winners and losers) into a persistent knowledge artifact that is injected into every future worker briefing. The models never get smarter; the project does.

The defining property: **failures are not wasted tokens, they are gotchas passed forward.** Knowledge compounds in the context layer, where it is inspectable, diffable, and versioned in git alongside the code it describes.

This PRD specifies a minimal reference implementation using the Anthropic ecosystem only.

> **Dogfooding status:** M1 and M2 were themselves built by running the loop — five blind parallel workers per task, mechanical gate, anonymized Opus review, verdict, distillation. The thesis has its first data: the round-1 winner (empty tips file) was Opus; the round-2 winner (14 distilled lessons in the briefing) was Haiku. Same models, better project. See Section 11 and `.farnsworth/orchestrator-log.md`.

## 2. Core Loop (v2: explore → distill → informed rebuild)

> **v2, adopted 2026-06-12** after the wine-stock run (Section 17) and
> the operator design review that followed it. The two-round structure
> is now the SPINE of every task, not a divergence-triggered exception
> (rationale and history in Section 2.2). All recorded example runs
> predate v2 and executed the v1 single-round task flow preserved in
> git history.

```
GOAL (Phase 0 objectives interview -> business objectives + done checks)
  |
  v
derive next TASK from the goal gap (smallest gateable slice, Section 2.3)
  |
  v
ROUND 1 -- EXPLORE
  -> DISPATCH (parallel, blind; wide, cheap, focus-diversified)
  -> GATE-1   (mechanical; EVIDENCE for the review, never a filter)
  -> REVIEW   (anonymized; probe the passers, idea-mine the failers)
  -> VERDICT-1 (champion from the passers | no champion | escalate)
  -> DISTILL  (lessons -> tips; mechanizable lessons -> gate extensions)
  |
  v
ROUND 2 -- INFORMED REBUILD
  -> DISPATCH (parallel, blind, CLEAN SLATE: brief + distilled lessons;
               round-1 code never travels -- only the champion stands)
  -> GATE-2   (mechanical, STRICT, including the ratcheted extensions)
  -> REVIEW   (anonymized; round-2 field + champion, relabeled together)
  -> VERDICT-2 (adopt | synthesize | escalate)
  -> DISTILL  (update .code-tips.md)
  |
  v
MERGE -> done check ----no----> derive next TASK (cycle continues)
            |          (round 2 yields nothing adoptable: distill again
           yes          -> ROUND 3, bounded by the STALLED rule, 2.4)
            |
            v
          STOP (goal complete)
```

It is a LOOP twice over: rounds repeat within a task until something is
adoptable, and tasks repeat until the primary goal is complete — 2
cycles for a small brief, 200 for a hard one (Section 2.4 defines the
continuation and termination contract). Every task now produces the
attempt-1 → attempt-2 delta on the same problem — the loop's cleanest
direct measurement of learning, which six v1 runs never produced.

One task in detail:

1. **Dispatch, round 1 (explore).** Orchestrator creates one git worktree per worker and dispatches the same task brief to all workers in parallel. Each brief is: current `.code-tips.md` + task specification + an optional per-worker **focus directive** (Section 2.1), with round-1 foci aimed at the Phase-0 open design questions. Workers run blind: no worker sees another worker’s output, no worker sees another worker’s focus, and no worker sees its own prior attempts. Exploration semantics: the field is wide and cheap by preference — gate-1 no longer requires merge-ability for a candidate to contribute, so round 1 buys breadth per dollar and is judged by what it teaches as much as by what it ships.
1. **Gate-1 (evidence, not filter).** Every gate command runs in every worktree, and the results travel WITH each candidate into review. Gate-1 excludes nobody: a candidate with a novel approach that does not stick the landing is often the round's most distillation-rich artifact, and a filter would discard it exactly when the field is struggling — when learning matters most. (v1 reduced failures to one-line autopsies and deep-read only winners; the thesis said failures are gotchas passed forward, and the v1 protocol was quietly dishonest to it.) The commit-as-artifact and hygiene checks still disqualify a candidate outright — no commits or a violated contract is a non-submission, not an interesting failure.
1. **Review, round 1.** The reviewer receives ALL candidate diffs labeled A, B, C in randomized order with no model attribution, each with its gate-1 evidence, and reviews in two depth tiers to keep cost sane: gate-passing candidates get the full empirical probe; failing candidates get idea-mining — read the diff for the approach and the trap, never debug it. The review covers what is good AND bad in each implementation, not just a ranking. The reviewer must sketch its own approach BEFORE reading candidates (anchoring defence).
1. **Verdict-1.** Selects the **champion** — the best gate-PASSING candidate — which survives unchanged into round 2's tournament. No passer means no champion: round 2 runs on lessons alone. Verdict-1 may instead **escalate** (the task specification itself is wrong; hints never silently amend the contract) or, rarely, **adopt-final**: the reviewer attests the champion is clean AND the field taught nothing worth a rebuild — skipping round 2 carries the burden of proof, never invoking it.
1. **Distill, round 1.** The reviewer writes the defect ledger and the field's lessons, routed by enforceability: semantic lessons become tips in `.code-tips.md`; mechanically-expressible lessons (structure, cardinality, exit codes — Section 2.6) become per-task **gate extensions** that ratchet gate-2. Under rebuild semantics, design-level lessons are legitimate distillation ("the streaming parse proved cleaner than the whole-file regex") — round 2 is SUPPOSED to converge on what round 1 taught, and the champion is the control. Lessons travel; code does not. Only the review phase may write the tips file; workers are read-only consumers. Commit message convention: `Good news, everyone! <summary of lesson>`.
1. **Dispatch, round 2 (informed rebuild).** Clean slate: fresh blind workers, original brief + updated tips + round-1 lessons, foci re-aimed at the defect ledger — and never round-1 diffs. Round 1's code is thrown away by design: code is the cheap part, lessons are the asset, and the goal is a better outcome, not a patch of what came before.
1. **Gate-2 (strict).** The full gate including the round-1 extensions. Round-2 candidates must pass to be adoptable.
1. **Review + Verdict-2.** The champion is relabeled into the round-2 field and the whole field is reviewed BLIND — the verdict-2 reviewer must not know which candidate is the champion, which models produced what, or which round anything came from. Exactly one of three outcomes:
- **Adopt:** one candidate is correct and complete; merge it as-is. The champion surviving verdict-2 is a NEGATIVE learning result (informed rebuild failed to beat blind exploration) and is recorded in the run log and metrics, never hidden.
- **Synthesize:** no candidate is adequate but the field contains usable insight; the reviewer authors a fresh implementation informed by the candidates and critique, anchored by its pre-written blind sketch.
- **Escalate:** the task specification itself is wrong or ambiguous; file a change request to the orchestrator.
1. **Merge.** Winning diff merges to main. Worktrees are destroyed. The done check (Section 2.4) decides continuation. If round 2 produced nothing adoptable, distill again and dispatch round 3: every round past 2 must show measurable progress against the defect ledger and gate checks, or the task STALLS into escalation — persistence alone is the Ralph loop wearing our clothes.

### 2.1 Focus-Diversified Dispatch

Each worker may carry a one-line focus directive in `farnsworth.json` —
"Focus on runtime speed", "Focus on security", "Focus on minimal
dependencies", "Focus on readability and maintainability", "Focus on test
rigor and edge cases", … The purpose is to FORCE the blind field apart:
identical briefings to same-family models produce convergent candidates
(observed: identical file footprints in every round run so far), which
starves both the review and the two-round trigger of signal. A focused
field searches more of the code space in round/task 1 and hands the
reviewer genuinely varied implementations whose distilled trade-offs feed
round/task 2.

Rules:

- **A focus is a lens, never a contract amendment.** The dispatch wrapper
  appends the directive with an explicit precedence sentence: the task
  brief and its acceptance criteria always win. A candidate that uses its
  focus to deviate from the spec loses in review like any other deviation.
- **Foci stay blind in review.** The review briefing discloses the round's
  directives as a sorted, UNATTRIBUTED set — the reviewer should know the
  field was deliberately diversified (so divergence is not misread as task
  ambiguity), but a per-candidate focus would link labels to worker specs
  and break anonymization. The mapping unseals with the rest post-verdict.
- **Recorded, not hidden.** Each worker's focus lands in `run.json` and in
  the run summary table, so per-focus win rates accumulate alongside
  per-model win rates (Section 7).
- **Round 2 narrows.** (v2: every task, not just triggered re-runs.)
  Round 1's foci aim at the Phase-0 open design questions — the branches
  of the decision tree the objectives interview certified as genuinely
  open (Section 2.5) — replacing the recycled generic lenses of early
  runs with diversification axes the task actually owns. Round 2's foci
  re-aim at the round-1 defect ledger: round 1 explores, distillation
  extracts what the exploration taught, round 2 converges on it.

### 2.2 The Two-Round Structure (the spine; formerly divergence-triggered)

v1 made the second round an exception: divergence across candidates
triggered a re-dispatch. It fired **zero times in ten recorded tasks** —
footprint-based measurement was blind under layout-pinning briefs, and
over-specified briefs kept fields convergent — while this PRD
simultaneously called the attempt-1 → attempt-2 delta "the cleanest
direct measurement of learning the loop can produce." Meanwhile every
recorded review found defects in gate-passing fields: the material for
an informed second round existed in 10 of 10 tasks. v2 resolves the
contradiction by making round 2 the default path of every task —
exploration, then distillation, then an informed clean-slate rebuild —
with `adopt-final` as the justified skip (the burden of proof inverted:
v1 required a trigger to run round 2; v2 requires an attestation to
skip it).

Rules carried forward and sharpened:

- **Lessons travel, diffs do not.** Round-2 workers receive the updated
  `.code-tips.md` and the round-1 lessons, never round-1 code.
  Distillation remains the anti-anchoring filter. The one designed
  exception is the **champion**, which enters round 2's REVIEW FIELD
  (not the workers' briefings), relabeled and unattributed — so "did
  learning beat blind exploration?" is decided blind by the verdict-2
  reviewer, not assumed by the orchestrator.
- **Divergence is recorded, not a trigger.** The content-based metric
  (mean pairwise token-Jaccard, in `run.json` since v1.2) now informs
  round-2 sizing and review depth — a convergent round-1 field needs a
  smaller, more targeted round 2 — instead of gating whether round 2
  happens at all.
- **Rounds past 2 are failure handling, not exploration.** They occur
  only when verdict-2 adopts nothing, and each must show measurable
  progress (defect ledger shrinking, more gate-2 checks passing) or the
  task STALLS into escalation (Section 2.4).

### 2.3 Task Grain and Domain: the Loop Is Task-Agnostic

A task is exactly three things: a brief (opaque text), acceptance
criteria inside it, and a mechanical gate (configurable commands). The
loop's machinery — dispatch, worktrees, gate, anonymized review, verdict,
distillation — never inspects the task's content. Two consequences, both
load-bearing:

**Grain is the orchestrator's choice, not the protocol's.** Valid tasks
include: one-shot an entire program from a spec; a milestone slice of a
larger build; a bug fix; a refactor; a feature on a codebase the loop has
never seen. The Word Garden examples (Sections 12–14) happened to use
milestone slices (engine, then UI) — a choice made by those examples'
briefs, not a property of the loop. The most instructive grain for
MEASURING the loop is the **re-shot**: dispatch the whole problem as
task-001, distill the field's mistakes, then dispatch the same whole
problem again as task-002 — fresh blind workers, updated tips, no
attempt-1 diffs (the Section 2.2 rule, promoted from a
divergence-triggered exception to an explicit design choice). Attempt 2
REPLACES attempt 1; the attempt-1 → attempt-2 delta on an identical
problem is the cleanest direct measurement of "the project got smarter"
the loop can produce. Word Garden 5 (Section 16) ran the whole-program
grain as re-shot attempt 1 under the Section 2.4 goal contract — and
the goal was met in one iteration, so attempt 2 never triggered. That
is the re-shot priced correctly: it is a CONTINGENT grain, dispatched
only when the done probe says attempt 1 left a gap, so it measures
learning exactly when there is something to learn. The attempt-2
measurement remains unexercised.

**Domain is the gate config's business, not the loop's.** Nothing in the
protocol assumes Python, greenfield code, or a toy: point the loop at an
existing repository — a Gitea/Forgejo fork, a new MCP server, a
production service — and the gate becomes that project's own
build/test/lint commands in `farnsworth.json`, the tips file accumulates
that project's contracts, and briefs carry issues or change requests
instead of spec sections. The CLI's only domain-flavored piece is the
FALLBACK gate used when no `farnsworth.json` exists (`python3 -m unittest
discover`), which any real project overrides. Greenfield demo, brownfield
patch to a large Go codebase: same loop, different `farnsworth.json`.

**v2 derivation rule: the smallest gateable slice.** "Derive the next
task from the gap" returns the WHOLE gap at seed time — observed twice:
two consecutive goal-driven runs (word-garden-5, wine-stock) dispatched
the entire program as task-001 and exited DONE in one iteration, so the
within-project feedback path never fired and the loop degenerated into a
tournament with a memory. The orchestrator therefore derives the next
task as the smallest coherent slice of the goal gap that is
independently gateable and reviewable (a ratified output grammar makes
the seams visible — Section 2.6: unimplemented subtrees are candidate
slices). Iteration count stays emergent and the task list is still never
pre-authored; the slice rule only prevents the count collapsing to one
on a non-trivial goal. Whole-program grain remains valid for genuinely
small goals, and v1's re-shot grain is subsumed: the v2 round-2 rebuild
IS the re-shot, priced into every task.

**Design tasks are tasks.** A brief may ask for a document rather than
code — "write the PRD for this goal" — judged by the same machinery
(the loop never inspects task content). For design tasks the mechanical
gate is weak (structure and reference checks at best) and the review
carries nearly all the weight; the two-round structure is mandatory in
spirit as well as letter, since a design task is maximally ambiguous by
construction. The adopted design becomes a protected contract file like
any brief, amendable only by escalation. Phase 0 (Section 2.5) feeds
the design round its objectives and its open questions.

### 2.4 Loop Continuation: Cycling Until the Goal Is Done

The unit of progress is an iteration; the unit of COMPLETION is the goal.
The goal is declared up front — an objective brief (what done means, in
acceptance-criteria form) plus mechanical done checks in `farnsworth.json`:

```json
"goal": {
  "brief": "GOAL.md",
  "done": [
    {"name": "acceptance", "command": ["python3", "-m", "unittest", "discover", "-s", "tests"]},
    {"name": "plays",      "command": ["sh", "-c", "printf '' | python3 -m word_garden"]}
  ]
}
```

`farnsworth done` runs the checks against the merged state: exit 0 means
the goal is complete, exit 1 means keep looping, exit 2 means no goal is
configured (which is itself the bug — a loop without a termination
contract either stops early or never).

Rules:

- **One next task per cycle, derived from the gap.** After every merge
  the orchestrator re-reads the goal against the merged state and writes
  the NEXT task brief only. It MUST NOT pre-author the full task list at
  the start: a pre-planned pipeline ("task-001 engine, task-002 UI, then
  stop") is a waterfall wearing a loop's clothes — it cannot react to
  verdicts, distilled lessons, or escalations, and it hardcodes the
  iteration count that should be emergent. *(Observed in the wild: a
  run-4 orchestrator session planned exactly that two-task pipeline
  before the first dispatch and treated finishing the list as finishing
  the job.)* v2 sharpens the derivation: the next task is the SMALLEST
  gateable slice of the gap (Section 2.3), never the whole gap by
  default — the opposite failure mode, observed in two goal-driven
  runs, is a one-iteration exit that never exercises the loop.
- **Iteration count is emergent.** The brief's complexity decides whether
  the loop cycles 2 times or 200. Nothing in the protocol fixes it.
- **Done has two halves.** Mechanical: `farnsworth done` passes. Semantic:
  the reviewer attests, in its final review, that the goal brief's
  acceptance criteria are met by the merged state — and for Phase-0
  projects the attestation targets the BUSINESS objectives and the
  decisions ledger (Section 2.5), never merely a loop-authored design
  document, which may itself have drifted from intent (the same
  gate-vs-review division as Section 2's steps — the done checks filter
  mechanics, the reviewer filters meaning). Both halves are required to
  stop with outcome DONE. Both halves leave artifacts: every probe writes
  `.farnsworth/done-checks.json` (git history is the series — the raw
  material for STALLED detection), and a mechanical pass writes
  `.farnsworth/attestation-briefing.md`, the reviewer protocol for the
  semantic half (enumerate criteria, verify empirically, write
  `attestation.md` + `attestation.json` with `goal_met`). The CLI writes
  the protocol for the same reason it writes the review briefing: a
  protocol traveling inside an orchestrator prompt is a protocol that
  drifts.
- **Exactly four exits.** DONE (both halves pass); ESCALATED (a change
  request blocks all remaining work pending a human); STOPPED (a
  human-set budget or iteration cap ran out); STALLED (no measurable
  progress toward the done checks for 3 consecutive iterations — an
  automatic escalation, never silent spinning). Every exit is recorded in
  the orchestrator log with the iteration count.

### 2.5 Phase 0: The Objectives Interview ("grill me")

When a project starts from a raw request and an artifact (a paragraph
and a CSV; an issue and a codebase) rather than a finished spec, the
loop begins with an interview: the orchestrator grills the human owner
about the plan until shared understanding is reached, walking each
branch of the decision tree and resolving dependencies between
decisions one by one. The spec becomes an OUTPUT of the loop, not an
input — the run-6 lesson was that a finished, detailed PRD collapses
the decision space before the field ever runs (every interesting
verdict discriminator in that run sat in space the brief accidentally
left open).

Rules of the interview:

- **The altitude rule (the BA discipline).** Questions stay at business
  objectives and end-user outcomes; the technical HOW belongs to the
  loop. The test is ownership, not vocabulary: anything the owner has
  an opinion about AS A USER ("what stock number do you make purchasing
  decisions on?", "my team lives in Excel", "it must run on the
  warehouse PC with nothing installed") is interview territory;
  anything they would answer "whatever works" to (flags, layouts, exit
  codes, file formats of internals) is the field's decision space and
  MUST NOT be asked.
- **Explore the artifact before asking.** Any question answerable from
  the supplied data or codebase is answered there, never put to the
  human. (In run 6, half the human-authored PRD's content — columns,
  value domains, the messy-number formats, most of a description
  grammar — was derivable from the fixture CSV alone.)
- **Recommend an answer with every question.** The human mostly accepts
  or corrects defaults; their scarce attention goes to the questions
  models are worst at — what is actually required.
- **The translation rule.** When the human answers a business question
  with a mechanism ("I want a flag that..."), translate back to the
  outcome and confirm ("what would that flag let you do?"). Record the
  outcome as the requirement; record the mechanism as a constraint only
  when it is a user-world fact.
- **Three-bucket routing.** Every branch of the decision tree lands in
  exactly one: (a) intent — ask the human; (b) fact of the artifact —
  explore, then ratify; (c) solution design — record as OPEN, never
  resolve. The open questions are deliverables, not failures: they
  become the round-1 focus directives (Section 2.1), so the field
  diversifies along the axes the interview certified as genuinely open.

Artifacts (all committed, all consulted before any later escalation):

```text
GOAL.md               business objectives, user outcomes, constraints,
                      done criteria at outcome level (the termination
                      contract, Section 2.4)
decisions-ledger.md   every question, recommendation, and answer --
                      shared understanding as a diffable file
open-questions.md     the unresolved design branches -> round-1 foci
```

Mechanical done checks and acceptance criteria are NOT extracted from
the human in Phase 0 — outcome-level objectives are rarely mechanically
checkable. They are proposed by the design round (Section 2.3, design
tasks) and RATIFIED by the human: a second, short interview touchpoint,
the modern form of requirements sign-off.

### 2.6 Requirements Artifacts: Output Grammars and Decision Tables

The loop's two best-documented defect classes are, in structural terms,
cardinality errors: a report section dropped when its item count was
zero (wine-stock candidate B — `section (1) { item (0,N) }` implemented
as `section (0,1)`), and five distinct display stages collapsed to two
(word-garden-5 — `stage (5)` violated). Both passed every mechanical
gate and cost reviewer tokens, because prose requirements have no
grammar a gate can check. The fix is sixty years old: Warnier/Orr-style
output decomposition — define the structure of what the business needs,
and derive the checks from the structure.

- **Output grammar.** A plain indented outline (no special notation
  needed) of the deliverable's structure with cardinalities:
  ```text
  report (1)
    header (1)
    executive summary (1)
    grouping section (0,1: gated by the grouping option)
    detail table (1) { item row (1,N) }
    warnings (1) { warning (0,N); empty renders "none" }
  ```
  Drafted by the orchestrator FROM the Phase-0 conversation and the
  artifact, ratified by the human — a one-page picture a business
  person can confirm, which is the original point of the notation.
- **Deliberately partial.** Required nodes carry cardinalities (the
  business owns what must appear and what must stay distinguishable);
  nodes marked OPEN are the design round's to settle. A complete
  grammar would re-pin the decision space the way run-6's PRD did;
  the partial grammar is the altitude rule applied to structure.
- **Grammars compile into gates.** A structure validator generated from
  the ratified grammar (sections present, order, repeating groups
  well-formed, empty-state markers where cardinality demands presence)
  moves the structure/cardinality defect class from reviewer territory
  into gate-2 — the strongest form of "distill into the gate" (Section
  2, step 5).
- **The input side too.** The supplied artifact gets the same
  treatment, induced rather than asked: file/record/field structure
  with cardinalities and alternations, ratified in Phase 0.
- **Decision tables for rule sets.** Validation/warning rules become a
  condition → action matrix the human ratifies; tests generate
  row-by-row.
- **Limits.** Grammars fit things that ARE hierarchies — documents,
  files, records, reports. Interaction flow, state, and cross-cutting
  qualities stay in the prose objectives and the decisions ledger.
  W/O the artifacts, not the world. And only the requirements half of
  the old methods is taken: deriving PROGRAM structure from the data
  structure (the DSSD/JSP move) is precisely the decision space the
  field exists to explore.

## 3. Roles and Models

All roles run as Claude Code SUBAGENTS of the orchestrating host session —
delegate dispatch (Section 4.1b), billed to the subscription. Headless
`claude -p` subprocesses are no longer used for Anthropic-model roles:
since June 2026, subscription `claude -p` draws from a separate, CAPPED
Agent SDK credit (Section 8, billing row), which is the wrong economics
for exactly the high-volume parallel fleets the loop dispatches. The
subprocess adapter (Section 4.1) is retained for the future third-party
fleet milestone — GLM, MiniMax, Qwen, local models — where a `claude -p`
style CLI invocation is the appropriate harness.

|Role                  |Model                           |Count|Responsibility                                                                                       |
|----------------------|--------------------------------|-----|-----------------------------------------------------------------------------------------------------|
|Orchestrator (PM)     |Fable 5 (`claude-fable-5`)      |1    |Task decomposition, dispatch, worktree lifecycle, divergence measurement, CR handling, loop control  |
|Reviewer (Team Leader)|Opus 4.8 (`claude-opus-4-8`)    |1    |Gate interpretation, anonymized review, verdict, synthesis authorship, sole writer of `.code-tips.md`|
|Worker                |Haiku 4.5 (`claude-haiku-4-5`)  |2    |Blind implementation attempts                                                                        |
|Worker                |Sonnet 4.6 (`claude-sonnet-4-6`)|2    |Blind implementation attempts                                                                        |
|Worker                |Opus 4.8 (`claude-opus-4-8`)    |1    |Blind implementation attempts (strongest independent candidate)                                      |

Worker diversity note: within one model family, diversity comes from capability tiers rather than architecture. The 2x Haiku / 2x Sonnet / 1x Opus mix is also an experiment in itself: per-model win rates (Section 7) will show whether cheap workers plus a strong reviewer match expensive workers, which is the economic question the loop exists to answer. *Early returns (Section 11): after one distillation cycle, a Haiku worker won the tournament outright.*

## 4. Mechanism

### 4.1 Subprocess dispatch (`claude -p`): the third-party adapter

> **Not for Anthropic models.** Since June 2026, subscription `claude -p`
> draws from a separate, capped Agent SDK credit; Anthropic-model fleets
> dispatch as delegate subagents (4.1b), which is also the CLI's built-in
> default when no `farnsworth.json` exists. This section is the adapter
> kept open for the future third-party milestone — GLM, MiniMax, Qwen,
> Codex, local models — anything driven by a headless CLI command. The
> command-form lessons below were learned on `claude -p` and generalize
> to any worker CLI: canary the command form before a tournament spends.

A subprocess worker is a headless CLI process in its own worktree
(historical `claude -p` example; a third-party CLI slots into the same
`command` template):

```bash
git worktree add ../task-042-w1 -b task-042-w1
cd ../task-042-w1
claude -p "$(cat .code-tips.md)

TASK: $(cat task-brief.md)" \
  --bare \
  --model claude-haiku-4-5 \
  --permission-mode acceptEdits \
  --output-format json
```

`--bare` keeps workers from inheriting orchestrator config (hooks, skills, CLAUDE.md) — but note it also disables OAuth/keychain auth (Section 8), so subscription hosts used `--setting-sources ""` plus scoped `--allowedTools` instead. The worktree contains the blast radius of `acceptEdits`. Workers commit to their branch; the diff against main is the deliverable. Subprocess mode is also the only mode with a per-worker dollar stream (`total_cost_usd` parsed from `--output-format json`).

### 4.1b Delegate dispatch (the default; subscription-billed subagents)

For Anthropic-model workers the loop uses **delegate dispatch**: the
Claude Code session that orchestrates the loop spawns one standard
subagent per worker, which draws on the subscription. A worker entry
carries `model` instead of `command` (`farnsworth.json` in this repo is
the live example, and the CLI's built-in default fleet is delegate);
the two forms are mutually exclusive per entry, and a fleet must be
uniformly one mode. Subprocess dispatch (4.1) remains the adapter for
anything that is not an Anthropic model.

A Python CLI cannot spawn host-session subagents, so delegate mode makes
the loop PHASED around the two points where agents work, with every
mechanical phase staying in the tool:

```bash
farnsworth run tasks/task-042.md   # worktrees + briefing files + ledger; exit 3
# host session spawns one subagent per briefing (model per ledger, pinned
# to its worktree, blind) — subscription billing
farnsworth gate task-042           # commit check, gate, anonymize, review briefing; exit 3
# host session spawns the reviewer subagent with review-briefing.md
farnsworth finalize task-042       # validate verdict.json; run.json + summary.md; exit 0
```

The phase boundary stays the artifact, never the agent (Section 4.3):
`gate` trusts only commits in worktrees, `finalize` trusts only a
validating verdict.json — so hung, duplicated, or vanished subagents are
absorbed by re-spawning and re-running the phase. The reviewer protocol
(blind sketch, empirical verification, review.md, verdict, distillation)
is written by the CLI into `review-briefing.md`, closing the gap where it
previously had to travel inside the reviewer command template. Exit code 3
("awaiting delegation") joins the 0/1/2 trichotomy. Known trade-off:
delegate mode has no per-worker `total_cost_usd` stream, so cost rows in
the summary come only from subprocess runs; the orchestrator notes
delegate-round costs in the process log instead.

### 4.1c The packaged Claude workflow: agents and skills

Delegate dispatch left one gap: the orchestration protocol itself — who
spawns which subagent, with what prompt, under which blindness and
liveness rules — traveled as prose in this PRD and improvised
orchestrator sessions. A protocol traveling inside an orchestrator
prompt is a protocol that drifts (the same argument that moved the
review protocol into the CLI-written `review-briefing.md`). The
workflow is therefore packaged as repo-versioned Claude Code assets:

```text
.claude/agents/farnsworth-coder.md     the worker role: worktree-pinned,
                                       commit-as-artifact, no delegation
                                       (no Agent tool), blind, protected
                                       files restated
.claude/agents/farnsworth-judge.md     the reviewer role: review-env-
                                       pinned, blind sketch first,
                                       empirical probes, select-or-author
                                       verdict, distillation contract
.claude/agents/farnsworth-attestor.md  the semantic done-half: verify
                                       criteria empirically, attest or
                                       refuse, never fix
.claude/skills/farnsworth-task/        one tournament round: preflight ->
                                       run -> parallel coder dispatch ->
                                       gate -> judge dispatch -> finalize
                                       -> report -> verdict handling
.claude/skills/farnsworth-loop/        the goal cycle: done probe ->
                                       smallest-slice task derivation ->
                                       /farnsworth-task -> journal ->
                                       attestation -> the four exits
```

Division of labor is unchanged: every mechanical phase stays in the CLI;
the skills script only the two points where agents do the work, plus
verdict handling. The agent definitions are defence in depth, not a
replacement for the CLI-written briefings — the coder's rules restate
the `WORKER_PREAMBLE` the briefing already carries, the judge's restate
the `REVIEWER_PREAMBLE`, and the gate still enforces the commit/hygiene
contract mechanically whatever any prompt said. Model routing maps the
ledger's model ids onto the host's subagent model override
(`claude-haiku-*` → haiku, `claude-sonnet-*` → sonnet, `claude-opus-*`
→ opus, `claude-fable-*` → fable). The coder deliberately has no Agent
tool (the wine-stock nested-delegation incident, Section 17, enforced
structurally this time), and the skill keeps the orchestrator out of
the de-anonymization path: it knows the ledger mapping, so it never
inspects candidate diffs pre-verdict and never relays
worker/model/focus identity to the judge.

### 4.1c-ii The three-layer architecture (v2.2): workflow conductor over the trust layer

With Claude Code dynamic workflows GA (June 2026), the skills stop
being the primary conductor. The decided architecture — ratified
2026-06-12 after the word-garden-6 learning run and an explicit
should-we-rewrite-in-JS review — is three layers with FORCED
boundaries:

```text
.claude/workflows/farnsworth-task.js  CONDUCTOR  (JS; the runtime's
                                      language — phases, fan-out,
                                      /workflows telemetry, pause/stop)
.claude/agents/farnsworth-*.md        JUDGMENT   (prompts; coders,
                                      judge, verifier, attestor)
farnsworth/ (this Python CLI)         TRUST      (deterministic,
                                      token-free, tested: worktrees,
                                      gate, anonymization, artifacts)
```

Why the language boundary is correct and NOT an accident of history:
the workflow runtime is sandboxed — no filesystem, no shell; its only
interface to the world is `agent()`. A TypeScript rewrite of the trust
layer would be invoked exactly as the Python one is (an agent runs a
shell command), so a rewrite moves zero seams while re-rolling the dice
on every bug class the Section 8 risk table has already caught and
fixed. Code does what code does best, agents supply judgment, and the
conductor is whatever Anthropic's runtime speaks.

Consequences, all shipped 2026-06-12:

- **Exit 3 is a PHASE BOUNDARY, not a request to a human.** The
  wording dates from when a host session improvised the agent phases;
  under a conductor it just means "mechanical phase complete, agent
  phase next". CLI docs and messages reframed accordingly.
- **`--json` conductor mode** on `run`, `gate`, `finalize`, and `done`:
  each phase emits its machine-readable record (dispatch ledger, gated
  ledger, run log, done outcome) on stdout — agents relay structured
  truth verbatim instead of paraphrasing terminal output. Gate progress
  still streams live on stderr. Exit codes identical in both modes.
- **A Verify phase** (the June 2026 audit/judge/verify pattern): after
  the verdict, a fresh agent — never the judge — attacks the verdict's
  load-bearing claims empirically in the review environment and returns
  confirmed/overstated/refuted; a refutation blocks finalize and sends
  the round back to the judge with the refutation in hand. The agent
  that does the work must not be the last one to grade it.
- **The skills remain as the fallback conductor** for hosts without the
  workflow runtime (remote/managed sessions, older CLIs), and as the
  human-readable statement of the protocol the script encodes.
- **Worker time-boxing:** round 1 is exploration; the preamble now
  instructs an honest, committed attempt over endless local debugging
  (the word-garden-6 w2 lesson), and conductor dispatch should cap
  worker turns.

### 4.2 The knowledge artifact: `.code-tips.md`

Format:

```markdown
# Code Tips (written by reviewer only; workers read-only)

## Invariants
- [2026-06-12, task-042] Field x is 128 chars. Never assume 64.

## Gotchas
- [2026-06-12, task-038] Library y's retry API swallows timeouts; wrap it.

## Style
- [2026-06-12, task-031] Errors bubble to handler.go; no inline recovery.

## Per-module notes
### auth/
- [2026-06-12, task-040] Token refresh is intentionally synchronous. Do not async it.
```

Rules:

- Every entry carries a date and the task/review that birthed it (provenance).
- Entries must be durable project truths, not incident reports. “Fixed typo in auth.py” is not a lesson.
- The file pays rent: every line is loaded into every future briefing. A periodic consolidation pass (Section 6) prunes and merges.
- Tips are guidance, never contract. A tip that contradicts the task spec or project PRD triggers an escalation, not a silent amendment.

### 4.3 Housekeeping: hung agents and leftover debris

Dispatch is fire-and-forget per worker, so the loop must assume some
dispatches hang, die silently, or get duplicated by infrastructure retries.
Three rules keep a run recoverable:

1. **Every command gets a deadline.** Workers and the reviewer accept an
   optional `timeout_seconds` in `farnsworth.json`. A worker that exceeds it
   is killed and recorded with `exit_code: -1` (the kill is noted in its
   `.stderr` artifact); whatever it committed before stalling still faces
   the gate like any other attempt. A reviewer timeout is an infrastructure
   error (exit 2): the verdict is the phase's artifact and cannot be partial.
1. **The artifact is the phase boundary, not the agent.** A phase is
   complete when its artifact exists and validates (commits in the worktree;
   a verdict.json that parses), never because an agent reported success — or
   went quiet. Duplicated dispatches are therefore harmless by construction:
   the second result either matches the artifact contract or is discarded.
1. **Debris is swept before re-dispatch.** `farnsworth clean <task-id>`
   removes the task's leftover worktrees and branches so the same task id
   can run again (the collision pre-checks otherwise refuse). Worktrees with
   uncommitted changes are skipped unless `--force`; candidate diffs are
   already archived under `.farnsworth/<task-id>/candidates/`, so nothing of
   record is lost. Exit 0 when fully clean, 1 when something was skipped.

In manual agent-dispatch mode (Section 8 auth row) the same rules apply by
protocol rather than by code: the orchestrator keeps a ledger of dispatched
agents with per-phase deadlines, checks liveness via transcript activity,
stops stalled agents through the host's task controls, verifies the phase
artifact, and re-dispatches only the phases whose artifacts are missing.

### 4.4 State and audit

All loop state is file-based and inspectable: task briefs, candidate diffs, gate results, review documents, verdicts, and the tips file all live in the repo (under `.farnsworth/` for per-task artifacts). No database. A human can reconstruct any decision from git history alone. The orchestrator additionally keeps a running process-findings journal in `.farnsworth/orchestrator-log.md`, written after each merge.

Every run additionally produces a short what-happened table — one row per worker (id, focus, exit, gate, candidate label, ADOPTED marker, dollar cost when recorded) plus the verdict and reasoning — written to `.farnsworth/<task-id>/summary.md`, printed at the end of `farnsworth run`, and reprintable any time with `farnsworth report <task-id>`. The table is the thirty-second read; `run.json` remains the contract of record.

Three more fields ride in `run.json` since v1.2: per-worker `cost_usd` (parsed from the worker's `--output-format json` stdout in subprocess mode; in delegate mode an orchestrator-recorded ledger field, since host-session subagents have no cost stream), the review's `cost_usd`, and a top-level `divergence` block — the round's content-based field-divergence score (mean pairwise token-Jaccard distance across candidate diffs). The divergence number is RECORDED, not yet acted on: four runs proved file footprints identical even under deliberate diversification, so the M4 trigger threshold must be calibrated from accumulated content-based scores before two-round mode can wire to it. `farnsworth metrics` aggregates all of this across every recorded run.

Whenever a verdict merges code, the summary also carries a reviewer-authored **progression note** (`review.progression` in `run.json`): how the merged code advances the previously adopted baseline — what it built on, what is new, what got better relative to the prior merged state, and which distilled lessons it visibly absorbed. The verdict reasoning explains why the winner beat the *field*; the progression note explains how the *project* moved. Without it, a reader of task-N's summary learns who won round N but not what round N added to rounds 1..N-1 — the exact question an outside user asks first. The reviewer writes it post-verdict (it has the cross-candidate and cross-task view); the orchestrator records it in `run.json` so `farnsworth report` reproduces it from the log alone. Under a re-shot task (Section 2.3) the baseline is the previous *attempt*, and the progression note becomes the loop's learning measurement itself: how attempt 2 improved on attempt 1.

## 5. MVP Scope

In scope:

- Single-task loop, CLI-invoked: `farnsworth run task-brief.md`
- Delegate dispatch for Anthropic-model fleets (Section 4.1b) — the default and the only sanctioned mode for Anthropic models since the June 2026 `claude -p` subscription caps: `run` -> `gate` -> `finalize` phases around host-session subagents, subscription-billed; the CLI's built-in default fleet is delegate
- The packaged Claude workflow (Section 4.1c): `.claude/agents/` role definitions (coder, judge, attestor) and `.claude/skills/` orchestration (`/farnsworth-task`, `/farnsworth-loop`), so the delegate-dispatch protocol ships as versioned code instead of orchestrator-prompt prose
- Parallel blind dispatch to the 5-worker fleet via worktrees
- Mechanical gate (configurable build/test/lint commands)
- Anonymized review with three-outcome verdict
- `.code-tips.md` lifecycle (reviewer-written, worker-injected, provenance-stamped)
- Divergence-triggered two-round mode
- Per-worker focus directives with unattributed disclosure to the reviewer (Section 2.1)
- JSON run log per task with per-model costs (from `--output-format json`)
- Run summary table: `.farnsworth/<task-id>/summary.md` + `farnsworth report <task-id>`, including the reviewer's progression note on merging verdicts (Section 4.4)
- Housekeeping: per-command `timeout_seconds` and `farnsworth clean <task-id>` (Section 4.3)
- Loop termination contract: `goal` config + `farnsworth done` (Section 2.4), with recorded probe results and a CLI-written attestation briefing
- `farnsworth preflight`: mechanical canary of the fleet config — parse, clean tree, green gate at base, and per-worker edit+commit capability in a scratch worktree (the two observed config-fatality classes) — before a tournament spends real money
- `farnsworth adopt <task-id> [--clean]`: merge the verdict's winner, install the reviewer's `code-tips.next.md`, surface `seed-tips.next.md` for seed-pile routing, count adopted tasks toward the Section 6 consolidation cadence
- `farnsworth metrics [root ...]`: the cross-run health table (Section 7) aggregated from every `run.json` on disk
- Mechanical hygiene gate: candidates that modify `.code-tips.md`, the fleet config, or the task brief fail the gate with an autopsy, in both dispatch modes
- Per-worker `cost_usd` capture (subprocess mode) and recorded content-based `divergence` per round (Section 4.4)

Explicit non-goals (MVP):

- No UI before the markdown loop works end to end. The TUI memory-map aesthetic is a later milestone, not MVP.
- No scheduler or daemon. The CLI runs one task per invocation; CYCLING is the orchestrator's job (Section 2.4), with `farnsworth done` as its termination probe. A `farnsworth loop` command that automates the cycle is post-MVP.
- No cross-provider workers (GLM, MiniMax, Qwen, Codex, local models). The dispatch interface must not preclude them — the subprocess `command` adapter (Section 4.1) is their landing spot, with the same blind/anonymized protocol — but MVP is Anthropic-only by design.
- No autonomous PRD/contract mutation. Escalations surface to a human.
- No fine-tuning, no embeddings, no vector store. The context layer is the only memory.

## 6. Maintenance Loops

- **Consolidation pass:** every N merged tasks (default 10), the reviewer audits `.code-tips.md` against the current codebase: merge duplicates, retire stale entries (with a tombstone note in the commit), and compress. This is doc-rot management as a first-class scheduled job. *(The cadence is now counted: `farnsworth adopt` tallies adopted tasks from the run logs and announces when the pass is due — nothing counted N before, which is why no consolidation was ever triggered.)*
- **Escalation queue:** CRs filed by the reviewer accumulate as issues for human ratification. The loop may continue on unaffected tasks while a CR is pending.

## 7. Metrics (the loop’s own health)

1. **First-pass gate success rate over time.** The primary KPI. If the loop is learning, this climbs as tips accumulate. Plateau or decline means the tips file has rotted or bloated.
1. **Per-model win rate** (adopted candidates by model) and per-model gate pass rate. Informs future routing and answers the cheap-workers question.
1. **Verdict distribution** (adopt / synthesize / escalate). A rising synthesize rate means workers are underpowered or briefs are poor; a rising escalate rate means the spec process is broken.
1. **Cost per merged task** (sum of per-invocation costs from JSON output), tracked against verdict type.
1. **Round 2 trigger rate.** *(v1 metric, retired in v2: round 2 is the spine of every task. Divergence is still recorded and now sizes round 2 and review depth — Section 2.2.)*
1. **Within-task learning delta (v2).** The defect ledger of round 1 vs round 2 inside one task, and the champion's fate in verdict-2: an informed rebuild beating the blind champion is the thesis confirmed at the tightest possible scope; the champion surviving is a recorded negative result. This replaces the cross-project defect-floor comparison as the loop's primary learning signal once v2 runs accumulate.

All metrics derive from the per-task JSON logs; a single script renders the dashboard. The chart that matters: gate success rate (y) against merged task count (x). Up and to the right means Farnsworth is learning.

*Measurement note from dogfooding: gate rate saturated immediately (5/5 both rounds), so it is a weak early signal on small tasks. The discriminating early metrics turned out to be field quality (spec/hygiene violations per round: 2 then 0) and reviewer-found defects in gate-passing candidates (2 per round so far) — the gate cannot see contract faithfulness. Track these alongside the headline chart.*

*Second measurement note from the Word Garden example: track per-ATTEMPT cost alongside per-model win rate — in the 5-way round, Opus won with the fewest tokens of the field (~31k, 12 tool calls) while a Haiku burned ~76k/64 calls on a weaker candidate; "cheap model" and "cheap attempt" are different quantities. And under triage the reviewer's SHARE of spend rises (50% -> 68% observed) even as absolute cost falls, because review depth is fixed while the field shrinks.*

*Third measurement note, from the Word Garden 2 replication (Section 13): defects-per-round in gate-passing candidates is the loop's primary EARLY learning signal — it improved under tips in both runs (1→0, 2→1) while the winning model's identity did not reproduce (metric 2 is long-horizon, noisy at one round per cell). Reviewer share also tracks worker economy, not just field size: a triaged round with heavy worker attempts kept the reviewer at ~55%, not the 68% seen before.*

*Fourth measurement note, from Word Garden 3 (Section 14): count defects per round in two ledgers — BEHAVIORAL bugs and CONTRACT-level deviations — and attribute each to whether a tips entry covered its class. Attribution is the seed experiment's real readout: in run 3, every defect class covered by a seed entry was absent from the field, and the one behavioral bug that shipped was exactly the lesson the domain-general curation rule had excluded from the seed. Also: with foci in play, record the winning FOCUS alongside the winning model; two rounds in, focus-task alignment predicts where candidates invest, not who wins.*

*Fifth measurement note, from Word Garden 5 (Section 16): under the goal contract, add two ledger lines — ITERATIONS-TO-GOAL (the emergent cycle count; the loop's headline efficiency number once goals are the unit of work) and the ATTESTATION dispatch's cost (a fixed per-goal overhead, ~68k tokens in run 5, distinct from per-task review spend). And keep the two defect ledgers honest about novelty: run 5's field had ZERO defects in classes covered by tips, while all four defects found were in classes no tip yet covered (ASCII stage distinctness, dead constants) — the loop's residual defect rate is concentrated precisely where memory hasn't been yet, which is the learning thesis read from the other side.*

*Sixth measurement note, from the fully CLI-dispatched run, Word Garden 4 (Section 15): with dollar-true costs (`total_cost_usd` from the JSON output), the reviewer crossed 100% of worker spend in a 5-way round ($3.61 vs $3.03) — manual-mode token shares understated review's weight. Empirical per-candidate verification is the dominant line item once dispatch is cheap and fast; review depth should scale with field DISAGREEMENT (convergent fields get spot-checks), queued for M4 alongside divergence measurement.*

## 8. Risks and Mitigations

|Risk                                    |Mitigation                                                                                                                                                               |
|----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|Reviewer anchoring on candidates        |Blind sketch before reading candidates (Section 2, verdict)                                                                                                              |
|Reviewer self-preference / position bias|Anonymized labels, randomized order, no model attribution                                                                                                                |
|Tips bloat (context tax)                |Rent rule, provenance, scheduled consolidation pass                                                                                                                      |
|Tips rot (superstitions)                |Provenance + consolidation audit against live codebase                                                                                                                   |
|Workers editing their own briefing      |`.code-tips.md` writable by reviewer role only; enforced in dispatch wrapper                                                                                             |
|Frankenstein merges                     |Verdict is select-or-author, never splice; cross-candidate ideas only via instructed revision of one coherent base                                                       |
|Runaway cost on routine tasks           |Tournament is for ambiguous/consequential/previously-failed tasks; orchestrator may dispatch a single Sonnet worker for routine ones (triage rule in orchestrator prompt)|
|Reviewer cost dominates                 |*(observed in dogfooding: reviewer ~51–54% of worker spend)* Triage rule plus consolidation keep review depth where it pays; routine tasks skip the tournament            |
|Weak worker tests mask defects          |*(observed: a negative-only assertion hid a dropped-autopsy bug)* Distilled testing rules in tips (assert the positive); reviewer scores test rigor explicitly            |
|Stale dispatch context                  |*(observed: worker worktrees forked from a stale base)* Dispatch wrapper pins and verifies the base commit; workers sync to it before starting                            |
|Billing surprises                       |From 15 June 2026, `claude -p` on subscription plans draws from a separate, CAPPED monthly Agent SDK credit — fatal economics for the loop's parallel fleets. Resolved structurally (v2.1): Anthropic-model fleets use delegate dispatch ONLY (Section 4.1b), which bills host-session subagents to the subscription, and the CLI's built-in default fleet is delegate; `claude -p` subprocess dispatch is reserved for third-party models (GLM, MiniMax, Qwen, local) and API-key hosts (Section 4.1)                       |
|Nested `claude -p` cannot authenticate in managed sandboxes|*(observed: Word Garden example; UPDATED Word Garden 5: auth worked briefly — a real worker built and gate-passed via the CLI — then went intermittent, which is worse than absent: never trust a passing auth probe for a whole run)* Credentials are host-managed FDs that child processes don't inherit. Dispatch is conceptually an adapter: the same blind/anonymized protocol runs via agent-tool sub-agents (manual mode) — used for most recorded runs, with Word Garden 5 driving the CLI's own briefing/review-env/report/done code from manual mode. Word Garden 4 (Section 15) ran fully CLI-dispatched on subscription OAuth before run 5 hit the intermittency — treat auth as per-run weather: canary every phase, fall back to delegate or manual dispatch when it turns. *Since v2.1 this whole risk class is confined to the third-party subprocess adapter (Section 4.1): Anthropic fleets never spawn nested `claude -p`*                  |
|Host git config forces commit signing   |*(observed: Word Garden example)* Global `commit.gpgsign=true` with a session-scoped signer fails every scratch/worktree commit; seed repos with repo-local `commit.gpgsign=false` (worktrees inherit it). The test suite is hermetic against this since task-002                              |
|Focus directive read as a contract amendment|Dispatch wrapper appends an explicit precedence sentence (brief wins); reviewer scores against acceptance criteria only; per-candidate focus sealed until post-verdict (Section 2.1)                                                                  |
|Single-round wins read as a trend       |*(observed: Word Garden 2)* The cheaper-model-wins streak broke on replication while the defect-floor effect held; treat per-model win rate as long-horizon, score learning by defects-per-round (Sections 7, 13)                                            |
|Hung, orphaned, or duplicated dispatches|*(observed: Word Garden example — a duplicate task-001 reviewer stalled for 35+ min after an infra retry; Word Garden 3 — duplicates in every background phase, all absorbed)* Housekeeping rules in Section 4.3: per-command timeouts, artifact-is-the-phase-boundary idempotency, `farnsworth clean` before re-dispatch; ledger + liveness checks in manual mode|
|Reviewer environment leaks worker identity |*(observed: Word Garden 3; IMPLEMENTED in the CLI 2026-06-12, first live use Word Garden 5)* A naive clone for the reviewer carries worker-named branches (`task-001-w1`…), and `farnsworth.json` maps ids to models/foci. The CLI now constructs the review environment: exported base tree minus `farnsworth.json` and prior `.farnsworth/` artifacts, re-initialized as a fresh single-commit repo, plus labeled diffs + gate notes ONLY; reviewer artifacts are copied back post-verdict and `farnsworth clean` sweeps the env                                  |
|Workers "improve" a required signature     |*(observed: Word Garden 3 — an extra `new_game_fn` param forfeited an otherwise-winning candidate)* Briefs and tips state required signatures are exact and CLOSED contracts; proposed improvements go to escalation or a follow-up task, never silently into the diff                          |
|Pre-planned task pipeline masquerades as the loop|*(observed: a run-4 orchestrator pre-authored "task-001 engine, task-002 UI" before the first dispatch and treated finishing the list as finishing the job)* Section 2.4: one next task per cycle, derived from the goal gap post-merge; `farnsworth done` decides continuation, never a checklist|
|`--bare` workers cannot authenticate on subscription hosts|*(observed: Word Garden 4 pre-flight — `--bare` never reads OAuth/keychain, so every dispatch dies "Not logged in")* Use `--setting-sources ""` for isolation instead; reserve `--bare` for API-key/apiKeyHelper hosts. Canary-test the config before any tournament|
|Headless permission mode starves workers of tools|*(observed: Word Garden 4 pre-flight — headless `acceptEdits` denies ALL Bash; workers could edit but not test or commit, so every candidate would gate empty)* Scoped `--allowedTools "Bash(python3:*)" "Bash(git:*)"` in the worker command; a `farnsworth preflight` canary command is queued|
|Gate passes a worker that never committed|*(observed live: Word Garden 4 task-002 — a worker left all its work untracked; the gate ran in the worktree and passed while the candidate diff `base..HEAD` was empty, so the briefing vouched for a 0-line candidate)* Enforced in code since 2026-06-12: no commits on the branch = gate failure with autopsy, uncommitted work archived to `<id>-uncommitted.diff`, empty diffs never take a label. The reviewer's empirical probe is the backstop and caught it live|
|Typo'd `--config` silently dispatches the default fleet|*(found in review 2026-06-12: `Config.load` fell back to the built-in default config — whose old form carried the `--bare` flag proven 100% fatal — whenever the named path was missing, contradicting its own docstring)* Fixed in code: an explicitly named config that does not exist is an error in every subcommand; relative `--config` paths anchor at the repo root uniformly; the built-in default worker command now uses the word-garden-4-proven `--setting-sources ""` + scoped `--allowedTools` form. `farnsworth preflight` is the standing defence|
|Workers briefed without rules of engagement (subprocess mode)|*(found in review 2026-06-12: the worker preamble — commit contract, tips-file hygiene, blindness — existed only in delegate dispatch; word-garden-4's non-committing worker was a subprocess run)* The preamble is shared by both dispatch modes, and the hygiene rules are also enforced mechanically: a candidate whose commits touch `.code-tips.md`, the fleet config, or the task brief fails the gate with an autopsy|
|Round-2 field converges into copies of round-1 thinking|By design under rebuild semantics — round 2 is supposed to converge on what round 1 taught, and design-level lessons are legitimate distillation (Section 2, step 5). The control is the champion standing relabeled in the verdict-2 field: if convergence is net-negative, the champion wins and the negative result is recorded. Tips must still never instruct replication of a specific candidate's code — the bar is "beat the champion", not "copy it"|
|Idea-mining gate-failers blows the review budget|Two depth tiers in the round-1 review protocol (Section 2, step 3): full empirical probe for passers only; failers get a diff-read for the approach and the trap, never debugging. Commit/hygiene violations skip review entirely — a non-submission is not an interesting failure|
|Round-3+ becomes persistence-as-strategy (Ralph wearing our clothes)|Rounds past 2 exist only as failure handling (verdict-2 adopted nothing) and each must show measurable progress — defect ledger shrinking, more gate-2 checks passing — or the task STALLS into escalation (Sections 2.2, 2.4)|
|Phase-0 interview drifts into technical specification|The altitude rule and translation rule (Section 2.5): business objectives and user outcomes only; mechanisms offered by the human are translated back to outcomes and recorded as constraints only when they are user-world facts. *(Observed in reverse: run-6's human-supplied PRD pinned exit codes, flags, and layout — all dev-team decisions — and the field converged to five stylistic variants of one design)*|
|A complete output grammar re-pins the decision space|Grammars are deliberately PARTIAL (Section 2.6): required nodes carry cardinalities the business owns; OPEN nodes are the design round's to settle and double as round-1 foci|
|Worker delegates its attempt to a nested agent|*(observed: wine-stock-report-generator-1 task-001 — a worker spawned a nested implementation agent and ended its turn "complete" with zero commits on its branch; the orphaned nested agent later finished as a duplicate in the same worktree)* The artifact rule catches it (commits are the deliverable; completion claims are not) and re-dispatch recovers the round; WORKER_PREAMBLE now forbids spawning/delegating outright, in both dispatch modes|
|`git reset --hard` cannot clean a greenfield candidate in review|*(observed: wine-stock-report-generator-1 — the first reviewer dispatch hung mid-examination; forensics showed an applied candidate sitting UNTRACKED on a clean base, because files a diff CREATES are untracked after `git apply` and reset does not touch them — candidates stack, and naive `git clean -fd` would delete the reviewer's own notes)* The review briefing now prescribes `git reset --hard && git clean -fd -e .farnsworth` (the served diffs are committed in the review base and survive regardless)|
|Re-gating serves stale labels to the reviewer|*(found in review 2026-06-12: `farnsworth gate` re-runs — the documented recovery for hung subagents — reshuffled labels but left previous labels' diffs in `candidates/` and never refreshed an existing review environment)* Fixed in code: re-gate sweeps the candidates dir before relabeling and refreshes the served diffs in an already-constructed review env — the word-garden-5 briefed-path bug class, closed from the other side|

## 9. Milestones

1. **M1, Skeleton** — ✅ **done (task-001, adopted from a 5-way tournament):** dispatch + worktrees + gate + JSON run log, single worker. Proves plumbing.
1. **M2, Tournament** — ✅ **done (task-002, adopted from a 5-way tournament):** full multi-worker blind dispatch, anonymized review briefing, configurable reviewer, three-outcome verdict, manual merge.
1. **M3, Memory:** `.code-tips.md` lifecycle + injection + consolidation pass automated in the CLI, **plus the cross-project tips seed** — validated live in Word Garden 3 (Section 14): a 9-entry domain-general seed suppressed every defect class it covered, in a fresh project, in both rounds. M3 also adopts the run-3 distillation refinement: when a project lesson instantiates a general class, the reviewer writes the general form for the seed pile and the specific form for project tips — and since 2026-06-12 the CLI's review briefing carries that instruction itself (general forms go to `seed-tips.next.md`, which `farnsworth adopt` surfaces for routing into the seed pile; the tips install is mechanized by `adopt` too). *(Three pieces shipped 2026-06-12 and live-validated in Word Garden 5: the CLI review briefing now instructs the reviewer to produce `code-tips.next.md` — the complete next tips file, installed by the orchestrator post-merge; seed v2 carried the first GENERALIZED entry, which suppressed its defect class across the whole field; and the seed pile is now a first-class artifact at [`seed-tips.md`](seed-tips.md) — copy it into a new project's `.code-tips.md` before round 1, and route every "general form" a reviewer distills back into it. Word Garden 4 added the boundary from the other side: a seed transfers MECHANICAL rule classes — its argparse entry suppressed run 2's defect — but not SEMANTIC state contracts, whose defect class recurred until the project's own round 1 distilled the specific tip; see Section 15.)*
1. **M4, Adaptive:** divergence measurement + two-round mode + triage rule. *(Focus-diversified dispatch — the divergence FORCING half of this milestone — shipped 2026-06-12 and had its first live tournament in Word Garden 3: foci measurably spread the field with zero contract-amendment misreads. The measurement half has a confirmed requirement from four runs — including Word Garden 5 at whole-program grain: file footprints are identical even under deliberate diversification — the metric must read content, not file lists, or round 2 will never trigger on well-briefed tasks. The content-based metric shipped 2026-06-12: mean pairwise token-Jaccard distance over candidate diffs, recorded as `divergence` in every run.json — recording-only until enough rounds calibrate a trigger threshold. Word Garden 4's live tournament added: foci modulate style, not the correctness floor — the test-rigor-focused Haiku still shipped the flag-only-assertion defect, so tier dominates focus. Disagreement-scaled review depth is queued here too: run 4's reviewer cost crossed 100% of worker spend in dollar terms.)*
1. **M5, Instrumentation:** metrics dashboard from JSON logs; publish gate-success-over-time chart in the README. *(First piece shipped 2026-06-12: per-run summary table in `summary.md` / `farnsworth report`, generated retroactively for all six prior recorded runs. Word Garden 4 added the first dollar-true cost rows from live `--output-format json` runs — and the CLI now parses `total_cost_usd` into run.json itself. Second piece shipped 2026-06-12: `farnsworth metrics` aggregates every run.json under the given roots into the cross-run table — verdict distribution, gate-rate-over-tasks chart data, per-model wins, divergence, dollar costs. Rendering the chart image remains open.)*
1. **M6, Theater:** TUI memory-map visualization of the fleet (post-MVP, separate doc).
1. **M8, Workflow Conductor (v2.2):** the dynamic-workflow runtime as
   the loop's primary orchestrator (Section 4.1c-ii). Shipped
   2026-06-12: `.claude/workflows/farnsworth-task.js` conducting the
   FULL two-round v2 spine — R1 explore, R1 gate/judge (verdict-1
   crowns the champion), distill (lessons installed between rounds,
   never code), R2 clean-slate rebuild, champion relabeled by the
   conductor into the R2 review field (the M7-pending manual protocol
   from Section 2.2, scripted), blind verdict-2 with the
   champion-survival negative result recorded, adversarial Verify, and
   finalize/adopt routed through whichever round's task owns the
   winner. Plus `--json` conductor mode across the phase commands,
   gate hardening from the word-garden-6 live run (per-command
   deadlines, stdin closed, commit-check-first, parallel worktree
   gating with streamed progress), and DYNAMIC FLEET SELECTION: the
   workflow's Fleet phase resolves the field at launch (`args.fleet`
   writes a run-scoped config; `args.config` names one; the repo
   default is surfaced, never silent) and the skill's Phase 0 confirms
   the fleet with the human before any dispatch — the recorded
   2H/2S/1O mix is a default and an experiment, not a fixture. Open:
   workflow conduction of subprocess/local fleets (today the Fleet
   phase routes them to the CLI's end-to-end `run`), heterogeneous
   delegate+command fields in a single round (the config enforces one
   dispatch mode per fleet), M7's CLI mechanization of the
   verdict-1 schema and champion relabeling (replacing the scripted
   manual steps), gate-as-evidence for no-candidate explore rounds,
   per-agent token telemetry from `/workflows` into `run.json`,
   `maxTurns` caps on coder dispatch, and the first live
   workflow-conducted run.
1. **M7, Two-Phase Loop (v2 CLI):** mechanize Sections 2/2.2/2.5/2.6 — gate-as-evidence (results travel with every candidate; only commit/hygiene checks disqualify), the verdict-1 schema (champion + defect ledger + lessons + gate extensions + `round_2: proceed|adopt-final|escalate`), round-2 phases (clean-slate re-dispatch with installed lessons; champion relabeled into the review field; negative-result recording), round-N progress accounting against the STALLED rule, Phase-0 artifact support (`GOAL.md`/`decisions-ledger.md`/`open-questions.md`, open questions surfaced as foci), and grammar-compiled structure gates. Until M7 lands the CLI implements the v1 single-round flow; the v2 protocol is dispatch-mode-agnostic and an orchestrator can run it today by treating each round as a CLI task and performing champion relabeling by hand. Per repo tradition, M7 should be built BY the loop.

## 10. Acceptance Criteria (faithfulness contract)

Later agents and reviewers score the implementation against this checklist:

- [x] Workers are blind: no candidate ever enters another worker’s context in the same round. *(tasks 001–002: isolated worktrees, no cross-contamination)*
- [x] Workers never write `.code-tips.md`. *(one task-001 worker committed the seed file byte-identical — flagged in review, rule distilled, zero recurrence in task-002)*
- [x] Review is anonymized and order-randomized. *(labels shuffled; attribution sealed outside the repo until post-verdict)*
- [x] Every verdict is exactly one of adopt / synthesize / escalate, recorded in the task log. *(2/2 recorded in run.json)*
- [x] Reviewer’s blind sketch exists before candidate review in every synthesize verdict. *(blind sketch produced in both reviews, though both verdicts were adopt)*
- [x] Every tips entry has date + provenance.
- [ ] Round 2 workers receive the original brief + updated tips + round-1 lessons, never round-1 diffs; the champion's code reaches only the review field. *(v2 spine; unexercised — the v1 divergence trigger never fired in ten tasks)*
- [ ] Gate-1 results reach the reviewer for every candidate; gate-1 never excludes a candidate from round-1 review (commit/hygiene non-submissions excepted). *(v2; unexercised)*
- [ ] The champion enters round-2 review relabeled and unattributed; the verdict-2 reviewer is blind to which candidate it is. *(v2; unexercised)*
- [ ] A champion surviving verdict-2 is recorded in run.json and metrics as a negative learning result. *(v2; unexercised)*
- [ ] Phase-0 projects carry GOAL.md, decisions-ledger.md, and open-questions.md; open questions become round-1 foci; attestation targets the business objectives and decisions ledger. *(v2; unexercised)*
- [ ] Mechanically-expressible round-1 lessons land as gate-2 extensions, not only as tips. *(v2; unexercised)*
- [x] All decisions reconstructible from git history alone (no hidden state).
- [x] A human can read `.code-tips.md` in under two minutes (consolidation is working). *(~35 lines after two distillations)*
- [ ] Gate-success-over-time chart exists and is generated from real run logs. *(M5; the chart DATA now comes from `farnsworth metrics` over the banked run logs — the rendered chart itself is still open)*
- [x] Every run yields a `summary.md` table a human can read in thirty seconds; `farnsworth report <task-id>` reprints it from `run.json` alone.
- [x] Every merging verdict's summary carries a progression note explaining how the adopted code advances the previously adopted baseline, not just why it beat the field. *(introduced 2026-06-12 after Word Garden 3; present for both of that run's tasks)*
- [x] Focus directives never reach the reviewer attributed to a candidate or worker id; each worker sees only its own focus.

## 11. Dogfooding Findings (tasks 001–002)

The loop built itself: M1 and M2 were each produced by a manually-orchestrated Farnsworth iteration (the orchestrator and reviewer were agents; the tool under construction became the thing it automates). Full process journal: `.farnsworth/orchestrator-log.md`. Per-task forensics: `.farnsworth/task-001/`, `.farnsworth/task-002/`.

| Metric | task-001 (empty tips) | task-002 (14 lessons injected) |
|---|---|---|
| First-pass gate rate | 5/5 | 5/5 |
| Spec/hygiene violations in field | 2 | 0 |
| Verdict | adopt | adopt |
| Winning model | **Opus 4.8** | **Haiku 4.5** |
| Worker tokens | ~244k | ~390k |
| Reviewer tokens | ~124k | ~212k |

What we learned, in order of importance:

1. **The thesis held on first contact.** With an empty tips file, the strongest model won. One distillation cycle later, the cheapest model won — on contract faithfulness, against two Sonnets and an Opus. The models never got smarter; the briefing did.
2. **The gate filters mechanics; the review filters meaning.** All ten candidates across both rounds passed the gate. The review then found, in gate-passing code: spec deviations, a silently-dropped-autopsy logic bug, and a run.json contract violation. Semantic review is not optional polish — it is the loop's actual quality filter.
3. **Tips raise the floor, fast.** Hygiene/spec violations went 2 → 0 in one cycle, including in the same model tier that committed them.
4. **Reviewer spend is the scaling pressure** (~half of worker spend per task). The triage rule (Section 8) and consolidation pass (Section 6) are economic necessities, not nice-to-haves.
5. **Weak tests are the blind spot.** A worker's bug survived its own suite because the test asserted only the negative. The distilled rule — assert the positive — is now in every future briefing.

## 12. First External Project: Word Garden (examples/word-garden-1)

The loop's first non-self subject: a small terminal word-guessing game,
built in two iterations on 2026-06-11 (full forensic record and process
report in [`examples/`](examples/README.md)). Run in manual agent-dispatch
mode (Section 8, auth risk row); protocol otherwise per this PRD.

| Metric | task-001 (no tips, 5 workers) | task-002 (21 tips, 3 workers triaged) |
|---|---|---|
| First-pass gate rate | 5/5 | 3/3 |
| Correctness bugs found in gate-passing field | 1 | 0 |
| Verdict | adopt | adopt |
| Winning model | **Opus 4.8** | **Sonnet 4.6** |
| Worker agent tokens | ~223k | ~122k |
| Reviewer agent tokens (share) | ~112k (50%) | ~83k (68%) |

What it added to the loop's evidence base:

1. **The thesis generalizes.** Third consecutive round across two projects
   where the win moved down the cost ladder exactly when distilled tips
   entered the briefing — and the field's defect rate fell to zero.
2. **Tips need contract language.** Round-1 lessons phrased as "MUST"
   were universally absorbed; the one phrased as "prefer..." was missed by
   all three round-2 workers. The reviewer now distills imperatively.
3. **Triage trade-off quantified.** Absolute cost down ~45%; reviewer share
   of spend up 50% -> 68%. Consolidation and review-depth scaling are the
   binding economic constraints, exactly as Section 8 predicted.
4. **Per-task gate extensions work.** Cheap orchestrator-added mechanical
   checks (piped-EOF exit, base-files-untouched) belong in the gate config
   as first-class per-task entries — queued for M4's triage work.

## 13. First Replication: Word Garden 2 (examples/word-garden-2)

The first controlled replication (2026-06-12): the same Word Garden spec,
byte-identical task-001 brief, same fleet mix and gate as Section 12's run,
re-seeded fresh with an EMPTY tips file. Full forensics:
[`examples/word-garden-2/`](examples/word-garden-2/); process report in its
`.farnsworth/orchestrator-log.md`.

| Metric | task-001 (no tips, 5 workers) | task-002 (21 tips, 3 workers triaged) |
|---|---|---|
| First-pass gate rate | 5/5 | 3/3 |
| Correctness bugs found in gate-passing field | 2 | 1 |
| Verdict | adopt | adopt |
| Winning model | **Opus 4.8** | **Opus 4.8** |
| Worker agent tokens | ~218k | ~193k |
| Reviewer agent tokens (share) | ~118k (54%) | ~106k (55%) |

What the replication confirmed, broke, and added:

1. **Confirmed:** gate-vs-review division (review again found real bugs in
   gate-passing candidates — a terminal-guess "flags right, message wrong"
   defect in two of five); tips lowering the field's defect rate (2 → 1);
   empty-tips rounds going to the strongest model; duplicated dispatches
   absorbed harmlessly by the artifact-boundary rule (Section 4.3).
2. **Broke:** the headline "win moves down the cost ladder with tips."
   Opus won BOTH rounds here, ending a three-round streak across two
   projects. Revision: the loop's reproducible learning signal is the
   defect FLOOR of the field, not the winner's identity. Per-model win
   rate (Section 7.2) is a long-horizon metric; defects-per-round in
   gate-passing candidates is the early one. The thesis stands — the
   project gets smarter — but its evidence is the floor, not the podium.
3. **Added — memory is project-scoped, mistakes are not.** Run 2's Haiku
   committed exactly the argparse defect run 1 had already distilled into
   the OTHER project's tips file. Proposed extension (queued for M3):
   a small curated cross-project tips seed — domain-general contracts
   (argparse exit codes, assert-the-positive, injected I/O) injected into
   round 1 of any new project, distinct from project-scoped tips.
4. **Added — tips must declare scope.** Run 1: advisory tips get ignored
   (write imperatively). Run 2: imperative tips get ignored OUTSIDE their
   stated scope (the MSG_*-reuse tip didn't say it bound tests too; 2 of 3
   workers string-matched literals in tests). Distillation rule is now:
   contract language AND explicit scope ("in source and tests").

## 14. The Extensions Run: Word Garden 3 (examples/word-garden-3)

The third Word Garden run (2026-06-12): same spec, byte-identical task
briefs, same fleet mix — but the first LIVE run of two queued extensions:
the **cross-project tips seed** (9 curated domain-general entries from
prior projects' distillations, injected before round 1) and
**focus-diversified dispatch** (Section 2.1). Two variables changed vs the
run-2 baseline; defect attribution is therefore done per defect CLASS
against seed coverage, and foci are judged by field divergence, not defect
count. Full forensics: [`examples/word-garden-3/`](examples/word-garden-3/).

| Metric | task-001 (9 seed tips, 5 workers) | task-002 (seed + 14 project tips, 3 triaged) |
|---|---|---|
| First-pass gate rate | 5/5 | 3/3 |
| Behavioral bugs in gate-passing field | 1 | 0 |
| Contract-level defects in field | 0 | 2 |
| Verdict | adopt | adopt |
| Winning model (focus) | **Sonnet 4.6** (defensive robustness) | **Opus 4.8** (readability) |
| Worker agent tokens | ~262k | ~226k |
| Reviewer agent tokens (share) | ~149k (57%) | ~125k (55%) |

What it settled, sharpened, and surfaced:

1. **Settled: cross-project seed tips work, attributably.** Every defect
   class covered by a seed entry was absent from the field — including
   the argparse `SystemExit` swallow that had shipped in BOTH prior
   projects' UI rounds (reviewer's audit: 0/9 seed entries violated).
   The run's single behavioral bug was word-garden-1's `is_lost`
   missing-win-guard defect — the one lesson that existed only as
   another project's PROJECT-scoped tip, excluded from the seed by the
   domain-general rule. Memory's scope boundary is visible in the defect
   data from both sides. Seed graduates into M3.
2. **Sharpened: distillation should generalize.** The `is_lost` lesson
   was always an instance of a general class ("a standalone predicate
   must not rely on a caller's check ordering"). New distillation rule:
   reviewers write the general form for the seed pile AND the specific
   form for project tips.
3. **Settled: foci diversify without corrupting.** Test counts spread
   36–145 across rounds; candidates invested along their lenses; zero
   contract-amendment misreads; anonymization held (foci disclosed as an
   unattributed set). Alignment isn't advantage: the
   accessibility-focused candidate produced the round's best
   accessibility work and still lost on a signature deviation.
4. **Surfaced: a reviewer-environment leak class.** Worker-named branches
   in a naively-cloned review repo de-anonymize the field; the review
   environment must be constructed from base tree + labeled diffs + gate
   notes only. (Risk table updated; belongs in the CLI's review dispatch.)
5. **Surfaced: closed-contract signatures.** A good-faith extra parameter
   on a required signature forfeited an otherwise-winning candidate;
   briefs now state required signatures are exact and closed.
6. **Third confirmations:** duplicate dispatches absorbed by the
   artifact-boundary rule (now including a duplicated reviewer, twice);
   footprint-based divergence measurement blind even under deliberate
   diversification; Haiku spending the field's most motion on a
   non-winning candidate (3 runs for 3).

## 15. The CLI-Dispatched Run: Word Garden 4 (examples/word-garden-4)

The run where the tool drove its own loop end to end (2026-06-12): same
Word Garden spec, byte-identical task-001 brief, same fleet mix and gate
as runs 1–2 — every worker and the reviewer dispatched as real `claude -p`
subprocesses by `python3 -m farnsworth run`, on a host whose subscription
OAuth let nested headless processes authenticate for the whole run (run 5
later found that auth can turn intermittent; Section 8). Run 4 happened in
parallel with run 3's session and independently exercised the same two
extensions — focus-diversified dispatch (Section 2.1) and a cross-project
tips seed (13 domain-general entries in round-1 `.code-tips.md`) — so its
results double as a same-day replication of Section 14's. Full forensics:
[`examples/word-garden-4/`](examples/word-garden-4/); process report in
its `.farnsworth/orchestrator-log.md`.

| Metric | task-001 (seed tips, 5 workers) | task-002 (seed + t1 tips, 3 triaged) |
|---|---|---|
| First-pass gate rate | 5/5 | 3/3 (one vacuous — empty diff) |
| Correctness bugs found in gate-passing field | 2 | 1 (+1 non-submission) |
| Verdict | adopt | adopt |
| Winning model (focus) | **Sonnet 4.6** (readability) | **Opus 4.8** (spec faithfulness) |
| Worker cost / reviewer cost | $3.03 / $3.61 (119%) | $3.60 / $3.40 (94%) |
| Wall clock | 13.5 min | 17 min |

What the run established:

1. **Configs are contracts; pre-flight them.** The fleet config recorded
   since run 1 had never executed, and canary tests found it 100% fatal
   twice over (`--bare` kills OAuth; headless `acceptEdits` denies Bash).
   Two new risk-table rows and a queued `farnsworth preflight` command.
2. **Seed tips transfer mechanical rules, not semantic ones.** The
   predicted argparse defect did not recur (seed bans it verbatim); the
   terminal-message defect class recurred anyway, same count and tier as
   the seedless replication — the domain-specific state contract must
   still be learned by THIS project's round 1. Both directions of
   "memory is project-scoped" now have evidence.
3. **Tier dominates focus.** First live focus round: foci measurably
   diversified style and both adopted candidates came from focused
   workers, but the test-rigor-focused Haiku still shipped the
   flag-only-assertion defect. A focus is a lens, not a capability tier.
4. **The loop caught — and now fixes — its own artifact-rule hole.** A
   no-commit worker gated PASS while its candidate diff was empty; the
   reviewer's empirical probe caught the 0-line "non-submission" and the
   verdict survived. The CLI now enforces commits-as-artifact mechanically
   (gate autopsy "no commits on branch", uncommitted work archived, empty
   diffs never labeled), plus a second live fix: `clean` now resolves the
   MAIN repo from inside a linked worktree. Defence in depth — a skeptical
   review layer — is what made the mechanical hole survivable.
5. **Wall-clock and dollars are now real numbers.** A full 5-worker
   tournament with empirical review: 13.5 minutes, ~$6.6. The two-task
   project: ~45 minutes, ~$13.6. The cheap-workers question (Section 3)
   can now accumulate dollar-denominated evidence per round.

## 16. The Goal-Driven Run: Word Garden 5 (examples/word-garden-5)

The fifth Word Garden run (2026-06-12) and the first project executed
under the Section 2.4 termination contract end to end: a goal brief +
six mechanical done checks seeded up front, ONE task derived from the
goal gap (the entire game, whole-program grain — Section 2.3's re-shot
attempt 1), and the exit decided by `farnsworth done` plus a reviewer
goal-attestation rather than a task list. Also first-run here: the
cross-project seed v2 (10 entries, including the generalized predicate
lesson — the run-3 "generalize while distilling" rule's first product)
and the CLI's constructed review environment (Section 8's reviewer-leak
mitigation, implemented in `farnsworth.loop` this run). Full forensics:
[`examples/word-garden-5/`](examples/word-garden-5/).

| Metric | task-001 (10 seed tips, 5 workers, whole-program grain) |
|---|---|
| First-pass gate rate | 5/5 (six checks, incl. per-task extensions as first-class config) |
| Engine-behavior bugs in field | **0** |
| Spec-deviation defects in field | 3 (ASCII growth-stage collapse) |
| Verdict | adopt |
| Winning model (focus) | **Sonnet 4.6** (readability) |
| Worker agent tokens | ~256k |
| Reviewer tournament tokens (share) | ~101k (39%) |
| Goal attestation tokens | ~68k |
| Iterations to goal (emergent) | **1** — exit DONE |

What it settled and surfaced:

1. **Settled: goal-driven cycling stops honestly.** The done probe and
   the attestation — not the orchestrator, not a list — ended the loop
   at one iteration. The re-shot never triggered because attempt 1 left
   no gap; that is the re-shot priced correctly (it measures learning
   exactly when there is something to learn).
2. **Settled: generalized seed entries widen memory's scope for free.**
   The tip-10 general form ("a standalone predicate must not rely on a
   caller's check ordering") was honored by all five candidates; the
   `is_lost` defect class that shipped in two prior projects' rounds
   was absent. Zero engine-behavior bugs in a whole-program field.
3. **Surfaced: the gate's blind spot has a sharper exemplar.** Three of
   five candidates passed the `plays-ascii` gate (exit 0, pure ASCII)
   while collapsing SPEC's five growth stages to 1–4 distinct glyphs.
   Gates verify exit codes and character sets; distinctness — meaning —
   was reviewer territory. Now distilled as project tips 11–15.
4. **Surfaced: fake-phase tests validate plumbing, not contracts.** The
   constructed review env worked on first live use, and first live use
   immediately caught a briefing bug the smoke test missed (briefed
   diff path != served diff path) because the fake reviewer globbed
   instead of following the briefing text.
5. **Economics: review share fell, attestation appeared.** Tournament
   review at ~39% of worker spend is the lowest recorded (pre-labeled
   diffs in a ready-made env cut review overhead), but each completed
   GOAL now carries one attestation dispatch — a fixed per-goal cost
   new to the ledger.
6. **Fourth confirmations:** identical file footprints even at
   whole-program grain (M4's divergence metric must read content);
   Haiku spending the field's most motion for a non-winning candidate;
   focus-alignment is not advantage (the accessibility-focused
   candidate shipped the worst ASCII display); duplicate dispatches
   absorbed by the artifact-boundary rule — this run in the attestation
   phase, a new artifact type, the rule working generically.
## 17. The Cross-Domain, Delegate-Dispatched Run: Wine Stock Report Generator (examples/wine-stock-report-generator-1)

The first subject outside the Word Garden family (2026-06-12), chosen to
test generalization on both axes at once: a NEW domain (a realistic
small-business CLI — warehouse stock CSV in, Markdown stock report out,
from a wine-industry PRD with an embedded real fixture) and a NEW
dispatch mode (the first live run of Section 4.1b delegate dispatch:
`run` → host-session worker subagents → `gate` → reviewer subagent →
`finalize` → `adopt --clean` → `done` → attestation, every mechanical
phase in the CLI). Run shape otherwise identical to word-garden-5:
goal-driven, whole-program grain, 12-entry seed, focus-diversified
2H/2S/1O fleet. Full forensics:
[`examples/wine-stock-report-generator-1/`](examples/wine-stock-report-generator-1/).

| Metric | task-001 (12 seed tips, 5 workers, whole-program grain) |
|---|---|
| First-pass gate rate | 5/5 (seven checks) |
| Behavioral bugs in field | 1 (parser over-rejection) |
| Spec-deviation defects | 1 (conditional Data Warnings section) |
| Test-quality defects | 2 (unexercised prompt seam; handle leaks) |
| Defects in seed-covered classes | **0** (12 entries audited) |
| Verdict | adopt |
| Winning model (focus) | **Opus 4.8** (report faithfulness) |
| Dispatch incidents | 2 (worker self-delegation; hung reviewer) — both absorbed |
| Divergence (content) | 0.64 — first run with the M4 metric recorded |
| Iterations to goal (emergent) | **1** — exit DONE |

What it settled and surfaced:

1. **Settled: the memory thesis crosses domains.** Zero defects in the
   classes the seed covers; ALL four field defects in classes no tip
   yet covered (conditional section rendering, tolerant-parser
   over-rejection, unexercised injection seams, test resource hygiene)
   — the word-garden-5 both-sides signature, reproduced in a
   CSV/reporting domain the seed had never seen. Three new generalized
   entries routed into the seed pile (entries 13–15).
2. **Surfaced: worker self-delegation, a new dispatch-failure class.**
   A worker spawned a nested agent and ended its turn with a confident
   completion claim and zero commits; its orphan later duplicated work
   in the same worktree. The artifact rule absorbed both halves.
   WORKER_PREAMBLE now forbids delegation (risk table updated).
3. **Surfaced: the review protocol's cleanup instruction was wrong for
   greenfield.** A hung reviewer's forensics showed why: `git apply` of
   an all-new-files candidate leaves it UNTRACKED, `reset --hard`
   cannot remove it, and naive `git clean -fd` would destroy the
   reviewer's notes. Briefing fixed in the CLI
   (`reset --hard && clean -fd -e .farnsworth`), with tests.
4. **Settled: delegate dispatch works end-to-end** — worktrees,
   briefings, ledger, commit-as-artifact, hygiene gate, constructed
   review env, verdict validation, adopt, done probe all mechanical;
   only the agent phases ran as subagents. Trade-off confirmed: no
   per-worker dollar stream (token counts recorded in the process log).
5. **Focus-alignment ≠ advantage, fifth round — now from both
   directions at once:** the verdict's discriminator was test rigor;
   the test-rigor-focused worker lost on an entirely untested prompt
   path while the report-faithfulness-focused worker won ON test rigor.
6. **Queued (greenfield ergonomics):** preflight's `gate-at-base` is
   red by design on a round-1 seed and needs a greenfield-aware
   diagnosis (one exit-code check also passed at base for the wrong
   reason); `run`/`prepare` refuses untracked `.farnsworth/` files that
   `adopt` tolerates — the orchestrator log had to be committed
   mid-flow; `gate` should copy the review briefing INTO the review env
   so the reviewer never reads outside its directory.

-----

*Ralph persists. Karpathy measures. Farnsworth learns.*

*Good news, everyone!*
