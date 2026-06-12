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

1. **Dispatch.** Orchestrator creates one git worktree per worker and dispatches the same task brief to all workers in parallel. Each brief is: current `.code-tips.md` + task specification. Workers run blind: no worker sees another worker’s output, and no worker sees its own prior attempts.
1. **Gate.** Each worktree passes a mechanical filter before any model judges it: build succeeds, tests pass, linter passes. Failures are reduced to a one-line autopsy (“Worker C: 3 test failures in auth”). Only passing candidates proceed to full review.
1. **Review.** The reviewer receives passing diffs labeled A, B, C in randomized order with no model attribution, plus one-line autopsies of the failures, and scores all candidates against the task’s acceptance criteria. The review covers what is good AND bad in each implementation, not just a ranking.
1. **Verdict.** Exactly one of three outcomes:
- **Adopt:** one candidate is correct and complete; merge it as-is.
- **Synthesize:** no candidate is adequate but the field contains usable insight; the reviewer authors a fresh implementation informed by the candidates and critique. The reviewer must sketch its own approach BEFORE reading candidates (anchoring defence; its blind sketch counts as candidate n+1).
- **Escalate:** the task specification itself is wrong or ambiguous; file a change request to the orchestrator. Hints never silently amend the contract.
1. **Distill.** The reviewer writes durable lessons from this iteration into `.code-tips.md`. Only the review phase may write this file; workers are read-only consumers. Commit message convention: `Good news, everyone! <summary of lesson>`.
1. **Merge.** Winning diff merges to main. Worktrees are destroyed. Loop continues.

### 2.1 Two-Round Mode (divergence-triggered)

After the gate, the orchestrator measures divergence across candidates (approach, decomposition, files touched). If candidates substantially agree, proceed to review normally. If they scatter, the task was ambiguous: run the review and distillation, then re-dispatch the same task as a fresh blind round where workers receive the updated `.code-tips.md` but NOT the round 1 diffs. Distillation is the anti-anchoring filter: lessons travel, diffs do not. Two rounds maximum per task; a second scatter is an automatic escalation.

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

## 5. MVP Scope

In scope:

- Single-task loop, CLI-invoked: `farnsworth run task-brief.md`
- Parallel blind dispatch to the 5-worker fleet via worktrees
- Mechanical gate (configurable build/test/lint commands)
- Anonymized review with three-outcome verdict
- `.code-tips.md` lifecycle (reviewer-written, worker-injected, provenance-stamped)
- Divergence-triggered two-round mode
- JSON run log per task with per-model costs (from `--output-format json`)
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
|Hung, orphaned, or duplicated dispatches|*(observed: Word Garden example — a duplicate task-001 reviewer stalled for 35+ min after an infra retry)* Housekeeping rules in Section 4.3: per-command timeouts, artifact-is-the-phase-boundary idempotency, `farnsworth clean` before re-dispatch; ledger + liveness checks in manual mode|

## 9. Milestones

1. **M1, Skeleton** — ✅ **done (task-001, adopted from a 5-way tournament):** dispatch + worktrees + gate + JSON run log, single worker. Proves plumbing.
1. **M2, Tournament** — ✅ **done (task-002, adopted from a 5-way tournament):** full multi-worker blind dispatch, anonymized review briefing, configurable reviewer, three-outcome verdict, manual merge.
1. **M3, Memory:** `.code-tips.md` lifecycle + injection + consolidation pass automated in the CLI. (The lifecycle is already running manually — two distillation commits so far — M3 moves it into the tool.)
1. **M4, Adaptive:** divergence measurement + two-round mode + triage rule.
1. **M5, Instrumentation:** metrics dashboard from JSON logs; publish gate-success-over-time chart in the README.
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
- [ ] Gate-success-over-time chart exists and is generated from real run logs. *(M5; two data points banked)*

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

-----

*Ralph persists. Karpathy measures. Farnsworth learns.*

*Good news, everyone!*
