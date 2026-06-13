---
name: farnsworth
description: Ignite the Farnsworth Loop against any target project - ratify a goal contract, confirm the fleet, then launch the farnsworth-loop dynamic workflow, which conducts smallest-slice tournament tasks (blind parallel coders, mechanical gate, anonymized judge, distilled lessons) until the goal is attested done. Use when asked to build, fix, or extend something "using the Farnsworth Loop" in any repository, e.g. /farnsworth ~/my-app "add CSV export".
---

# Farnsworth Loop — ignition

You IGNITE the loop; the **dynamic workflows conduct it**. The
argument names the target project directory and the goal request,
e.g. `/farnsworth ~/proj "build X"`. You never write project code and
you never conduct tournament phases by hand while the workflow
runtime is available.

## How the pieces are registered (installed by this plugin)

- `FARNSWORTH_HOME` is this plugin's root: resolve it as two
  directories above this skill's base directory (override with the
  `FARNSWORTH_HOME` env var if set). It contains the Python trust
  layer (`farnsworth/`), the workflows, the agent roles, and
  `seed-tips.md`.
- The plugin's SessionStart hook syncs into user scope, available in
  every project:
  - `~/.claude/workflows/farnsworth-loop.js` and
    `farnsworth-task.js` — the conductors (dynamic workflows,
    Claude Code ≥ 2.1.154).
  - `~/.claude/agents/farnsworth-coder.md`, `farnsworth-judge.md`,
    `farnsworth-attestor.md`, `farnsworth-improver.md` — the
    tool-scoped roles. Each carries an
    explicit `tools:` allowlist (Bash, Read, Edit/Write, Glob, Grep)
    so the workflow's bust-out to CLI tasks runs only through
    approved tools.
- If any of those files are missing (hook hasn't run yet), copy them
  from `FARNSWORTH_HOME/.claude/{workflows,agents}/` now.

## Phase 0 — Ratify the goal (once per project)

1. The target project must be its own git repository (the CLI
   dispatches into git worktrees). `git init` a new directory if
   needed; set `git config commit.gpgsign false` if the host forces
   signing.
2. If the request is raw (no ratified goal), interview the owner at
   business-objective altitude when they are present; otherwise
   choose conventional defaults and record every choice. Produce in
   the project root, then commit:
   - `GOAL.md` — the termination contract: objective, mechanical done
     checks, semantic (attestable) criteria, exits. Self-contained
     and outcome-level. Read by the LOOP (done probe + attestor),
     never by workers.
   - `farnsworth.json` — workers, reviewer, gate commands, and a
     `goal` block whose `done` checks mirror GOAL.md.
   - `.code-tips.md` — seeded from `FARNSWORTH_HOME/seed-tips.md`.
3. Keep all source material (specs, PRDs, issues, design notes)
   OUTSIDE the project repository, on the orchestrator's side — see
   Premise isolation.

## Premise isolation (load-bearing — the loop's defining rule)

Workers must learn each task from the loop, never from their
surroundings:

- **Each task brief is the COMPLETE premise.** Embed, verbatim, every
  requirement the slice needs — signatures, exact messages, data,
  acceptance criteria. A brief must never point at a document outside
  itself; if a worker would need to open the spec, the brief is wrong.
- **Source material stays out of worker reach.** Specs and goal text
  live outside the repo or are loop-read only.
- **Workers are blind:** no worker sees another's briefing, focus,
  output, or progress; the judge never learns which worker, model, or
  focus produced a label.

## Ignition

1. **Confirm with the user before any tokens are spent** (one
   AskUserQuestion): the fleet (read `farnsworth.json` workers;
   present id / dispatch mode / model / focus per worker), the
   iteration budget, AND how many self-directed improvement rounds to
   run once the goal is met (PRD 2.7; default: the config's
   `goal.improvement_rounds`, else 0). Write agreed changes back to
   the config.
2. **Launch the `farnsworth-loop` dynamic workflow** with args:

   ```js
   { repo: '/abs/path/to/target-project',
     farnsworthPath: '<FARNSWORTH_HOME>',
     maxIterations: <agreed budget>,
     improvementRounds: <agreed rounds>,
     fleet: [ /* only when the user changed the field */ ] }
   ```

   The workflow conducts everything from there: probe → premise
   (smallest gateable slice — one task per iteration, never the whole
   gap) → nested `farnsworth-task` two-round tournament (blind
   explore → distill → informed rebuild → verify) → merge → attest →
   improvement rounds ratchet the goal append-only (mechanizable
   criteria → done checks, semantic → attestation) → go again,
   exiting only DONE / ESCALATED / STOPPED / STALLED.
3. Tell the user the run is live and that they can watch and steer it
   in `/workflows` (pause, stop, per-agent token telemetry).

## Fallback (no workflow runtime only)

If and only if the host runs Claude Code < 2.1.154 (no dynamic
workflows): say so explicitly, then conduct the same spine manually —
each phase via `PYTHONPATH=FARNSWORTH_HOME python3 -m farnsworth
{run,gate,finalize,adopt,done} ...` from the target repo root,
spawning the synced `farnsworth-coder` / `farnsworth-judge` /
`farnsworth-attestor` agents at the exit-3 phase boundaries, honoring
the same blindness and anonymity rules. Never silently substitute
this for the workflow.
