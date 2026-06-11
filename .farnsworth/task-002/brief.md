# Task 002 — M2 Tournament: parallel blind dispatch + anonymized review + verdict

## Goal

Extend the existing M1 skeleton (the `farnsworth/` package on this branch) to
Milestone M2 of the PRD (README.md): `python3 -m farnsworth run <task-brief.md>`
now dispatches N workers in parallel blind worktrees, gates each one, builds an
anonymized review briefing, runs a configurable reviewer, and records a
three-outcome verdict. Merge stays MANUAL (the human merges; the tool only
reports). Build on the current code; do not rewrite it from scratch.

## Hard requirements

1. **Stdlib only, Python 3.11+**, same package layout. Honor every entry in
   `.code-tips.md` (briefing contract, run.json contract, toplevel anchoring,
   timestamps, hygiene, style, test rigor).
2. **Config schema** (`farnsworth.json`) becomes:
   ```json
   {
     "workers": [
       {"id": "w1", "command": ["...", "{prompt}", "..."]},
       {"id": "w2", "command": ["..."]}
     ],
     "reviewer": {"command": ["...", "{prompt}", "..."]},
     "gate": [{"name": "tests", "command": ["..."]}]
   }
   ```
   - Worker ids must be unique, nonempty, filesystem-safe; validate.
   - Back-compat: a legacy `"worker": {...}` entry is treated as
     `"workers": [{"id": "w1", ...}]`.
   - `reviewer` is required only when more than zero candidates pass the gate;
     missing reviewer with passing candidates is a clear config error.
3. **Dispatch (blind, parallel):** one worktree per worker at
   `../<task-id>-<worker-id>` on branch `<task-id>-<worker-id>`, all created
   from the same base commit. Worker briefing per the existing M1 contract
   (tips + `"\n\nTASK: "` + brief). Run all worker commands CONCURRENTLY
   (`concurrent.futures` or `subprocess.Popen` fan-out; your choice), each
   with CWD set to its own worktree. Capture per-worker stdout/stderr to
   `.farnsworth/<task-id>/<worker-id>.stdout` / `.stderr`. A worker command
   crashing (nonzero exit) is recorded, not fatal to the run.
4. **Gate:** unchanged semantics (all gates run, in order, per worktree;
   `passed` = AND of exit codes). Gate every worker, including ones whose
   command exited nonzero. One-line autopsy per gate result.
5. **Anonymization:** workers whose gate passed become candidates. Assign
   labels `A`, `B`, `C`, ... in RANDOM order (`random.shuffle`). For each
   candidate write `git diff <base>..<worktree-HEAD>` to
   `.farnsworth/<task-id>/candidates/<LABEL>.diff`. The label->worker mapping
   must NOT appear in any file the reviewer reads and must NOT be passed to
   the reviewer; it is written into run.json only after the reviewer exits.
6. **Review briefing** (substituted into the reviewer command's `{prompt}`):
   contains, in order: the task brief verbatim; for each candidate, the label
   and the relative path to its diff file; one ANONYMIZED autopsy line per
   gate-failed worker (e.g. `"a failed candidate: tests: exit 1"` — no worker
   ids); and the literal instruction that the reviewer must write
   `.farnsworth/<task-id>/verdict.json` with schema:
   ```json
   {"outcome": "adopt" | "synthesize" | "escalate",
    "candidate": "A" | null,
    "reasoning": "..."}
   ```
   Reviewer command runs with CWD = repo toplevel. `candidate` must be a
   valid label when outcome is `adopt`, else null; validate after the
   reviewer exits and fail clearly on missing/invalid verdict.json.
7. **No merge, no tips writing:** the tool never merges branches and never
   writes `.code-tips.md`. After a valid verdict it prints an ASCII summary
   (per-worker gate line, candidate count, verdict) and keeps all worktrees
   for manual inspection/merge.
8. **run.json:** same field contract as M1 for each entry in `workers[]`
   (id, branch, worktree, exit_code, stdout_file, gate{...}), plus per-worker
   `"candidate_label": "A" | null`, plus top-level:
   ```json
   "review": {"exit_code": 0, "verdict": {"outcome": "...", "candidate": "...",
               "reasoning": "..."}}
   ```
   Top-level `task_id, started_at, finished_at, base_commit` unchanged.
   Exit code of the CLI: 0 when a valid verdict was produced (any outcome),
   1 on gate-everything-failed (no candidates -> no review; still write
   run.json with `"review": null`), 2 on infrastructure/config errors.
9. **Tests** (extend the existing suite; keep it green): fake workers are
   `python3 -c` one-liners (NEVER the real `claude`). Cover at least:
   - two passing + one gate-failing worker: correct candidate set, labels are
     a permutation, diffs exist, autopsy of the failure is anonymized;
   - the briefing passed to a fake reviewer contains labels and brief text
     but NOT worker ids and NOT the mapping;
   - fake reviewer writes adopt/synthesize/escalate verdicts: each parsed and
     recorded; invalid verdict.json -> exit 2; adopt with bad label -> exit 2;
   - all workers fail gate -> exit 1, `review` null in run.json;
   - legacy single-`worker` config still works end to end;
   - run.json on disk equals the returned dict; no worktree/branch leakage
     (teardown removes everything; scratch repos in temp dirs).
10. **Concurrency note:** workers run in sibling worktrees of one repo;
    `git worktree add` calls must be serialized (do them before the parallel
    fan-out). Only the worker COMMANDS run concurrently.

## Acceptance criteria

- [ ] `python3 -m unittest discover -s tests` green; `python3 -m compileall
      farnsworth` green.
- [ ] Blindness: nothing from one worker's worktree is readable in another's
      briefing or environment.
- [ ] Anonymity: reviewer inputs contain no worker ids, no model names, no
      mapping; labels randomized.
- [ ] Verdict is exactly one of adopt/synthesize/escalate, validated, in
      run.json.
- [ ] Tool never merges and never writes `.code-tips.md`.
- [ ] run.json M1 field names preserved; new fields exactly as specified.
- [ ] No third-party imports; no committed bytecode; ASCII-only CLI output.

## Out of scope

Automatic merge, tips distillation/writing, divergence measurement, two-round
mode, triage, metrics dashboards, daemons, UI.
