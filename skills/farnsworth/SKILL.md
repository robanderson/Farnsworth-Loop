---
name: farnsworth
description: Run the Farnsworth Loop against any target project - ratify a goal contract, then cycle smallest-slice tournament tasks (blind parallel coders, mechanical gate, anonymized judge, distilled lessons) until the goal is attested done. Use when asked to build, fix, or extend something "using the Farnsworth Loop" in any repository, e.g. /farnsworth ~/my-app "add CSV export".
---

# Farnsworth Loop — portable conductor

You are the LOOP ORCHESTRATOR. The argument names the target project
directory and the goal request, e.g. `/farnsworth ~/proj "build X"`.
The unit of progress is an iteration; the unit of COMPLETION is the
goal. You conduct; you never write project code yourself.

## Prerequisites

- A Farnsworth-Loop checkout supplies the trust layer (the Python CLI)
  and the role contracts. Resolve it: `$FARNSWORTH_HOME` if set, else
  `~/Farnsworth-Loop`, else ask the user. Every CLI call below runs
  from the TARGET project root as
  `PYTHONPATH=$FARNSWORTH_HOME python3 -m farnsworth ...`.
- The target project must be its own git repository (the CLI dispatches
  into git worktrees). `git init` a new directory if needed, and set
  `git config commit.gpgsign false` if the host forces signing.

## Phase 0 — Ratify the goal (once per project)

1. If the request is raw (no ratified goal), interview the owner at
   business-objective altitude when they are present; otherwise choose
   conventional defaults and record every choice. Produce in the
   project root:
   - `GOAL.md` — the termination contract: objective, mechanical done
     checks, semantic (attestable) criteria, exits. Self-contained and
     outcome-level. It is read by the LOOP (done probe + attestor),
     never by workers.
   - `farnsworth.json` — workers (confirm the fleet with the user
     before any tokens are spent), reviewer, gate commands, and a
     `goal` block whose `done` checks mirror GOAL.md.
   - `.code-tips.md` — seeded from `$FARNSWORTH_HOME/seed-tips.md`.
2. Keep all source material (specs, PRDs, issues, design notes)
   OUTSIDE the project repository, on the orchestrator's side. See
   Premise isolation below.
3. Commit the seed. Run `farnsworth preflight` (a red gate-at-base on
   a greenfield repo is a documented false positive; anything else is
   fatal). Canary one cheap subagent (create file, run a command,
   commit, report denials) before the first tournament.

## Premise isolation (load-bearing — the loop's defining rule)

Workers must learn the task from the loop, never from their
surroundings:

- **Each task brief is the COMPLETE premise.** Embed, verbatim, every
  requirement the slice needs — signatures, exact messages, data,
  acceptance criteria. A brief must never point at a document outside
  itself; if a worker would need to open the spec, the brief is wrong.
- **Source material stays out of worker reach.** Specs and goal text
  live outside the repo or are loop-read only; worker prompts state:
  the briefing is your entire world — do not read GOAL.md, tasks/, or
  anything under .farnsworth/ beyond your own briefing.
- **Workers are blind**: no worker sees another's briefing, focus,
  output, or progress; the judge never learns which worker, model, or
  focus produced a label.

## The cycle (one iteration per pass)

1. **Probe.** `python3 -m farnsworth done` — exit 1: continue to
   step 2. Exit 0: go to Attestation. Exit 2: report and stop.
2. **Derive ONE task.** Re-read GOAL.md against the merged state and
   the latest `.farnsworth/done-checks.json`. Write the SMALLEST
   coherent slice of the remaining gap that is independently gateable
   and reviewable as `tasks/task-NNN.md` (next free number) — never
   the whole gap, never a pre-authored list. Each iteration does
   *something*, not everything. If the slice needs a narrower gate
   than the goal's, write a per-task config (a copy of farnsworth.json
   with the reduced `gate`) and pass `--config` to run/gate. Commit
   the brief.
3. **Tournament (two rounds, PRD Section 2).**
   - ROUND 1 — EXPLORE: `farnsworth run tasks/task-NNN.md` (exit 3 =
     ready). Read `.farnsworth/<task>/dispatch.json`; spawn ALL coder
     subagents in one parallel batch — role contract from
     `$FARNSWORTH_HOME/.claude/agents/farnsworth-coder.md` (use the
     registered `farnsworth-coder` agent if the host has it, else a
     general agent with that role text prepended), model per ledger
     entry, pinned to its absolute worktree, told to read ONLY its own
     briefing file. When all return: `farnsworth gate <task>` (exit 3
     = candidates ready).
   - JUDGE 1: spawn one reviewer subagent (role from
     `farnsworth-judge.md`, reviewer model), pinned to the constructed
     review environment named by the gate output, briefed with
     `.farnsworth/<task>/review-briefing.md`. Round-1 framing: its
     "adopt" is the CHAMPION — it does not merge yet; distill hard.
   - DISTILL: `farnsworth finalize <task>`; install
     `code-tips.next.md` over `.code-tips.md`; create the `-r2` brief
     as an exact copy of the brief plus a top line noting the informed
     rebuild; commit "Good news, everyone! <lessons>". Round-1 code
     never travels.
   - ROUND 2 — INFORMED REBUILD: repeat run/dispatch/gate on the `-r2`
     brief with fresh workers. Relabel the round-1 champion's diff
     into round 2's candidates (spare label, unattributed, listed in
     the review briefing). JUDGE 2 reviews the whole field blind.
   - VERIFY: spawn an independent verifier to attack the verdict's
     load-bearing claims empirically; a refuted verdict re-runs the
     judge phase.
   - FINALIZE: `farnsworth finalize` + `farnsworth report`; on adopt,
     `farnsworth adopt <winning-task> --clean`. A champion surviving
     verdict-2 is a negative learning result — record it, never hide
     it. Synthesize verdicts surface to the user; escalate verdicts
     stop the task with the change request relayed verbatim.
4. **Journal.** Append the iteration to
   `.farnsworth/orchestrator-log.md` (what merged, verdict, lessons,
   done-check movement); commit "Good news, everyone! <summary>".
5. **Stall check.** No measurable done-check progress for 3
   consecutive iterations exits STALLED.
6. **Budget check.** A user-set iteration or budget cap exhausted
   exits STOPPED.

## Attestation (the semantic half of done)

When `farnsworth done` exits 0 it writes
`.farnsworth/attestation-briefing.md`. Spawn ONE attestor subagent
(role from `farnsworth-attestor.md`, reviewer-tier model) with the
briefing verbatim. `attestation.json` `goal_met: true` → exit DONE;
`false` → its reasoning names the gap; feed that into step 2 and keep
cycling.

## Exits (exactly four, always recorded)

**DONE** (both halves pass) · **ESCALATED** (a change request blocks
all remaining work) · **STOPPED** (budget/cap) · **STALLED** (3
iterations without progress). Record the exit and iteration count in
the orchestrator log; report it with the `farnsworth metrics` table.
