# Task 001 — M1 Skeleton: dispatch + worktree + gate

## Goal

Implement Milestone M1 of the Farnsworth Loop PRD (see README.md): a CLI that
runs ONE task with ONE worker — create a git worktree, run the worker command
in it, run the mechanical gate, and write a JSON run log. No review phase, no
tips lifecycle, no parallelism yet. Prove the plumbing.

## Hard requirements

1. **Language:** Python 3.11+, standard library only. No third-party deps.
2. **Layout:** a `farnsworth/` package, runnable as `python3 -m farnsworth`.
3. **CLI:** `python3 -m farnsworth run <task-brief.md>`
   - `<task-brief.md>` is any markdown file; its path stem (e.g. `task-042`
     from `task-042.md`) is the task id.
   - Optional `--config <path>` (default: `farnsworth.json` in repo root).
4. **Config file** (`farnsworth.json`), JSON, with at least:
   ```json
   {
     "worker": {
       "command": ["claude", "-p", "{prompt}", "--bare", "--model",
                    "claude-haiku-4-5", "--permission-mode", "acceptEdits",
                    "--output-format", "json"]
     },
     "gate": [
       {"name": "tests", "command": ["python3", "-m", "unittest", "discover"]}
     ]
   }
   ```
   - `{prompt}` in any argv element is substituted with the worker briefing.
   - The worker briefing is: contents of `.code-tips.md` (if present), then
     `"\n\nTASK: "`, then the contents of the task brief file.
   - The worker command is configurable precisely so tests can substitute a
     fake worker — tests MUST NOT invoke the real `claude` binary.
5. **Run behavior** (the loop body, single worker):
   a. Verify the CWD is a git repo with a clean working tree; abort with a
      clear error otherwise.
   b. Create worktree `../<task-id>-w1` on new branch `<task-id>-w1`
      (fail clearly if branch or path already exists).
   c. Run the worker command with CWD set to the worktree. Capture stdout,
      stderr, exit code. Worker stdout is saved verbatim (it may be the
      `claude --output-format json` payload; do not require it to parse).
   d. Run each gate command, in order, in the worktree. A gate entry fails on
      nonzero exit. Record per-gate: name, exit code, and a one-line autopsy
      (e.g. `"tests: exit 1"` plus last line of stderr if any). All gates run
      even if an earlier one fails.
   e. Write the run log to `.farnsworth/<task-id>/run.json` in the MAIN repo
      (not the worktree). Schema below.
   f. Do NOT merge and do NOT destroy the worktree; print its path and the
      gate summary, exit 0 if all gates passed, exit 1 otherwise.
6. **Run log schema** (`run.json`):
   ```json
   {
     "task_id": "task-042",
     "started_at": "ISO-8601 UTC",
     "finished_at": "ISO-8601 UTC",
     "base_commit": "sha of main repo HEAD at dispatch",
     "workers": [
       {
         "id": "w1",
         "branch": "task-042-w1",
         "worktree": "../task-042-w1",
         "exit_code": 0,
         "stdout_file": "w1.stdout",
         "gate": {"passed": true,
                   "results": [{"name": "tests", "exit_code": 0,
                                 "autopsy": "tests: exit 0"}]}
       }
     ]
   }
   ```
   Worker stdout/stderr go to `.farnsworth/<task-id>/w1.stdout` / `w1.stderr`.
7. **Tests:** stdlib `unittest`, discoverable via
   `python3 -m unittest discover -s tests -v`. Tests must build a throwaway
   git repo in a temp dir (subprocess git is fine), use a fake worker command
   (e.g. a `bash -c` or `python3 -c` one-liner that writes a file and
   commits), and assert: worktree created, gate pass and gate fail paths,
   run.json schema fields present, clean-tree precondition enforced.
8. **No side effects in this repo's root:** running the test suite must not
   leave worktrees, branches, or `.farnsworth/` artifacts behind in the repo
   under test (use temp dirs; clean up worktrees in test teardown).

## Acceptance criteria

- [ ] `python3 -m farnsworth run …` works end-to-end with a fake worker in a
      scratch repo.
- [ ] `python3 -m unittest discover -s tests` passes.
- [ ] `python3 -m compileall farnsworth` succeeds.
- [ ] run.json matches the schema above (field names exactly).
- [ ] No third-party imports anywhere.
- [ ] Code does not write `.code-tips.md` anywhere (workers are read-only
      consumers of it).

## Out of scope (do not build)

Parallel dispatch, review, verdicts, tips writing, divergence measurement,
metrics, consolidation, daemons, UI. Keep it small; this is the skeleton.
