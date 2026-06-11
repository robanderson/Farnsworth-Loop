# Task 001 Review — M1 Skeleton

## Blind sketch (written before reading candidates)

My own approach to the M1 skeleton, written before reading any candidate diff.
This counts as candidate F (anchoring defence).

### Module decomposition

A small `farnsworth/` package, stdlib only:

- `farnsworth/__init__.py` — empty or version string.
- `farnsworth/__main__.py` — entry point so `python3 -m farnsworth` works.
  Just calls `cli.main(sys.argv[1:])` and passes the return code to
  `sys.exit`.
- `farnsworth/cli.py` — argument parsing with `argparse`. A subparser `run`
  taking the positional `task_brief` and optional `--config` (default
  `farnsworth.json`). Dispatches to `run.run_task(...)`. Returns int exit code.
- `farnsworth/config.py` — load and validate the config JSON. Provide
  defaults. A `Config` dataclass / typed dict: `worker_command: list[str]`,
  `gate: list[{name, command}]`.
- `farnsworth/gitutil.py` — thin wrappers over `subprocess` git:
  `is_clean_worktree(cwd)`, `current_commit(cwd)`, `add_worktree(path, branch)`,
  `branch_exists`, path-exists checks. Each raises a clear `FarnsworthError`
  on failure.
- `farnsworth/run.py` — the loop body orchestration (the heart). Functions:
  - `build_briefing(tips_path, brief_path) -> str`
  - `substitute_prompt(argv, prompt) -> list[str]`
  - `run_worker(command, cwd) -> (exit_code, stdout, stderr)`
  - `run_gate(gate_entries, cwd) -> GateResult`
  - `run_task(brief_path, config_path) -> int` — ties it all together,
    writes run.json, returns 0/1.
- `farnsworth/errors.py` — `FarnsworthError(Exception)`.

I'd keep run.json assembly inline in `run_task` building a plain dict that
mirrors the schema exactly, then `json.dump` with indent.

### Key design decisions

1. **Task id derivation:** `Path(brief).stem`. `task-042.md` -> `task-042`.
   Use the stem only, not the full name.
2. **Briefing composition (exact):** read `.code-tips.md` if it exists (else
   empty string), concatenate `tips + "\n\nTASK: " + brief_contents`. If tips
   absent, the brief decides — I'd lean to `"" + "\n\nTASK: " + brief` so the
   `"\n\nTASK: "` separator is always present (the spec says "contents of
   .code-tips.md (if present), then '\n\nTASK: ', then the contents of the task
   brief"). The separator is unconditional.
3. **Prompt substitution:** replace any argv element exactly equal to or
   containing the literal `{prompt}` token via `.replace("{prompt}", prompt)`.
   Spec says "`{prompt}` in any argv element is substituted" — so substring
   replace across every element, not just exact match.
4. **Clean-tree precondition:** `git status --porcelain` empty AND it is a git
   repo (`git rev-parse --is-inside-work-tree`). Abort with clear error + exit
   nonzero (raise FarnsworthError caught in cli -> stderr + return 1).
5. **base_commit:** `git rev-parse HEAD` in the main repo, captured before
   creating the worktree ("at dispatch").
6. **Worktree:** `git worktree add ../<task-id>-w1 -b <task-id>-w1`. Fail
   clearly if branch or path already exists (check first, or detect git's
   nonzero exit and surface message).
7. **Worker run:** `subprocess.run(command, cwd=worktree, capture_output=True,
   text=True)`. Do not require stdout to be JSON — save verbatim. Save stdout
   to `.farnsworth/<task-id>/w1.stdout`, stderr to `w1.stderr` in MAIN repo.
8. **Gate semantics:** run ALL gates even if an earlier fails (no short
   circuit). Each: nonzero exit = fail. Autopsy = `"<name>: exit <code>"` plus
   last line of stderr if present. `gate.passed` = all gates exit 0.
9. **run.json location:** `.farnsworth/<task-id>/run.json` in MAIN repo. Create
   dirs. Field names EXACTLY as schema: task_id, started_at, finished_at,
   base_commit, workers[]{id, branch, worktree, exit_code, stdout_file,
   gate{passed, results[]{name, exit_code, autopsy}}}.
10. **Timestamps:** ISO-8601 UTC. `datetime.now(timezone.utc).isoformat()` (or
    with explicit `Z`). started_at before worker, finished_at after gate.
11. **Do not merge, do not destroy worktree.** Print worktree path + gate
    summary. Exit 0 iff all gates passed else 1.
12. **Never write `.code-tips.md`** — only read it.
13. **stdout_file** in run.json is the relative filename `"w1.stdout"`, matching
    the schema's example (not an absolute path).

### Test strategy

`tests/` with stdlib `unittest`, discoverable via
`python3 -m unittest discover -s tests`. A helper that builds a throwaway git
repo in `tempfile.mkdtemp()`: `git init`, set user.email/name, an initial
commit. Fake worker = a `python3 -c` or `bash -c` one-liner that writes a file
and `git add`/`git commit`s inside the worktree (proves CWD is the worktree).

Test cases:
- end-to-end happy path: worktree dir exists at `../<id>-w1`, run.json written
  with all schema fields, gate passed True, return 0.
- gate-fail path: a gate command exits nonzero -> gate.passed False, autopsy
  string present, process returns 1, all gates still recorded.
- all-gates-run: two gates, first fails — assert second still ran/recorded.
- clean-tree precondition: dirty the tree (write uncommitted file) -> run
  aborts with error, nonzero, no worktree created.
- branch/path-already-exists -> clear failure.
- run.json schema field presence (exact names).
- no `.code-tips.md` written anywhere.
- teardown removes worktrees/branches (use temp dirs so the host repo is
  untouched); `git worktree prune` in teardown.

Tests must construct their own scratch repo and never touch the real repo root.

### Things I'd watch for (likely candidate mistakes)

- Writing run.json into the worktree instead of main repo.
- Short-circuiting the gate on first failure (spec: all gates run).
- Making the `"\n\nTASK: "` separator conditional on tips presence.
- `stdout_file` as absolute path rather than `"w1.stdout"`.
- Using local time instead of UTC for timestamps.
- Exact-match-only `{prompt}` substitution missing the "any argv element"
  substring case.
- Third-party imports sneaking in.
- Tests invoking the real `claude` binary.
- Test leakage: worktrees/branches/.farnsworth left in the repo under test.
- Writing `.code-tips.md`.

---

## Candidate reviews (written after reading diffs + gate-notes)

### The decisive spec point: briefing composition

The brief states the briefing is "contents of `.code-tips.md` (if present), then
`"\n\nTASK: "`, then the contents of the task brief file." The canonical string
is therefore `tips + "\n\nTASK: " + brief`, and when tips are absent the result
is `"\n\nTASK: " + brief` (the `\n\nTASK: ` separator is unconditional — it is a
fixed literal, not glue that only appears between two present operands).

- **A, B:** faithful. Both unconditionally produce `tips + "\n\nTASK: " + brief`.
- **C, D, E:** all special-case the no-tips path to `"TASK: " + brief` (no leading
  `\n\n`). This is a literal deviation from the spec string. It is minor in
  practice (the real worker won't care about two leading newlines) but it is an
  exact-string requirement the brief spelled out, and three of five candidates
  got it wrong the same way — a recurring mistake worth locking down.
- **E additionally** `.rstrip()`s both the tips and the brief before composing,
  mutating the brief contents. The spec says "the contents of the task brief
  file" — verbatim. Another (separate) faithfulness slip.

### Candidate A

GOOD:
- Cleanest decomposition: `cli / config / gitutil / loop`, each with a typed
  error class and a single responsibility. `loop.run()` returns the run-log dict
  and is directly unit-testable with a `cwd=` injection point.
- Briefing composition exactly correct (`tips + "\n\nTASK: " + brief`,
  unconditional separator).
- `run()` derives the repo root via `git rev-parse --show-toplevel` and bases the
  worktree on `dirname(repo_root)`, so it is correct even when invoked from a
  subdirectory of the repo (B also does this; D and E use CWD).
- Explicit pre-checks for branch-exists and worktree-path-exists with clear
  `LoopError` messages, in addition to letting git fail.
- UTC timestamps via `datetime.now(timezone.utc)` with an explicit `Z` suffix and
  microseconds stripped — tidy and unambiguous.
- Config is validated (`Config.from_dict`) with helpful errors; falls back to a
  built-in default only when the path is absent.
- Tests are the strongest of the field: explicit briefing-ordering assertion
  (`SOME_TIP` before `UNIQUE_TASK_BODY` and `"\n\nTASK: "` present), all-gates-run
  with a passing second gate after a failing first, autopsy contains stderr tail,
  on-disk run.json equals the returned dict, clean-tree + non-git + existing-branch
  preconditions, and a no-`.code-tips.md`-write assertion. Scratch repo nested in
  a TemporaryDirectory; worktrees tracked and force-removed in teardown — zero
  leakage. Stem test covers `.markdown` and bare-name cases.
- Hygiene clean: `.gitignore` added, no `.pyc` committed (gate-notes).

BAD:
- `cli.main` recomputes the repo root via `repo_toplevel(os.getcwd())` purely to
  print an absolute worktree path; harmless but slightly redundant with what
  `loop.run` already knows.
- Abort/precondition failures surface as exit code 2 (from `cli.main`), not 1.
  The brief only specifies 0 (gates pass) / 1 (gates fail) for the *normal* path
  and "clear error" for aborts; 2 for usage/precondition errors is a defensible
  convention, not a violation.
- No standalone subprocess test of `python3 -m farnsworth` end-to-end (tests call
  `loop.run` in-process). Acceptable; module entrypoint is trivial.

Acceptance-criteria checklist:
- [x] `python3 -m farnsworth run …` end-to-end with fake worker — yes (in-process).
- [x] `unittest discover -s tests` passes — gate confirms.
- [x] `compileall farnsworth` — yes.
- [x] run.json schema field names exact — yes; `stdout_file: "w1.stdout"`,
      `worktree: "../<id>-w1"`, nested `gate.results[].{name,exit_code,autopsy}`.
- [x] No third-party imports — stdlib only.
- [x] Never writes `.code-tips.md` — only reads it; test asserts it.
- [x] All gates run even if earlier fails — yes; tested.
- [x] Worktree not destroyed, not merged — correct.
- [x] No side effects in repo root — temp dirs + teardown.

### Candidate B

GOOD:
- Briefing composition correct (`parts.append("\n\nTASK: " + brief)`; tips
  prepended only if present — net result is the canonical string in both cases).
- Repo-root-based worktree placement (`dirname(repo_root)`), correct from
  subdirectories.
- Clean `git_utils` module; `run_worker` streams stdout/stderr straight to the
  artifact files (no buffering surprises). run.json fields exact, `worktree` via
  `os.path.relpath(worktree, repo_root)` yields `../<id>-w1`.
- Good test coverage: schema fields, run.json-in-main-repo (explicitly asserts it
  is NOT in the worktree), all-gates-run, gate.passed-false-when-any-fails,
  stdout/stderr files created, dirty + staged precondition both abort,
  `{prompt}` substitution unit test, prompt-includes-tips and no-tips cases.
  Brief and config written *outside* the repo (in base_dir) so the scratch tree
  stays clean. Hygiene clean (.gitignore, no pyc).

BAD:
- `__main__.py`'s `main()` calls `parser.parse_args()` with no argument, reading
  `sys.argv` directly, so `main` cannot be driven with an injected argv in tests
  (A and E both accept `argv`). Minor testability gap; tests call `run_task`
  directly so it doesn't bite here.
- Precondition/worktree-creation failures return exit code 2 (like A). Same
  defensible-convention note.
- Does NOT pre-check branch/path existence; relies solely on git's nonzero exit
  surfaced as a RuntimeError. The brief says "fail clearly if branch or path
  already exists" — git's stderr is included in the message, so this is
  acceptable, but it is less explicit than A/D/E and there is no test for it.
- `imports sys` unused in `__main__.py` path is fine; `typing` import in
  `git_utils` is light noise. Cosmetic.

Acceptance-criteria checklist: all met (same as A). Schema exact; no third-party;
no `.code-tips.md` write; all-gates-run tested; no leakage.

### Candidate C

GOOD:
- Functionally close: worktree from `repo_path.parent`, run.json schema fields
  exact, all gates run, stdout/stderr saved, autopsy includes stderr tail.
- Decent test split across `test_cli` and `test_runner`; covers gate pass/fail,
  schema, multiple gates, stdout capture, autopsy, missing brief/config, invalid
  JSON, dirty tree, and a code-tips-injection test.

BAD (serious):
- **Commits `.code-tips.md` into the repo** (a 9-line skeleton). The brief and
  PRD are explicit that workers are read-only consumers of `.code-tips.md`;
  authoring/committing it is the single most-guarded invariant in the whole
  project. Even as a "scaffold" this is exactly the boundary the loop exists to
  protect. Disqualifying on its own.
- **Commits the task brief** (`.farnsworth/task-001/brief.md`) into the
  deliverable — pollutes the repo with loop-control state the worker should not
  be touching.
- **Commits `__pycache__/*.pyc`** (4 + 2 files; gate-notes flags it). Build
  artifacts in the tree.
- Briefing composition deviation (`"TASK: "` when no tips; see decisive point).
- Non-ASCII glyphs (`✓`, `✗`) in CLI output — gratuitous and can break on
  non-UTF terminals.
- `subprocess.run(timeout=None)` and broad `except Exception` mapping to
  `exit_code = -1` is over-built for M1 and silently swallows real errors.
- `run_task` lives in `cli.py` and does git work there, while `runner.py` also
  does git work — responsibilities smeared across both.

Acceptance-criteria checklist:
- [x] runs end-to-end; [x] tests pass; [~] compileall (committed pyc is separate);
- [x] schema fields present; [x] no third-party;
- [ ] **"does not write `.code-tips.md` anywhere"** — VIOLATED: it commits one.
- [~] hygiene — pyc + brief + tips committed.

### Candidate D

GOOD:
- Class-based `Runner` is readable; explicit branch-exists and worktree-exists
  pre-checks with clear `RuntimeError`s. Worktree/branch derivation and run.json
  schema are correct. Good precondition + branch-exists + multiple-gates tests.

BAD (serious):
- **Commits `.code-tips.md`** — same disqualifying invariant breach as C.
- **Commits `__pycache__/*.pyc`** (gate-notes flags it).
- **Worktree path from `Path.cwd().parent`, not the git repo root.** If invoked
  from any subdirectory of the repo, the worktree lands in the wrong place and
  `_verify_git_clean` checks the wrong tree. A and B handle this; D does not.
- `datetime.utcnow().isoformat() + "Z"` — `utcnow()` is deprecated from Python
  3.12 and returns a naive datetime; appending `"Z"` to a naive ISO string is a
  bit of a hack. Also `started_at` and `finished_at` are set to the *same* `now`,
  so the log cannot show elapsed time.
- Briefing composition deviation (`"TASK: "` when no tips), and its own test
  (`test_no_tips_file`) *asserts the wrong behavior* (`startswith("TASK:")`),
  baking the deviation into the suite.
- `gate` config also carries the project's own real tests + compileall as gates
  in `farnsworth.json` — fine, but the committed pyc undercuts the compileall
  intent.

Acceptance-criteria checklist:
- [x] runs; [x] tests pass; [x] schema; [x] no third-party;
- [ ] **does not write `.code-tips.md`** — VIOLATED (committed).
- [ ] hygiene (pyc committed); subdirectory-invocation correctness broken.

### Candidate E

GOOD:
- Functional core is sound: repo state validated, branch/path pre-checks, all
  gates run, run.json schema exact, `cli.main(argv=None)` accepts injected argv
  (good testability). Clean `_autopsy` helper. Solid test suite: worktree
  created, gate pass/fail, schema with SHA regex, dirty-tree rejected,
  stdout/stderr saved, all-gates-run, `{prompt}` substitution with tips, and a
  no-`.code-tips.md`-write assertion. Hygiene clean (.gitignore, no pyc).

BAD:
- **Worktree path from `os.getcwd()` as repo root**, not `git rev-parse
  --show-toplevel`. Works when invoked from the repo top (as the tests do) but
  breaks from a subdirectory — same latent bug as D, less severe than D only
  because E at least verifies it *is* a git repo.
- Briefing composition deviation (`"TASK: "` when no tips) AND it `.rstrip()`s
  both tips and brief, mutating brief content — two separate faithfulness slips.
- **`.gitignore` ignores `.farnsworth/*/run.json`, `w1.stdout`, `w1.stderr`.**
  This contradicts the PRD principle that loop state is file-based and
  inspectable/committable (Section 4.3: "all loop state ... live in the repo");
  for M1 these are generated artifacts so it is arguable, but it is a design
  choice that fights the project's audit story and no other candidate made it.
- Uses `sys.exit("message")` for control flow inside `run_task`. This raises
  `SystemExit` with the message as `.code` (a string), so the process exits 1 and
  prints the message — works, but mixing library-level control flow with
  `sys.exit` is poorer separation than A/B's exception-then-CLI pattern. E's own
  dirty-tree test leans on `str(ctx.exception.code)` containing "clean", which is
  brittle (it asserts against the exit *message*, not an exit code).

Acceptance-criteria checklist:
- [x] runs; [x] tests pass; [x] schema exact; [x] no third-party;
- [x] never writes `.code-tips.md` (tested);
- [~] all-gates-run yes; [~] inspectability: gitignores run artifacts;
- [~] subdirectory-invocation correctness latent-broken.

### Cross-field summary

| Criterion | A | B | C | D | E |
|---|---|---|---|---|---|
| Briefing composition exact | ✔ | ✔ | ✘ (no-tips) | ✘ (no-tips) | ✘ (no-tips + rstrip) |
| Worktree rooted at git toplevel | ✔ | ✔ | ✔ | ✘ (cwd) | ✘ (cwd) |
| run.json schema exact | ✔ | ✔ | ✔ | ✔ | ✔ |
| All gates run | ✔ | ✔ | ✔ | ✔ | ✔ |
| Never writes/commits `.code-tips.md` | ✔ | ✔ | ✘ commits | ✘ commits | ✔ |
| Hygiene (no pyc / no stray commits) | ✔ | ✔ | ✘ | ✘ | ✔ |
| Inspectable artifacts (no gitignore of run.json) | ✔ | ✔ | ✔ | ✔ | ✘ |
| Test rigor | high | high | med | med | high |

## Verdict

**ADOPT A.**

Reasoning. A is correct and complete against every hard requirement and every
acceptance criterion, with no disqualifying flaw:

- Briefing composition is exactly the spec string in both the tips-present and
  tips-absent cases — a point three of the five candidates got wrong.
- It roots the worktree at the true git toplevel, so it is correct regardless of
  the invocation directory (D and E are latently broken here).
- It never writes or commits `.code-tips.md` (C and D both commit it — the single
  most-protected invariant in the PRD), commits no `.pyc`, and adds a `.gitignore`.
- run.json matches the schema field-for-field; all gates run; the worktree is
  preserved and not merged.
- Its test suite is the most rigorous of the field: it is the only one that
  asserts the *ordering* of the briefing (tips before task) and the presence of
  the literal `"\n\nTASK: "` separator, alongside all-gates-run, schema-equals-
  on-disk, and every precondition, with zero repo-root leakage.

B is the runner-up and is genuinely adequate — if A did not exist this would be
"adopt B". B's only gaps versus A are stylistic (parse_args without argv; no
explicit branch-exists pre-check/test). Because exactly one candidate is correct
AND complete AND the strongest, this is an adopt, not a synthesize. My blind
sketch matched A's decomposition closely (cli/config/git/loop, in-process
testable `run()`), which raises rather than lowers my confidence: A is the
implementation I would have written, executed more thoroughly. No splicing is
needed or permitted.

This is not an escalate: the brief is unambiguous and internally consistent. The
one wrinkle — whether `"\n\nTASK: "` is unconditional — is resolvable directly
from the brief's own wording (it lists the separator as a fixed third element),
and A/B read it correctly, so the spec is not defective.
