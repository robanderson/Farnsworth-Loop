# Task 002 Review — M2 Tournament

## Blind sketch (written before reading candidates)

My own M2 design, written before reading any candidate diff. This counts as
candidate F (anchoring defence).

### What changes from M1

M1 ran one worker, gated it, wrote run.json, exit 0/1 on gate. M2 turns this
into a tournament: N workers in parallel blind worktrees, gate each, anonymize
the passers into labeled candidates, build a review briefing, run a configurable
reviewer, validate the verdict, write the expanded run.json, exit 0/1/2. Merge
and tips writing stay out of scope. I want to EXTEND the M1 modules, not rewrite
them — keep `cli / config / gitutil / loop`, keep `loop.run()` returning the
run-log dict and accepting an injectable `cwd`.

### Config schema (config.py)

`Config` grows from a single `worker_command` to:
- `workers: list[{id, command}]` — ids unique, nonempty, filesystem-safe.
- `reviewer: {command}` — optional at parse time; required only if >0 candidates
  pass the gate (validated later in the loop, raised as a clear config error).
- `gate: list[{name, command}]` — unchanged.

Validation rules I'll enforce in `Config.from_dict`:
- Back-compat: if `data` has a legacy `"worker": {...}` and no `"workers"`,
  rewrite it to `workers = [{"id": "w1", "command": worker["command"]}]`. If both
  present, that's a config error (ambiguous) — or prefer `workers` and ignore;
  I'll make presence-of-both an error to be strict, but spec only says legacy
  `worker` maps to a single w1, so at minimum handle the legacy-only case.
- `workers` must be a non-empty list; each entry a dict with `id` (str, nonempty)
  and `command` (non-empty list of str).
- Ids unique. Filesystem-safe = a conservative whitelist (letters, digits, `-`,
  `_`), reject path separators, `.`/`..`, whitespace, empty. This matters because
  the id becomes a branch name and a worktree dir name and a stdout filename.
- `reviewer`: if present, must be a dict with a non-empty str-list `command`.
  Store as `self.reviewer_command` or None. Defer the "required when candidates
  exist" check to the loop, where candidate count is known.
- Keep `DEFAULT_CONFIG` working: I'd update it to the new `workers` list form (or
  leave the legacy `worker` key and let back-compat handle it; cleaner to update
  it). It needs a `reviewer` entry too so the default is a real M2 config.

I must NOT break the M1 config tests; `from_dict({"worker": {...}})` must still
yield a usable single-worker config.

### Dispatch (loop.py) — blind, parallel

1. Precondition checks unchanged: is-git-repo, clean tree, brief exists, derive
   repo_root from `git rev-parse --show-toplevel` (per task-001 tip; do NOT use
   cwd as root — that bit two M1 candidates).
2. `base_commit = head_commit(repo_root)` captured once, before any worktree.
   All worktrees branch from this same base commit.
3. SERIALIZE the `git worktree add` calls — the concurrency note in the brief is
   explicit and correct: `git worktree add` mutates the shared repo
   (.git/worktrees, refs), so racing them corrupts state. Do all the adds in a
   simple loop first. Pre-check branch-exists and worktree-path-exists for each
   (task-001 tip), failing clearly before touching git.
4. Build the briefing ONCE (it's identical for all workers: `tips + "\n\nTASK: "
   + brief`, verbatim, separator unconditional — task-001 invariants). Same
   prompt substituted into each worker's command.
5. Run the worker COMMANDS concurrently — `concurrent.futures.ThreadPoolExecutor`
   with `subprocess.run(cwd=worktree_abs, capture_output=True, text=True)`. Each
   future returns (exit_code, stdout, stderr). Threads are fine here; the work is
   subprocess I/O. CWD per worker = its own worktree (blindness: a worker can
   only see its own tree; nothing from a sibling tree is in its CWD or env).
6. A nonzero worker exit is RECORDED, not fatal. Capture stdout/stderr to
   `.farnsworth/<task-id>/<worker-id>.stdout` / `.stderr`.

### Gate

Unchanged `_run_gate` semantics: all gates run in order per worktree, `passed`
= AND of exit codes. Gate EVERY worker, including ones whose worker command
exited nonzero (the brief is explicit — gate them anyway; a crashed worker may
still have left a committable/uncommittable tree, and we record the gate result
either way). One-line autopsy per gate result, same format as M1.

### Anonymization — the crux

- Candidates = workers whose `gate.passed` is True.
- Generate labels A, B, C, ... for the candidate count. Pair labels to candidate
  workers in RANDOM order via `random.shuffle` (shuffle the worker list, then zip
  with A.., or shuffle the labels). The mapping label->worker is built here but
  MUST NOT be written anywhere the reviewer can read it, and MUST NOT be passed
  into the reviewer command. It goes into run.json (as each worker's
  `candidate_label`) only AFTER the reviewer process exits.
- For each candidate write `git diff <base>..<worktree-HEAD>` to
  `.farnsworth/<task-id>/candidates/<LABEL>.diff`. HEAD of each worktree = that
  worker's branch tip. Use `git diff base..branch` (or `base..HEAD` run in the
  worktree). The diff file is named by LABEL only — no worker id in the filename
  or contents (a raw `git diff` body contains file paths/content, not worker ids,
  so that's safe as long as the worker didn't write its own id into a file; not
  my concern to police).

### Review briefing (loop.py)

Built as a string substituted into the reviewer command's `{prompt}`. Contents
in this exact order:
1. The task brief verbatim.
2. For each candidate (in label order A, B, ...): the label and the RELATIVE path
   to its diff file (relative to repo toplevel, e.g.
   `.farnsworth/<task-id>/candidates/A.diff`).
3. One ANONYMIZED autopsy line per gate-FAILED worker, e.g.
   `"a failed candidate: tests: exit 1"` — NO worker ids, NO labels (failed
   workers don't get labels), NO model names.
4. The literal instruction telling the reviewer to write
   `.farnsworth/<task-id>/verdict.json` with the schema
   `{"outcome": adopt|synthesize|escalate, "candidate": "A"|null, "reasoning": ...}`.

Reviewer runs with CWD = repo toplevel (so the relative diff paths resolve).
Reviewer command crashing is an infra error path, but the brief's run.json
`review.exit_code` field implies we record the reviewer's exit code; I'd capture
it. Capture reviewer stdout/stderr too (reviewer.stdout/.stderr) for audit.

### Verdict validation (loop.py)

After the reviewer exits, read `.farnsworth/<task-id>/verdict.json`:
- Missing file -> infra/contract error -> exit 2.
- Not valid JSON -> exit 2.
- `outcome` not in {adopt, synthesize, escalate} -> exit 2.
- If `outcome == "adopt"`: `candidate` must be a valid existing label -> else
  exit 2.
- If `outcome != "adopt"`: `candidate` must be null (I'd accept/normalize to
  null; the schema shows null for non-adopt). I'll validate it's null or coerce.
- `reasoning` present (string). On any failure, raise a typed error caught in cli
  -> exit 2.

### run.json contract

Preserve M1 top-level: `task_id, started_at, finished_at, base_commit`. `workers`
is now a list of all workers, each with M1 fields (`id, branch, worktree,
exit_code, stdout_file, gate{passed, results[]}`) PLUS `candidate_label: "A"|null`
(null for gate-failed / non-candidate workers). New top-level `review`:
`{"exit_code": int, "verdict": {outcome, candidate, reasoning}}` — or `null` when
no candidates passed (no review ran). On-disk run.json must equal the returned
dict (task-001 tip + M1 test).

### Exit codes (cli.py)

- 0: a valid verdict was produced (ANY outcome — adopt/synthesize/escalate all
  exit 0; the verdict being escalate is still a successful run of the tool).
- 1: gate-everything-failed — zero candidates, so no review; still write run.json
  with `review: null`. Exit 1.
- 2: infrastructure/config errors — bad config, missing/invalid verdict.json,
  reviewer missing when candidates exist, git failures, etc.

The cli summary (ASCII only): per-worker gate line (id + PASS/FAIL + label if
any), candidate count, and the verdict outcome/candidate. Keep `cli.main(argv)`
injectable.

### Tests (extend tests/test_loop.py, keep green)

Fake workers and fake reviewer are `python3 -c` one-liners — NEVER real claude.
A fake reviewer reads its `{prompt}` arg (or argv) and writes verdict.json. I'll
add helpers to write a multi-worker config and a fake-reviewer config. Required
scenarios (from the brief):
- Two passing + one gate-failing worker: candidate set is exactly the two
  passers, labels are a permutation of {A,B}, both diff files exist and are
  non-empty, the failing worker's autopsy appears anonymized in the briefing
  (no worker id).
- The briefing handed to the fake reviewer contains the labels and the brief text
  but NOT any worker id and NOT the mapping. (Fake reviewer echoes its prompt to
  a file; assert.)
- Fake reviewer writes adopt / synthesize / escalate — each parsed and recorded
  in run.json; exit 0.
- Invalid verdict.json (garbage / missing outcome) -> exit 2.
- Adopt with a bad/nonexistent label -> exit 2.
- All workers fail gate -> exit 1, `review` is null in run.json, no reviewer
  invoked.
- Legacy single-`worker` config works end to end (back-compat).
- run.json on disk equals the returned dict.
- No worktree/branch leakage: teardown removes ALL worktrees (now multiple per
  task); scratch repos in temp dirs. I'll need to track every worker's worktree.

### Things I'll watch for (likely candidate mistakes)

- The mapping leaking to the reviewer: writing label->worker into a file in
  `candidates/`, into the briefing, into an env var, or naming diff files / dirs
  by worker id. This is the single most-guarded M2 invariant.
- Racing `git worktree add` (must be serialized) — corrupts the repo.
- Non-deterministic / unseeded shuffle making tests flaky (tests must assert a
  permutation, not a fixed order; or the impl exposes a seed injection).
- Reviewer required-when-candidates-exist check missed (crash instead of clean
  exit 2 config error).
- Exit code confusion: escalate/synthesize wrongly mapped to nonzero; or
  gate-all-fail mapped to 2 instead of 1; or valid-verdict mapped per-outcome.
- `review: null` vs an empty dict on the no-candidates path.
- Worker `exit_code` nonzero treated as fatal (should be recorded, still gated).
- Briefing for the reviewer accidentally including worker ids in the diff path
  (paths must be label-named) or in the autopsy lines.
- Back-compat broken: legacy `worker` config rejected, or M1 config tests broken.
- `candidate_label` absent on gate-failed workers (should be null, present).
- Mapping written into run.json BEFORE reviewer exits (ordering — must be after).
- Tips/`.code-tips.md` written by the tool (still forbidden); tool merging (still
  forbidden).
- Test leakage from the now-multiple worktrees per run.
- Non-ASCII glyphs in CLI output; third-party imports; committed pyc.

---

## Candidate reviews (written after reading A-E + gate-notes)

All five passed the mechanical gate (unittest + compileall). gate-notes.json
records "gate pass; clean file set" for all. Reviewed blind against the brief's
hard requirements (1-10) and acceptance criteria. Scored on spec faithfulness,
code quality on the M1 base, test rigor, and .code-tips.md adherence.

### Candidate A

GOOD:
- Correct overall M2 shape: serialized worktree creation before a
  ThreadPoolExecutor fan-out; gates every worker incl. nonzero-exit ones;
  random labels via `random.shuffle`; reviewer CWD = repo toplevel.
- Anonymized autopsy is BUILT CORRECTLY (iterates gate-failed workers, emits
  `a failed candidate: <name>: exit N`, no worker ids).
- Verdict validation is clean and typed (LoopError -> cli exit 2): outcome enum,
  adopt-needs-valid-label, non-adopt-needs-null, reasoning is str. Back-compat
  `worker` -> `[{id:w1}]`; unique + filesystem-safe id regex `[A-Za-z0-9_.-]`.
- `worker_command` back-compat property preserved for the old config test.
- run.json: M1 fields preserved + per-worker `candidate_label` + top-level
  `review`. Mapping written AFTER reviewer exits.

BAD:
- Writes a separate `candidate-mapping.json` into the artifact dir. It is
  written after the reviewer exits and the reviewer never reads it, so it does
  NOT leak; but it is an unrequested audit file sharing the exact name of the
  task-001 attribution artifact. Tolerable, not required.
- The headline test `test_two_passing_one_failing_worker` is a mess: dead code,
  self-contradicting inline comments ("Actually... Let's make w3 gate fail
  instead"), and it ultimately abandons the 3-worker scenario to test only two
  passing workers. The brief's REQUIRED "two passing + one gate-failing"
  scenario is therefore not actually exercised as written.
- `_assign_labels` raises bare LoopError past 26 candidates (fine, but no AA..).

Checklist vs acceptance criteria:
- [x] stdlib only, 3.11+, same layout   [x] config schema + unique/safe ids
- [x] back-compat legacy `worker`       [x] blind parallel dispatch, serialized adds
- [x] gate-all incl. nonzero exit       [x] random labels, diffs per LABEL
- [x] mapping not in reviewer inputs     [x] anonymized autopsy in briefing
- [x] verdict schema + validation        [x] exit 0/1/2
- [x] run.json contract (+stray mapping file)  [~] tests: headline scenario broken
- [x] no merge / no tips writing

### Candidate B

GOOD:
- Reasonable structure: serialized adds, parallel fan-out, gate-all, random
  labels, reviewer CWD = toplevel, verdict validation (adopt-needs-candidate,
  non-adopt-needs-null), label validity checked against the candidates dir.
- Back-compat handled; unique-id check; filesystem-safe id regex `[A-Za-z0-9_-]`.

BAD (one is a real spec defect):
- BROKEN anonymized autopsy: `_build_review_briefing` derives `failing_workers`
  by iterating `passing_workers` and keeping those whose gate did NOT pass --
  which is by construction always EMPTY. Gate-failure autopsies therefore NEVER
  appear in the reviewer briefing. Violates hard requirement #6.
- Its anonymization test only asserts worker ids are ABSENT; it never asserts
  the autopsy line is PRESENT, so the broken code slips through. The brief's
  required "autopsy of the failure is anonymized" scenario is uncovered.
- `_run_worker` returns gate_passed=False / gate_results=[] placeholders that a
  later loop overwrites by mutating the result dict -- works but fragile.

Checklist:
- [x] config schema/back-compat/ids      [x] blind parallel dispatch
- [x] gate-all                            [x] random labels + per-LABEL diffs
- [x] mapping not in reviewer inputs      [ ] anonymized autopsy in briefing (BROKEN)
- [x] verdict schema + validation         [x] exit 0/1/2
- [x] run.json contract                   [~] test rigor (autopsy path uncovered)
- [x] no merge / no tips writing

### Candidate C  -- WINNER

GOOD:
- Cleanest faithful extension of the M1 architecture. Config decomposed
  sensibly; rejects BOTH `worker` and `workers` present (strict, unambiguous
  back-compat); unique + filesystem-safe ids; reviewer optional at parse,
  required-at-runtime check when candidates exist (clear LoopError -> exit 2).
- Correct M2 flow: serialized adds with pre-checks, ThreadPoolExecutor fan-out,
  `_run_worker` does worker+gate per worktree, random labels via
  `random.shuffle`, per-LABEL diffs, reviewer CWD = toplevel.
- ANONYMIZED AUTOPSY BUILT CORRECTLY (iterates failed_workers, `a failed
  candidate: <autopsy>`), no worker ids.
- Verdict validation complete: presence of all three fields, outcome enum,
  adopt-needs-valid-label (checked against in-memory `label_to_worker_id`),
  non-adopt-needs-null.
- run.json EXACTLY to contract: M1 fields preserved, per-worker
  `candidate_label`, top-level `review` (or null). NO extra top-level fields,
  NO stray mapping file in the artifact dir. Best contract fidelity of the five.
- Also updates the committed `farnsworth.json` to the new schema -> repo stays
  internally consistent. ASCII summary; no third-party imports.
- Tests cover every brief-required scenario: two-pass + labels + diffs, briefing
  has no worker ids/mapping, adopt/synthesize/escalate each recorded, invalid
  verdict -> raise, adopt-bad-label -> raise, all-fail -> review null, legacy
  end-to-end, run.json == disk, config validation (dup/unsafe/empty/reviewer).

BAD:
- Test gap: the anonymized-AUTOPSY path is not asserted by any test (its
  anonymization test uses a single passing worker, so there is no gate-failed
  worker to autopsy). The CODE is correct on that path; only the test coverage
  is missing. This is the one thing C does less thoroughly than D/E.
- Anonymization test leans on `assertNotIn("w1", briefing)` with a short brief;
  fine here but a brittle pattern (a real brief could contain "w1").

Checklist: all hard requirements met; only the autopsy-path TEST is missing.
This is the single most contract-faithful, lowest-risk diff to merge as-is.

### Candidate D

GOOD:
- Most thorough tests by far: a dedicated `tests/test_tournament.py` (~800
  lines) plus updates to the existing suite. Covers two-pass-one-fail WITH an
  asserted anonymized autopsy, no-worker-ids, no-mapping, all three verdicts,
  invalid JSON, bad outcome, bad label, MISSING verdict file, all-fail -> null,
  legacy end-to-end, run.json == disk, all-gates-run-in-order, briefing order +
  separator, and full config-validation matrix.
- Correct autopsy (one line per gate-failed worker, anonymized). Config helper
  decomposition (`_validate_command`/`_validate_gate`) is clean; `worker_command`
  back-compat property kept. Verdict validation complete (reasoning must be
  non-empty str -- slightly stricter than spec but reasonable).

BAD:
- Writes a separate `candidate-mapping.json` audit file (same caveat as A).
- Minor cruft: an inner `_run_worker_task` is defined then never used (the
  executor calls `_run_single_worker` directly). Recomputes `finished_at` after
  review. Neither is a defect, just noise on the M1 base.

Checklist: all hard requirements met; best test rigor; mild code cruft + stray
mapping file. A strong #2; lost to C purely on contract leanness/cleanliness.

### Candidate E

GOOD:
- Best-engineered config module (static-method decomposition
  `_parse_workers`/`_parse_gate`/`_parse_reviewer`, schema in the docstring).
- Cleanest loop: plan-then-create worktrees (fails before side effects),
  parallel fan-out, gate-all, `_label_sequence`, per-LABEL diffs, reviewer CWD =
  toplevel, complete verdict validation.
- STRONGEST anonymization test: asserts task text + `candidate A/B` present, the
  `a failed candidate:` autopsy present, AND no worker ids AND no model names
  ("haiku") leak. Also asserts no merge (main HEAD unchanged) and that the
  internal `_worktree_abs` key is stripped from run.json.
- Ships a fuller default `farnsworth.json` (the 5-worker fleet from the PRD).

BAD (the disqualifier for adopt):
- Adds an UNDOCUMENTED top-level `"label_mapping"` field to run.json. The brief
  (#8) and the acceptance criterion "run.json M1 field names preserved; new
  fields exactly as specified" enumerate ONLY `review` (top-level) and per-worker
  `candidate_label`. `label_mapping` is an extra, unrequested field and is fully
  redundant with the per-worker `candidate_label`. task-001 already established
  run.json as "an exact contract". Writing the mapping after the reviewer exits
  is fine; putting it in run.json as a new top-level key is a contract deviation.
- Uses env var `FARN_TASK` to pass the task id to its fake reviewer in tests --
  harmless in tests, but a reminder that the real reviewer must get the verdict
  path from the briefing, which E's production briefing does correctly.

Checklist: every behavioral requirement met and the best anonymization test in
the field, BUT the run.json field contract is violated by the extra
`label_mapping` key. That single deviation is what keeps E from adopt.

## Verdict

ADOPT C.

Rationale: C is the most spec-faithful diff in the field with correct behavior
on every hard requirement, the leanest run.json (exact contract, no stray
top-level keys, no extra artifact-dir files), strict and unambiguous back-compat,
and a clean extension of the M1 module boundaries. Its only shortfall is a
missing TEST for the anonymized-autopsy path (the underlying code is correct);
follow-up: add one gate-failing-worker test asserting `a failed candidate:`
appears in the reviewer briefing (borrow D's or E's assertion). E is the best
engineering but violates the exact run.json contract (`label_mapping`); D is the
best tested but carries a stray mapping file + dead code; B has a real spec
defect (autopsy never reaches the briefing) hidden by a weak test; A's headline
required scenario is not actually exercised. No splicing -- C stands on its own.
