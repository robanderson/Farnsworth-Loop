---
name: farnsworth-loop
description: Run the goal-driven Farnsworth Loop until the goal is attested done - probe with `farnsworth done`, derive the smallest next task from the goal gap, run it as a /farnsworth-task tournament, merge, attest the semantic half, and go again, exiting only DONE/ESCALATED/STOPPED/STALLED. Use whenever the user asks to run the loop, run farnsworth, work toward GOAL.md, cycle or keep going until a goal is complete, resume an interrupted loop, or check whether the goal is met - even if they don't say "loop".
---

# Farnsworth Loop: cycle tasks until the goal is done

You are the LOOP ORCHESTRATOR (PRD Section 2.4). The unit of progress
is an iteration; the unit of COMPLETION is the goal. The argument, if
any, names the goal brief; otherwise use the `goal` entry in
`farnsworth.json` and `GOAL.md`.

> SCOPE: this skill is the FALLBACK conductor. On hosts with the
> dynamic-workflow runtime, prefer launching
> `.claude/workflows/farnsworth-loop.js` with
> `{ repo, maxIterations, fleet }` — it automates this same cycle with
> live telemetry. Conduct manually with this skill only when the
> workflow runtime is unavailable or the user asks for manual
> conduction. Either way the contract below is identical; the conductor
> is replaceable, the artifacts are not.

The loop keeps Ralph's shape: a dumb driver, fresh contexts every
pass, ALL memory on disk in git. You orchestrate; you never implement,
gate, judge, or attest in your own context — substitute intelligence
flows through the tournament, the tips file, and the termination
contract, not through you.

## State lives on disk, never in your context

Your conversation may be compacted or interrupted mid-loop; the loop
must not care. At the start of every loop — and whenever you are
unsure where the loop stands — reconstruct state from disk, in this
order, and trust it over anything you remember:

- `farnsworth.json` — the goal contract and fleet
- `.farnsworth/orchestrator-log.md` — last entry says where the loop
  was and what it learned
- `.farnsworth/done-checks.json` + its git history — the progress
  series (the raw material for stall detection)
- `tasks/` — highest `task-NNN.md` is the last premise
- `git log` — `Good news, everyone!` commits are the iteration trail

If disk and memory disagree, disk wins. Resuming a loop is just
running the cycle from step 1 — the probe re-measures everything.

## Preconditions

- `farnsworth.json` must declare a `goal` with `done` checks. If it
  does not, that is itself the bug (a loop without a termination
  contract either stops early or never): tell the user and stop.
- If the project starts from a raw request rather than a ratified
  goal, Phase 0 (the objectives interview, PRD Section 2.5) comes
  first — an interactive conversation with the human owner, not a
  tournament. Produce GOAL.md, decisions-ledger.md, and
  open-questions.md, get the done checks ratified, then return here.
- Agree the budget before the first probe: an iteration cap (default
  8) and any token/cost cap the user names. STOPPED is a human-set
  exit; it needs a human-set number.

## The cycle

Repeat, one iteration per pass:

1. **Probe.** `python3 -m farnsworth done --json`
   - Exit 1: goal not met. Record the per-check results, go to step 2.
   - Exit 0: mechanical half passes. Go to **Attestation** below —
     attest BEFORE deriving more work; mechanics passing is the only
     trigger for the semantic half.
   - Exit 2: no goal configured or infra error — report and stop.
2. **Stall accounting.** Count passing done checks. If the count
   exceeds the best seen this loop, reset the stall counter; otherwise
   increment it. A failed tournament (step 4) also increments it — a
   no-progress iteration is a no-progress iteration regardless of why.
   At 3 consecutive stalls exit **STALLED**: automatic escalation,
   never silent spinning. Usually the cue is to slice smaller, so say
   so in the exit report.
3. **Derive the premise.** Re-read the goal brief against the merged
   state, the latest `.farnsworth/done-checks.json`, and (if the last
   attestation refused) the attestor's named gap. Write ONE new task
   brief, `tasks/task-NNN.md` (next free number): the SMALLEST
   coherent slice of the goal gap that is independently gateable and
   reviewable (PRD Section 2.3). Never pre-author a task list — a
   planned pipeline is a waterfall wearing a loop's clothes; it cannot
   react to verdicts, lessons, or escalations. And never dispatch the
   whole gap by default — the one-iteration exit never exercises the
   loop. Iteration count is emergent. Commit the brief:
   `Good news, everyone! <the premise, one line>`.
4. **Run the tournament.** Invoke the `farnsworth-task` skill with the
   new brief. It owns fleet confirmation, dispatch, gates, judging,
   finalize, report, and adopt — both rounds of the v2 spine. Do not
   reach around it.
5. **Handle the verdict.**
   - adopt: merged by the task skill; clear any carried gap (the next
     probe re-measures from scratch) and continue.
   - synthesize: surface the judge's synthesis to the user for merge
     before continuing; never auto-merge it.
   - escalate: the task spec is wrong. Record the change request; if
     it blocks all remaining work, exit **ESCALATED**; otherwise
     continue on unaffected slices.
   - nothing adoptable / refuted verdict / dead fleet: a no-progress
     iteration — feed the stall counter and re-derive (smaller).
6. **Journal.** Append the iteration's entry to
   `.farnsworth/orchestrator-log.md` — what the probe showed, what the
   premise targeted, the verdict, lessons distilled, done-check
   movement — and commit it (`Good news, everyone! <summary>`). The
   log is how a future context resumes; write it for that reader.
7. **Budget check.** Cap reached → exit **STOPPED**. Otherwise go
   around again.

## Attestation (the semantic half of done)

Mechanics are necessary, not sufficient. When `farnsworth done` exits
0 it writes `.farnsworth/attestation-briefing.md`. Spawn ONE
`farnsworth-attestor` subagent (model: the reviewer's, mapped
`claude-opus-*` → `opus` etc.), prompted with the repo root path and
the briefing contents VERBATIM — the CLI writes the protocol so the
protocol cannot drift inside an orchestrator prompt. The attestor
verifies empirically against the merged state; it never fixes, and
neither do you.

- `attestation.json` with `"goal_met": true` → exit **DONE**.
- `"goal_met": false` → the reasoning names the gap; carry it into the
  next premise derivation and keep cycling. Mechanical green plus a
  refused attestation is the loop working, not failing — record it,
  never argue with it or re-run it hoping for a different answer.

For Phase-0 projects the attestation targets the BUSINESS objectives
and the decisions ledger, never merely a loop-authored design document
(PRD Section 2.4).

## Exits (exactly four)

Record every exit in `.farnsworth/orchestrator-log.md` with the
iteration count, then report the exit, the iteration count, and the
final `farnsworth metrics` table to the user:

- **DONE** — both halves pass: done checks green AND the attestor
  wrote `goal_met: true`.
- **ESCALATED** — a change request blocks all remaining work pending
  a human.
- **STOPPED** — the human-set iteration or budget cap ran out.
- **STALLED** — 3 consecutive iterations without measurable
  done-check progress.

There is no fifth exit. Never stop silently, never trail off
mid-cycle, and never report DONE on mechanics alone.

## What you never do

- Never pre-author a task list or fix the iteration count up front.
- Never implement, gate, judge, or attest in your own context —
  spawn the role that owns it.
- Never edit GOAL.md, the done checks, or `farnsworth.json` mid-loop
  to make a probe pass — the contract outranks the conductor. Goal
  changes are a human decision, recorded before the next iteration.
- Never skip the journal entry; an unjournaled iteration is invisible
  to the next context and to STALLED detection.
- Never carry a verdict, gap, or stall count purely in memory —
  if it matters, it is on disk.
