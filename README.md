# Good News, Everyone!

# Farnsworth Loop: Reference Implementation PRD

**Author:** Rob Anderson
**Date:** 12 June 2026
**Status:** Draft v1.1 (revised 11 June 2026 after dogfooding tasks 001–002 — yes, the loop shipped a day before its own PRD date)
**Repo:** farnsworth-loop

-----

## 1. Thesis

Agent loops differ on one axis: what flows through the feedback path.

- **Ralph Loop:** no feedback. Same prompt, fresh context, persistence as strategy. Open-loop control.
- **Karpathy Loop:** scalar feedback. Keep or discard against a metric. A thermostat. Requires a cheap, evaluable metric, which most software work does not have.
- **Farnsworth Loop:** semantic feedback. An intelligent review phase distills verbal lessons from every attempt (winners and losers) into a persistent knowledge artifact that is injected into every future worker briefing. The models never get smarter; the project does.

The defining property: **failures are not wasted tokens, they are gotchas passed forward.** Knowledge compounds in the context layer, where it is inspectable, diffable, and versioned in git alongside the code it describes.

This PRD specifies a minimal reference implementation using the Anthropic ecosystem only.

> **Dogfooding status:** M1 and M2 were themselves built by running the loop — five blind parallel workers per task, mechanical gate, anonymized Opus review, verdict, distillation. The thesis has its first data: the round-1 winner (empty tips file) was Opus; the round-2 winner (14 distilled lessons in the briefing) was Haiku. Same models, better project. See Section 11 and `.farnsworth/orchestrator-log.md`.

## 2. Core Loop

```
TASK -> DISPATCH (parallel, blind) -> GATE (mechanical) -> REVIEW (anonymized)
     -> VERDICT (adopt | synthesize | escalate) -> DISTILL (update .code-tips.md)
     -> MERGE -> next TASK
```

One iteration in detail:

1. **Dispatch.** Orchestrator creates one git worktree per worker and dispatches the same task brief to all workers in parallel. Each brief is: current `.code-tips.md` + task specification + an optional per-worker **focus directive** (Section 2.1). Workers run blind: no worker sees another worker’s output, no worker sees another worker’s focus, and no worker sees its own prior attempts.
1. **Gate.** Each worktree passes a mechanical filter before any model judges it: build succeeds, tests pass, linter passes. Failures are reduced to a one-line autopsy (“Worker C: 3 test failures in auth”). Only passing candidates proceed to full review.
1. **Review.** The reviewer receives passing diffs labeled A, B, C in randomized order with no model attribution, plus one-line autopsies of the failures, and scores all candidates against the task’s acceptance criteria. The review covers what is good AND bad in each implementation, not just a ranking.
1. **Verdict.** Exactly one of three outcomes:
- **Adopt:** one candidate is correct and complete; merge it as-is.
- **Synthesize:** no candidate is adequate but the field contains usable insight; the reviewer authors a fresh implementation informed by the candidates and critique. The reviewer must sketch its own approach BEFORE reading candidates (anchoring defence; its blind sketch counts as candidate n+1).
- **Escalate:** the task specification itself is wrong or ambiguous; file a change request to the orchestrator. Hints never silently amend the contract.
1. **Distill.** The reviewer writes durable lessons from this iteration into `.code-tips.md`. Only the review phase may write this file; workers are read-only consumers. Commit message convention: `Good news, everyone! <summary of lesson>`.
1. **Merge.** Winning diff merges to main. Worktrees are destroyed. Loop continues.

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
- **Round 2 narrows.** When two-round mode triggers, the orchestrator may
  drop or re-aim foci for the re-dispatch: round 1 explores, distillation
  extracts what the exploration taught, round 2 converges on it.

### 2.2 Two-Round Mode (divergence-triggered)

After the gate, the orchestrator measures divergence across candidates (approach, decomposition, files touched). If candidates substantially agree, proceed to review normally. If they scatter, the task was ambiguous: run the review and distillation, then re-dispatch the same task as a fresh blind round where workers receive the updated `.code-tips.md` but NOT the round 1 diffs. Distillation is the anti-anchoring filter: lessons travel, diffs do not. Two rounds maximum per task; a second scatter is an automatic escalation.

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
the loop can produce. No recorded run has used the re-shot grain yet; it
is the queued design for the next example.

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

## 3. Roles and Models

All roles run Claude Code headless (`claude -p`) within the Anthropic ecosystem.

|Role                  |Model                           |Count|Responsibility                                                                                       |
|----------------------|--------------------------------|-----|-----------------------------------------------------------------------------------------------------|
|Orchestrator (PM)     |Fable 5 (`claude-fable-5`)      |1    |Task decomposition, dispatch, worktree lifecycle, divergence measurement, CR handling, loop control  |
|Reviewer (Team Leader)|Opus 4.8 (`claude-opus-4-8`)    |1    |Gate interpretation, anonymized review, verdict, synthesis authorship, sole writer of `.code-tips.md`|
|Worker                |Haiku 4.5 (`claude-haiku-4-5`)  |2    |Blind implementation attempts                                                                        |
|Worker                |Sonnet 4.6 (`claude-sonnet-4-6`)|2    |Blind implementation attempts                                                                        |
|Worker                |Opus 4.8 (`claude-opus-4-8`)    |1    |Blind implementation attempts (strongest independent candidate)                                      |

Worker diversity note: within one model family, diversity comes from capability tiers rather than architecture. The 2x Haiku / 2x Sonnet / 1x Opus mix is also an experiment in itself: per-model win rates (Section 7) will show whether cheap workers plus a strong reviewer match expensive workers, which is the economic question the loop exists to answer. *Early returns (Section 11): after one distillation cycle, a Haiku worker won the tournament outright.*

## 4. Mechanism

### 4.1 Worker dispatch

Each worker is a headless Claude Code process in its own worktree:

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

`--bare` keeps workers from inheriting orchestrator config (hooks, skills, CLAUDE.md). The worktree contains the blast radius of `acceptEdits`. Workers commit to their branch; the diff against main is the deliverable.

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

Every run additionally produces a short what-happened table — one row per worker (id, focus, exit, gate, candidate label, ADOPTED marker) plus the verdict and reasoning — written to `.farnsworth/<task-id>/summary.md`, printed at the end of `farnsworth run`, and reprintable any time with `farnsworth report <task-id>`. The table is the thirty-second read; `run.json` remains the contract of record.

Whenever a verdict merges code, the summary also carries a reviewer-authored **progression note** (`review.progression` in `run.json`): how the merged code advances the previously adopted baseline — what it built on, what is new, what got better relative to the prior merged state, and which distilled lessons it visibly absorbed. The verdict reasoning explains why the winner beat the *field*; the progression note explains how the *project* moved. Without it, a reader of task-N's summary learns who won round N but not what round N added to rounds 1..N-1 — the exact question an outside user asks first. The reviewer writes it post-verdict (it has the cross-candidate and cross-task view); the orchestrator records it in `run.json` so `farnsworth report` reproduces it from the log alone. Under a re-shot task (Section 2.3) the baseline is the previous *attempt*, and the progression note becomes the loop's learning measurement itself: how attempt 2 improved on attempt 1.

## 5. MVP Scope

In scope:

- Single-task loop, CLI-invoked: `farnsworth run task-brief.md`
- Parallel blind dispatch to the 5-worker fleet via worktrees
- Mechanical gate (configurable build/test/lint commands)
- Anonymized review with three-outcome verdict
- `.code-tips.md` lifecycle (reviewer-written, worker-injected, provenance-stamped)
- Divergence-triggered two-round mode
- Per-worker focus directives with unattributed disclosure to the reviewer (Section 2.1)
- JSON run log per task with per-model costs (from `--output-format json`)
- Run summary table: `.farnsworth/<task-id>/summary.md` + `farnsworth report <task-id>`, including the reviewer's progression note on merging verdicts (Section 4.4)
- Housekeeping: per-command `timeout_seconds` and `farnsworth clean <task-id>` (Section 4.3)

Explicit non-goals (MVP):

- No UI before the markdown loop works end to end. The TUI memory-map aesthetic is a later milestone, not MVP.
- No task queue, scheduler, or daemon. One task per invocation.
- No cross-provider workers (GLM, MiniMax, Codex, local models). The dispatch interface must not preclude them, but MVP is Anthropic-only by design.
- No autonomous PRD/contract mutation. Escalations surface to a human.
- No fine-tuning, no embeddings, no vector store. The context layer is the only memory.

## 6. Maintenance Loops

- **Consolidation pass:** every N merged tasks (default 10), the reviewer audits `.code-tips.md` against the current codebase: merge duplicates, retire stale entries (with a tombstone note in the commit), and compress. This is doc-rot management as a first-class scheduled job.
- **Escalation queue:** CRs filed by the reviewer accumulate as issues for human ratification. The loop may continue on unaffected tasks while a CR is pending.

## 7. Metrics (the loop’s own health)

1. **First-pass gate success rate over time.** The primary KPI. If the loop is learning, this climbs as tips accumulate. Plateau or decline means the tips file has rotted or bloated.
1. **Per-model win rate** (adopted candidates by model) and per-model gate pass rate. Informs future routing and answers the cheap-workers question.
1. **Verdict distribution** (adopt / synthesize / escalate). A rising synthesize rate means workers are underpowered or briefs are poor; a rising escalate rate means the spec process is broken.
1. **Cost per merged task** (sum of per-invocation costs from JSON output), tracked against verdict type.
1. **Round 2 trigger rate.** How often divergence forces a second round; a proxy for task ambiguity.

All metrics derive from the per-task JSON logs; a single script renders the dashboard. The chart that matters: gate success rate (y) against merged task count (x). Up and to the right means Farnsworth is learning.

*Measurement note from dogfooding: gate rate saturated immediately (5/5 both rounds), so it is a weak early signal on small tasks. The discriminating early metrics turned out to be field quality (spec/hygiene violations per round: 2 then 0) and reviewer-found defects in gate-passing candidates (2 per round so far) — the gate cannot see contract faithfulness. Track these alongside the headline chart.*

*Second measurement note from the Word Garden example: track per-ATTEMPT cost alongside per-model win rate — in the 5-way round, Opus won with the fewest tokens of the field (~31k, 12 tool calls) while a Haiku burned ~76k/64 calls on a weaker candidate; "cheap model" and "cheap attempt" are different quantities. And under triage the reviewer's SHARE of spend rises (50% -> 68% observed) even as absolute cost falls, because review depth is fixed while the field shrinks.*

*Third measurement note, from the Word Garden 2 replication (Section 13): defects-per-round in gate-passing candidates is the loop's primary EARLY learning signal — it improved under tips in both runs (1→0, 2→1) while the winning model's identity did not reproduce (metric 2 is long-horizon, noisy at one round per cell). Reviewer share also tracks worker economy, not just field size: a triaged round with heavy worker attempts kept the reviewer at ~55%, not the 68% seen before.*

*Fourth measurement note, from Word Garden 3 (Section 14): count defects per round in two ledgers — BEHAVIORAL bugs and CONTRACT-level deviations — and attribute each to whether a tips entry covered its class. Attribution is the seed experiment's real readout: in run 3, every defect class covered by a seed entry was absent from the field, and the one behavioral bug that shipped was exactly the lesson the domain-general curation rule had excluded from the seed. Also: with foci in play, record the winning FOCUS alongside the winning model; two rounds in, focus-task alignment predicts where candidates invest, not who wins.*

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
|Billing surprises                       |From 15 June 2026, `claude -p` on subscription plans draws from a separate monthly Agent SDK credit; budget accordingly or run workers on API keys                       |
|Nested `claude -p` cannot authenticate in managed sandboxes|*(observed: Word Garden example)* Credentials are host-managed FDs that child processes don't inherit. Dispatch is conceptually an adapter: the same blind/anonymized protocol runs via agent-tool sub-agents (manual mode) — used for tasks 001–002 and the Word Garden example                  |
|Host git config forces commit signing   |*(observed: Word Garden example)* Global `commit.gpgsign=true` with a session-scoped signer fails every scratch/worktree commit; seed repos with repo-local `commit.gpgsign=false` (worktrees inherit it). The test suite is hermetic against this since task-002                              |
|Focus directive read as a contract amendment|Dispatch wrapper appends an explicit precedence sentence (brief wins); reviewer scores against acceptance criteria only; per-candidate focus sealed until post-verdict (Section 2.1)                                                                  |
|Single-round wins read as a trend       |*(observed: Word Garden 2)* The cheaper-model-wins streak broke on replication while the defect-floor effect held; treat per-model win rate as long-horizon, score learning by defects-per-round (Sections 7, 13)                                            |
|Hung, orphaned, or duplicated dispatches|*(observed: Word Garden example — a duplicate task-001 reviewer stalled for 35+ min after an infra retry; Word Garden 3 — duplicates in every background phase, all absorbed)* Housekeeping rules in Section 4.3: per-command timeouts, artifact-is-the-phase-boundary idempotency, `farnsworth clean` before re-dispatch; ledger + liveness checks in manual mode|
|Reviewer environment leaks worker identity |*(observed: Word Garden 3)* A naive clone for the reviewer carries worker-named branches (`task-001-w1`…), de-anonymizing candidates by id. Construct the review environment: base tree + labeled diffs + gate notes ONLY — no refs, no worktrees, no mapping files                                  |
|Workers "improve" a required signature     |*(observed: Word Garden 3 — an extra `new_game_fn` param forfeited an otherwise-winning candidate)* Briefs and tips state required signatures are exact and CLOSED contracts; proposed improvements go to escalation or a follow-up task, never silently into the diff                          |

## 9. Milestones

1. **M1, Skeleton** — ✅ **done (task-001, adopted from a 5-way tournament):** dispatch + worktrees + gate + JSON run log, single worker. Proves plumbing.
1. **M2, Tournament** — ✅ **done (task-002, adopted from a 5-way tournament):** full multi-worker blind dispatch, anonymized review briefing, configurable reviewer, three-outcome verdict, manual merge.
1. **M3, Memory:** `.code-tips.md` lifecycle + injection + consolidation pass automated in the CLI, **plus the cross-project tips seed** — validated live in Word Garden 3 (Section 14): a 9-entry domain-general seed suppressed every defect class it covered, in a fresh project, in both rounds. M3 also adopts the run-3 distillation refinement: when a project lesson instantiates a general class, the reviewer writes the general form for the seed pile and the specific form for project tips.
1. **M4, Adaptive:** divergence measurement + two-round mode + triage rule. *(Focus-diversified dispatch — the divergence FORCING half of this milestone — shipped 2026-06-12 and had its first live tournament in Word Garden 3: foci measurably spread the field with zero contract-amendment misreads. The measurement half has a confirmed requirement from three runs: file footprints are identical even under deliberate diversification — the metric must read content, not file lists, or round 2 will never trigger on well-briefed tasks.)*
1. **M5, Instrumentation:** metrics dashboard from JSON logs; publish gate-success-over-time chart in the README. *(First piece shipped 2026-06-12: per-run summary table in `summary.md` / `farnsworth report`, generated retroactively for all six recorded runs.)*
1. **M6, Theater:** TUI memory-map visualization of the fleet (post-MVP, separate doc).

## 10. Acceptance Criteria (faithfulness contract)

Later agents and reviewers score the implementation against this checklist:

- [x] Workers are blind: no candidate ever enters another worker’s context in the same round. *(tasks 001–002: isolated worktrees, no cross-contamination)*
- [x] Workers never write `.code-tips.md`. *(one task-001 worker committed the seed file byte-identical — flagged in review, rule distilled, zero recurrence in task-002)*
- [x] Review is anonymized and order-randomized. *(labels shuffled; attribution sealed outside the repo until post-verdict)*
- [x] Every verdict is exactly one of adopt / synthesize / escalate, recorded in the task log. *(2/2 recorded in run.json)*
- [x] Reviewer’s blind sketch exists before candidate review in every synthesize verdict. *(blind sketch produced in both reviews, though both verdicts were adopt)*
- [x] Every tips entry has date + provenance.
- [ ] Round 2 workers receive updated tips but no round 1 diffs. *(not yet exercised — no divergence trigger so far)*
- [x] All decisions reconstructible from git history alone (no hidden state).
- [x] A human can read `.code-tips.md` in under two minutes (consolidation is working). *(~35 lines after two distillations)*
- [ ] Gate-success-over-time chart exists and is generated from real run logs. *(M5; six data points banked)*
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

-----

*Ralph persists. Karpathy measures. Farnsworth learns.*

*Good news, everyone!*
