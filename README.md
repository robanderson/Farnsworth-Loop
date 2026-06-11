# Farnsworth Loop: Reference Implementation PRD

**Author:** Rob Anderson
**Date:** 12 June 2026
**Status:** Draft v1.0
**Repo:** farnsworth-loop

-----

## 1. Thesis

Agent loops differ on one axis: what flows through the feedback path.

- **Ralph Loop:** no feedback. Same prompt, fresh context, persistence as strategy. Open-loop control.
- **Karpathy Loop:** scalar feedback. Keep or discard against a metric. A thermostat. Requires a cheap, evaluable metric, which most software work does not have.
- **Farnsworth Loop:** semantic feedback. An intelligent review phase distills verbal lessons from every attempt (winners and losers) into a persistent knowledge artifact that is injected into every future worker briefing. The models never get smarter; the project does.

The defining property: **failures are not wasted tokens, they are gotchas passed forward.** Knowledge compounds in the context layer, where it is inspectable, diffable, and versioned in git alongside the code it describes.

This PRD specifies a minimal reference implementation using the Anthropic ecosystem only.

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

Worker diversity note: within one model family, diversity comes from capability tiers rather than architecture. The 2x Haiku / 2x Sonnet / 1x Opus mix is also an experiment in itself: per-model win rates (Section 7) will show whether cheap workers plus a strong reviewer match expensive workers, which is the economic question the loop exists to answer.

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

### 4.3 State and audit

All loop state is file-based and inspectable: task briefs, candidate diffs, gate results, review documents, verdicts, and the tips file all live in the repo (under `.farnsworth/` for per-task artifacts). No database. A human can reconstruct any decision from git history alone.

## 5. MVP Scope

In scope:

- Single-task loop, CLI-invoked: `farnsworth run task-brief.md`
- Parallel blind dispatch to the 5-worker fleet via worktrees
- Mechanical gate (configurable build/test/lint commands)
- Anonymized review with three-outcome verdict
- `.code-tips.md` lifecycle (reviewer-written, worker-injected, provenance-stamped)
- Divergence-triggered two-round mode
- JSON run log per task with per-model costs (from `--output-format json`)

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
|Billing surprises                       |From 15 June 2026, `claude -p` on subscription plans draws from a separate monthly Agent SDK credit; budget accordingly or run workers on API keys                       |

## 9. Milestones

1. **M1, Skeleton:** dispatch + worktrees + gate, single Haiku worker, no review. Proves plumbing.
1. **M2, Tournament:** full 5-worker blind dispatch, anonymized review, three-outcome verdict, manual merge.
1. **M3, Memory:** `.code-tips.md` lifecycle + injection + consolidation pass. The loop is now a Farnsworth Loop.
1. **M4, Adaptive:** divergence measurement + two-round mode + triage rule.
1. **M5, Instrumentation:** metrics dashboard from JSON logs; publish gate-success-over-time chart in the README.
1. **M6, Theater:** TUI memory-map visualization of the fleet (post-MVP, separate doc).

## 10. Acceptance Criteria (faithfulness contract)

Later agents and reviewers score the implementation against this checklist:

- [ ] Workers are blind: no candidate ever enters another worker’s context in the same round.
- [ ] Workers never write `.code-tips.md`.
- [ ] Review is anonymized and order-randomized.
- [ ] Every verdict is exactly one of adopt / synthesize / escalate, recorded in the task log.
- [ ] Reviewer’s blind sketch exists before candidate review in every synthesize verdict.
- [ ] Every tips entry has date + provenance.
- [ ] Round 2 workers receive updated tips but no round 1 diffs.
- [ ] All decisions reconstructible from git history alone (no hidden state).
- [ ] A human can read `.code-tips.md` in under two minutes (consolidation is working).
- [ ] Gate-success-over-time chart exists and is generated from real run logs.

-----

*Ralph persists. Karpathy measures. Farnsworth learns.*

*Good news, everyone!*