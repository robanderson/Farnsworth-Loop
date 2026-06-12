---
name: farnsworth-loop
description: Run the goal-driven Farnsworth Loop until the goal is done - derive the next task from the goal gap, run each task as a /farnsworth-task tournament, probe completion with `farnsworth done`, dispatch the farnsworth-attestor for the semantic half, and exit DONE/ESCALATED/STOPPED/STALLED. Use when asked to run the loop, work toward GOAL.md, or cycle tasks until a goal is complete.
---

# Farnsworth Loop: cycle tasks until the goal is done

You are the LOOP ORCHESTRATOR (PRD Section 2.4). The unit of progress is
an iteration; the unit of COMPLETION is the goal. The argument, if any,
names the goal brief; otherwise use the `goal` entry in `farnsworth.json`
and `GOAL.md`.

## Preconditions

- `farnsworth.json` must declare a `goal` with `done` checks. If it does
  not, that is itself the bug (a loop without a termination contract
  either stops early or never): tell the user and stop.
- If the project starts from a raw request rather than a ratified goal,
  Phase 0 (the objectives interview, PRD Section 2.5) comes first — that
  is an interactive conversation with the human owner, not a tournament.
  Produce GOAL.md, decisions-ledger.md, and open-questions.md, then
  return here.

## The cycle

Repeat, one iteration per pass:

1. **Probe.** `python3 -m farnsworth done`
   - Exit 1: the goal is not met. Continue to step 2.
   - Exit 0: mechanical half passes. Go to **Attestation** below.
   - Exit 2: no goal configured or infra error — report and stop.
2. **Derive the next task.** Re-read the goal brief against the merged
   state and the latest `.farnsworth/done-checks.json`. Write ONE new
   task brief, `tasks/task-NNN.md` (next free number): the SMALLEST
   coherent slice of the goal gap that is independently gateable and
   reviewable (PRD Section 2.3). Never pre-author a task list, and never
   dispatch the whole gap by default. Commit the brief.
3. **Run the tournament.** Invoke the `farnsworth-task` skill with the
   new brief. It dispatches the coder subagents, the judge, finalize,
   report, and adopt.
4. **Handle the verdict.**
   - adopt: merged by the task skill; continue.
   - synthesize: surface to the user for merge before continuing.
   - escalate: record the change request; if it blocks all remaining
     work, exit **ESCALATED**; otherwise continue on unaffected slices.
5. **Journal.** Append the iteration's entry to
   `.farnsworth/orchestrator-log.md` (what merged, the verdict, lessons
   distilled, done-check movement) and commit it with the convention
   `Good news, everyone! <summary>`.
6. **Stall check.** Compare the done-check series in git history: no
   measurable progress (no new checks passing, defect ledger not
   shrinking) for 3 consecutive iterations exits **STALLED** — an
   automatic escalation, never silent spinning.
7. **Budget check.** If the user set an iteration or budget cap and it
   is exhausted, exit **STOPPED**.

## Attestation (the semantic half of done)

When `farnsworth done` exits 0 it writes
`.farnsworth/attestation-briefing.md`. Spawn ONE `farnsworth-attestor`
subagent (model: the reviewer's, mapped `claude-opus-*` → `opus` etc.),
prompted with the repo root path and the briefing contents VERBATIM.

- `attestation.json` with `"goal_met": true` → exit **DONE**.
- `"goal_met": false` → the reasoning names the gap; feed it into step 2
  and keep cycling. Mechanical green plus a refused attestation is the
  loop working, not failing.

## Exits (exactly four)

Record every exit in `.farnsworth/orchestrator-log.md` with the
iteration count: **DONE** (both halves pass), **ESCALATED** (a change
request blocks all remaining work pending a human), **STOPPED**
(human-set budget or cap ran out), **STALLED** (3 iterations without
measurable progress). Report the exit, the iteration count, and the
final `farnsworth metrics` table to the user.
