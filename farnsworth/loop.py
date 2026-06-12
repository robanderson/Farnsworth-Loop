"""The multi-worker loop body with review (Milestone M2, Tournament).

One invocation:

  1. Verify the CWD is a clean git repo.
  2. Create N worktrees ``../<task-id>-<worker-id>`` in parallel, one per worker.
  3. Run each worker command in its worktree (parallel fan-out).
  4. Run each gate command in each worktree (all workers gated).
  5. Anonymize passing candidates: assign labels A, B, C, ... in random order.
  6. If any candidates passed: run the reviewer with an anonymized briefing.
  7. Parse and validate the verdict.json from the reviewer.
  8. Write .farnsworth/<task-id>/run.json in the MAIN repo.
  9. Leave all worktrees in place for manual inspection/merge.

Full support for multiple workers, blind dispatch, anonymized review, and verdicts.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import json
import os
import random
import shutil
import subprocess

from . import gitutil, report
from .config import Config, DEFAULT_CONFIG_NAME
from .divergence import divergence


class LoopError(RuntimeError):
    """Raised on a precondition failure that aborts the run."""


# Rules of engagement for every dispatched worker, in BOTH dispatch modes.
# Subprocess workers used to receive only tips + task (the preamble lived in
# delegate dispatch alone), which left the artifact rule and the tips-file
# hygiene contract traveling by hope — and word-garden-4's non-committing
# worker was a subprocess-mode run.
WORKER_PREAMBLE = """\
You are worker {worker_id} in a Farnsworth Loop tournament round.

Rules of engagement:
- Work ONLY inside this worktree (you are already in it); never touch the
  main repository, other worktrees, or anything outside this directory.
- Implement the task below completely, then COMMIT all of your work to the
  current branch ({branch}) with clear messages. Your committed diff against
  the base commit is the deliverable; uncommitted work does not exist.
- Run the project's tests yourself before finishing.
- Time-box yourself: this round is EXPLORATION. Make one complete, honest
  attempt; if something still fails after a couple of fix passes, COMMIT
  what you have and note the gap in the commit message. Gate results
  travel with your candidate as evidence, and an instructive incomplete
  attempt beats an endless local debugging loop, which counts as no
  attempt at all when the clock runs out.
- Do the work YOURSELF, in this session: never spawn, launch, or delegate
  to sub-agents. A delegated attempt ends your turn with a completion
  claim and no commits, which counts as no attempt at all.
- Never create or modify `.code-tips.md` (read-only briefing material).
- You work blind: do not look for, or at, other workers' attempts.

----

{briefing}
"""


def _utcnow_iso():
    """Return the current UTC time as an ISO-8601 string with a Z suffix."""
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def task_id_from_brief(brief_path):
    """Derive the task id from the brief path stem (``task-042.md`` -> ``task-042``)."""
    base = os.path.basename(brief_path)
    stem, _ext = os.path.splitext(base)
    return stem


def build_briefing(repo_root, brief_path):
    """Construct the worker briefing.

    The briefing is the contents of ``.code-tips.md`` (if present in the repo
    root), then ``"\n\nTASK: "``, then the contents of the task brief file.
    """
    tips_path = os.path.join(repo_root, ".code-tips.md")
    tips = ""
    if os.path.exists(tips_path):
        with open(tips_path, "r", encoding="utf-8") as fh:
            tips = fh.read()
    with open(brief_path, "r", encoding="utf-8") as fh:
        brief = fh.read()
    return tips + "\n\nTASK: " + brief


def focus_briefing(briefing, focus):
    """Append a worker's focus directive to the shared briefing.

    The directive is a lens for choices the task brief leaves open — its
    purpose is to widen the code space the blind field searches — never a
    license to deviate from the brief, which stays supreme.
    """
    if not focus:
        return briefing
    return (
        briefing
        + "\n\nFOCUS DIRECTIVE: "
        + focus
        + "\nApply this focus wherever the task brief leaves an "
        "implementation choice open. The task brief and its acceptance "
        "criteria always take precedence over the focus directive."
    )


def _substitute_prompt(command, prompt):
    """Replace any ``{prompt}`` token within each argv element with ``prompt``."""
    return [arg.replace("{prompt}", prompt) for arg in command]


def _decode_stream(data):
    """Best-effort text from a TimeoutExpired stream (str, bytes, or None)."""
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data


def _one_line(text):
    """Return the last non-empty line of ``text``, stripped, or ''."""
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _extract_cost_usd(stdout_text):
    """Best-effort ``total_cost_usd`` from a command's JSON output, or None.

    ``claude -p --output-format json`` emits one JSON object on stdout;
    other worker commands emit whatever they like, so anything unparseable
    simply yields no cost row.
    """
    text = (stdout_text or "").strip()
    if not text:
        return None
    candidates = [text]
    last_line = text.splitlines()[-1].strip()
    if last_line != text:
        candidates.append(last_line)
    for chunk in candidates:
        try:
            data = json.loads(chunk)
        except ValueError:
            continue
        if isinstance(data, dict):
            cost = data.get("total_cost_usd")
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                return cost
        return None
    return None


def protected_paths(repo_root, brief_path, config_path=None):
    """Repo-relative paths no candidate may modify (the hygiene contract).

    The tips file is reviewer-owned, the fleet config and the task brief are
    the round's contract. Workers are told this in the preamble; the gate
    enforces it mechanically here, because told-in-the-briefing is exactly
    the enforcement level that failed for the commit rule in word-garden-4.
    """
    protected = {".code-tips.md", DEFAULT_CONFIG_NAME}
    for path in (brief_path, config_path):
        if not path:
            continue
        rel = os.path.relpath(os.path.abspath(path), repo_root)
        if not rel.startswith(".."):
            protected.add(rel)
    return protected


def hygiene_violations(base_commit, worktree_abs, protected):
    """Return the sorted protected paths the candidate's commits touched."""
    changed = set(gitutil.changed_paths(base_commit, worktree_abs))
    return sorted(changed & set(protected))


# A gate command that blocks can hang the whole phase (observed live,
# word-garden-6: a dead worker's abandoned test suite looped forever and a
# 5-second gate ran 16+ minutes before a human killed it). Every gate
# command therefore runs with stdin closed and a deadline: per-entry
# ``timeout_seconds`` in the config, this default otherwise.
GATE_TIMEOUT_DEFAULT = 300


def _run_gate(gate, worktree):
    """Run every gate command in ``worktree`` and return (passed, results).

    All gates run even if an earlier one fails. Each result records the gate
    name, the exit code, and a one-line autopsy. Commands get stdin from
    /dev/null (interactive code under test must not block the gate) and are
    killed at their deadline with exit code -1.
    """
    results = []
    passed = True
    for entry in gate:
        name = entry["name"]
        timeout = entry.get("timeout") or GATE_TIMEOUT_DEFAULT
        try:
            proc = subprocess.run(
                entry["command"],
                cwd=str(worktree),
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=timeout,
            )
            exit_code = proc.returncode
            autopsy = "{0}: exit {1}".format(name, exit_code)
            if exit_code != 0:
                passed = False
                # pytest and most linters report failures on stdout, unittest
                # on stderr; an autopsy with no tail tells the reviewer
                # nothing.
                tail = _one_line(proc.stderr) or _one_line(proc.stdout)
                if tail:
                    autopsy = "{0} | {1}".format(autopsy, tail)
        except subprocess.TimeoutExpired:
            passed = False
            exit_code = -1
            autopsy = (
                "{0}: killed after {1}s timeout (a gate command must never "
                "block: suspect stdin reads or an infinite loop)".format(
                    name, timeout
                )
            )
        results.append(
            {
                "name": name,
                "exit_code": exit_code,
                "autopsy": autopsy,
            }
        )
    return passed, results


def check_done(goal, repo_root):
    """Run the goal's done checks at ``repo_root``.

    The loop-termination probe (PRD Section 2.4): exit-style truth about
    whether the primary goal's mechanical completion criteria pass against
    the currently merged state. Returns ``{"passed": bool, "results":
    [...]}`` in the same shape as a gate result. The reviewer's attestation
    is the other half of "done"; this is only the mechanical half.
    """
    passed, results = _run_gate(goal["done"], repo_root)
    return {"passed": passed, "results": results}


def record_done_outcome(outcome, repo_root):
    """Write the done probe's result to ``.farnsworth/done-checks.json``.

    All loop state is file-based and reconstructible from git history
    (Section 4.4); a probe whose result exists only on a terminal isn't.
    The file holds the LATEST probe — git history is the series, which is
    also what STALLED detection (3 iterations without progress) needs.
    """
    farnsworth_dir = os.path.join(repo_root, ".farnsworth")
    os.makedirs(farnsworth_dir, exist_ok=True)
    path = os.path.join(farnsworth_dir, "done-checks.json")
    payload = {
        "checked_at": _utcnow_iso(),
        "passed": outcome["passed"],
        "results": outcome["results"],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    return path


def build_attestation_briefing(goal):
    """The reviewer protocol for the semantic half of "done" (Section 2.4).

    Written by the CLI for the same reason the review protocol is: a
    protocol that travels inside an orchestrator's prompt is a protocol
    that drifts (the word-garden-5 lesson, applied to the goal contract's
    other artifact type).
    """
    brief = goal.get("brief")
    brief_line = (
        "Goal brief: {0}".format(brief)
        if brief
        else "Goal brief: (none configured; attest against the project's stated goal)"
    )
    lines = [
        "# Goal Attestation Briefing",
        "",
        "The mechanical done checks pass. Mechanics are necessary, not",
        "sufficient: you are the SEMANTIC half of the termination contract",
        "(PRD Section 2.4). Attest -- or refuse to attest -- that the merged",
        "state meets the goal brief's acceptance criteria. Exit DONE requires",
        "both halves.",
        "",
        brief_line,
        "",
        "## Protocol",
        "",
        "1. Read the goal brief and enumerate its acceptance criteria.",
        "2. Verify each criterion EMPIRICALLY against the merged state (run",
        "   the code, probe the behavior); never attest from reading alone.",
        "3. Write the full attestation to .farnsworth/attestation.md:",
        "   per-criterion evidence, and any residual gaps.",
        "4. Write .farnsworth/attestation.json LAST, with schema:",
        "",
        '   {"goal_met": true | false, "reasoning": "..."}',
        "",
        "goal_met true means the loop exits DONE. goal_met false means the",
        "loop keeps cycling, and your reasoning must name the gap the next",
        "task brief should close.",
        "",
    ]
    return "\n".join(lines)


def write_attestation_briefing(goal, repo_root):
    """Write the attestation briefing under ``.farnsworth/`` and return its path."""
    farnsworth_dir = os.path.join(repo_root, ".farnsworth")
    os.makedirs(farnsworth_dir, exist_ok=True)
    path = os.path.join(farnsworth_dir, "attestation-briefing.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build_attestation_briefing(goal))
    return path


def _run_worker(worker_spec, briefing, worktree_abs, artifact_dir, gate):
    """Run a single worker and return (exit_code, gate_passed, gate_results).

    Called in parallel for each worker.
    """
    worker_id = worker_spec["id"]
    command = _substitute_prompt(worker_spec["command"], briefing)

    # Run the worker command. A hung worker must not hang the run: on
    # timeout the child is killed, the exit code is recorded as -1, and
    # whatever the worker committed before stalling still faces the gate.
    timeout = worker_spec.get("timeout")
    try:
        worker_proc = subprocess.run(
            command,
            cwd=worktree_abs,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = worker_proc.returncode
        stdout_text = worker_proc.stdout or ""
        stderr_text = worker_proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        exit_code = -1
        stdout_text = _decode_stream(exc.stdout)
        stderr_text = _decode_stream(exc.stderr) + (
            "\nfarnsworth: worker killed after {0}s timeout\n".format(timeout)
        )

    # Write stdout/stderr.
    stdout_name = "{0}.stdout".format(worker_id)
    stderr_name = "{0}.stderr".format(worker_id)
    with open(os.path.join(artifact_dir, stdout_name), "w", encoding="utf-8") as fh:
        fh.write(stdout_text)
    with open(os.path.join(artifact_dir, stderr_name), "w", encoding="utf-8") as fh:
        fh.write(stderr_text)

    # Run the mechanical gate.
    gate_passed, gate_results = _run_gate(gate, worktree_abs)

    return {
        "exit_code": exit_code,
        "gate_passed": gate_passed,
        "gate_results": gate_results,
        "stdout_name": stdout_name,
        "stderr_name": stderr_name,
        "cost_usd": _extract_cost_usd(stdout_text),
    }


def load_and_validate_verdict(artifact_dir, label_to_worker_id):
    """Load ``verdict.json`` from ``artifact_dir`` and validate the contract.

    The verdict is the review phase's artifact: outcome is exactly one of
    adopt/synthesize/escalate; adopt names a real candidate label; the
    other outcomes carry a null candidate. Raises LoopError otherwise.
    """
    verdict_path = os.path.join(artifact_dir, "verdict.json")
    try:
        with open(verdict_path, "r", encoding="utf-8") as fh:
            verdict = json.load(fh)
    except FileNotFoundError:
        raise LoopError("reviewer did not write verdict.json")
    except json.JSONDecodeError as exc:
        raise LoopError("verdict.json is not valid JSON: {0}".format(exc))

    if not isinstance(verdict, dict):
        raise LoopError("verdict.json root must be a JSON object")
    for field in ("outcome", "candidate", "reasoning"):
        if field not in verdict:
            raise LoopError("verdict.json missing '{0}' field".format(field))

    outcome = verdict["outcome"]
    candidate_label = verdict["candidate"]

    if outcome not in ("adopt", "synthesize", "escalate"):
        raise LoopError(
            "verdict outcome must be one of adopt/synthesize/escalate, got: {0}".format(
                outcome
            )
        )

    if outcome == "adopt":
        if not candidate_label or candidate_label not in label_to_worker_id:
            raise LoopError(
                "outcome is 'adopt' but candidate is missing or invalid: {0}".format(
                    candidate_label
                )
            )
    else:
        # synthesize or escalate
        if candidate_label is not None:
            raise LoopError(
                "outcome is '{0}' but candidate should be null, got: {1}".format(
                    outcome, candidate_label
                )
            )
    return verdict

def review_env_path(task_id, repo_root):
    """Sibling directory holding the constructed review environment."""
    return os.path.join(
        os.path.dirname(repo_root), "{0}-review".format(task_id)
    )


def _construct_review_env(review_env, base_commit, repo_root, artifact_dir, task_id):
    """Build the anonymized environment the reviewer runs in.

    The reviewer gets the base tree, the labeled candidate diffs, and the
    gate notes in its briefing -- NOTHING else. A naive clone or worktree
    carries worker-named branches (``task-NNN-w1``...), and the project's
    ``farnsworth.json`` maps worker ids to models and foci, either of which
    de-anonymizes the field. The environment is therefore constructed: the
    exported tree of the base commit, minus ``farnsworth.json`` and any
    committed ``.farnsworth/`` artifacts of earlier tasks, re-initialized as
    a fresh single-commit repo so the reviewer can ``git apply`` each diff
    and ``git reset --hard`` between candidates.
    """
    os.makedirs(review_env)
    gitutil.export_tree(base_commit, review_env, repo_root)

    # Strip attribution surfaces from the exported tree.
    fleet_config = os.path.join(review_env, "farnsworth.json")
    if os.path.exists(fleet_config):
        os.remove(fleet_config)
    committed_artifacts = os.path.join(review_env, ".farnsworth")
    if os.path.isdir(committed_artifacts):
        shutil.rmtree(committed_artifacts)

    # Labeled diffs at the same relative path the briefing references.
    shutil.copytree(
        os.path.join(artifact_dir, "candidates"),
        os.path.join(review_env, ".farnsworth", task_id, "candidates"),
    )
    gitutil.init_review_repo(review_env)


def _copy_back_review_artifacts(review_env, artifact_dir, task_id):
    """Copy the reviewer's artifacts out of the review environment.

    Everything the reviewer wrote under ``.farnsworth/<task-id>/`` --
    verdict.json, review.md, blind-sketch.md, code-tips.next.md -- comes
    back to the main repo's artifact dir. The candidates/ dir is skipped:
    the main repo's copies are the originals of record.
    """
    src = os.path.join(review_env, ".farnsworth", task_id)
    if not os.path.isdir(src):
        return
    for name in os.listdir(src):
        if name == "candidates":
            continue
        source = os.path.join(src, name)
        dest = os.path.join(artifact_dir, name)
        if os.path.isdir(source):
            shutil.copytree(source, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(source, dest)


def run(brief_path, config_path=None, cwd=None):
    """Execute the multi-worker loop body with review (subprocess dispatch).

    Returns the run-log dict. Raises LoopError on a precondition failure.
    Delegate-mode configs must use the phased flow in ``delegate.py``
    (prepare -> host session spawns subagents -> gate -> reviewer subagent
    -> finalize); this entry point refuses them.
    """
    cwd = cwd or os.getcwd()

    # (a) Verify clean git repo.
    if not gitutil.is_git_repo(cwd):
        raise LoopError("not a git repository: {0}".format(cwd))
    repo_root = gitutil.repo_toplevel(cwd)
    if not gitutil.is_clean_worktree(repo_root):
        raise LoopError(
            "working tree is not clean; commit or stash changes before running"
        )

    if not os.path.exists(brief_path):
        raise LoopError("task brief not found: {0}".format(brief_path))

    config = Config.load(config_path)
    if config.mode == "delegate":
        raise LoopError(
            "config uses delegate dispatch (workers carry 'model'); use "
            "'farnsworth run' to prepare, have the host session spawn the "
            "subagents, then 'farnsworth gate' and 'farnsworth finalize'"
        )

    task_id = task_id_from_brief(brief_path)
    parent = os.path.dirname(repo_root)
    base_commit = gitutil.head_commit(repo_root)
    started_at = _utcnow_iso()

    # (b) Create all worktrees upfront (serial); must be done before parallel fan-out.
    # The review environment's path is also claimed now: discovering the
    # collision only after the workers have run would waste the whole field.
    review_env = review_env_path(task_id, repo_root)
    if os.path.exists(review_env):
        raise LoopError(
            "review environment path already exists: {0}".format(review_env)
        )

    worktree_specs = []
    for worker_spec in config.workers:
        worker_id = worker_spec["id"]
        branch = "{0}-{1}".format(task_id, worker_id)
        worktree_rel = "../{0}-{1}".format(task_id, worker_id)
        worktree_abs = os.path.join(parent, "{0}-{1}".format(task_id, worker_id))

        # Check for collisions before creating.
        if gitutil.branch_exists(branch, repo_root):
            raise LoopError("branch already exists: {0}".format(branch))
        if os.path.exists(worktree_abs):
            raise LoopError("worktree path already exists: {0}".format(worktree_abs))

        gitutil.add_worktree(worktree_abs, branch, repo_root)
        worktree_specs.append(
            {
                "worker_id": worker_id,
                "branch": branch,
                "worktree_rel": worktree_rel,
                "worktree_abs": worktree_abs,
            }
        )

    # Per-task artifact directory lives in the MAIN repo.
    artifact_dir = os.path.join(repo_root, ".farnsworth", task_id)
    os.makedirs(artifact_dir, exist_ok=True)

    # (c) Build the briefing once, use for all workers.
    briefing = build_briefing(repo_root, brief_path)

    # (d) Run all workers in parallel, each under the shared preamble.
    worker_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(config.workers)) as executor:
        futures = {}
        for i, worktree_spec in enumerate(worktree_specs):
            worker_id = worktree_spec["worker_id"]
            worktree_abs = worktree_spec["worktree_abs"]
            worker_spec = config.workers[i]

            prompt = WORKER_PREAMBLE.format(
                worker_id=worker_id,
                branch=worktree_spec["branch"],
                briefing=focus_briefing(briefing, worker_spec.get("focus")),
            )
            future = executor.submit(
                _run_worker,
                worker_spec,
                prompt,
                worktree_abs,
                artifact_dir,
                config.gate,
            )
            futures[worker_id] = future

        for worker_id, future in futures.items():
            worker_results[worker_id] = future.result()

    # (e) Identify candidates (workers whose gate passed AND committed).
    #
    # PRD 4.3: commits in the worktree are the phase artifact. The gate runs
    # in the worktree, where uncommitted files execute fine — but the
    # candidate diff is base..HEAD, so a no-commit worker would enter review
    # as an empty diff the briefing vouches for (observed live: word-garden-4
    # task-002). Enforce the artifact rule mechanically here, and archive the
    # uncommitted work so a later `clean --force` cannot destroy the only
    # copy of what the worker actually did.
    protected = protected_paths(repo_root, brief_path, config_path)
    candidates = []
    failed_workers = []
    for i, worktree_spec in enumerate(worktree_specs):
        worker_id = worktree_spec["worker_id"]
        result = worker_results[worker_id]
        if (
            result["gate_passed"]
            and gitutil.head_commit(worktree_spec["worktree_abs"]) == base_commit
        ):
            uncommitted = gitutil.snapshot_uncommitted_diff(
                worktree_spec["worktree_abs"]
            )
            autopsy = "commits: no commits on branch"
            if uncommitted.strip():
                with open(
                    os.path.join(
                        artifact_dir, "{0}-uncommitted.diff".format(worker_id)
                    ),
                    "w",
                    encoding="utf-8",
                ) as fh:
                    fh.write(uncommitted)
                autopsy += " (uncommitted work archived)"
            result["gate_passed"] = False
            result["gate_results"].append(
                {"name": "commits", "exit_code": 1, "autopsy": autopsy}
            )
        if result["gate_passed"]:
            # Hygiene contract, enforced mechanically: the tips file, the
            # fleet config, and the brief are off limits to candidates.
            violations = hygiene_violations(
                base_commit, worktree_spec["worktree_abs"], protected
            )
            if violations:
                result["gate_passed"] = False
                result["gate_results"].append(
                    {
                        "name": "hygiene",
                        "exit_code": 1,
                        "autopsy": "hygiene: modified protected file(s): "
                        + ", ".join(violations),
                    }
                )
        if result["gate_passed"]:
            candidates.append(
                {
                    "worker_id": worker_id,
                    "worktree_abs": worktree_spec["worktree_abs"],
                    "base_commit": base_commit,
                }
            )
        else:
            failed_workers.append(
                {
                    "worker_id": worker_id,
                    "gate_results": result["gate_results"],
                }
            )

    # (f) Anonymize candidates: shuffle, drop empty diffs, assign labels.
    random.shuffle(candidates)
    label_to_worker_id = {}
    label_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    labeled = []
    for candidate in candidates:
        # Belt-and-braces companion to the commit check in (e): a candidate
        # whose diff against base is empty (e.g. only an empty commit) has
        # nothing to review and must not consume a label.
        text = gitutil.diff_text(base_commit, candidate["worktree_abs"])
        if not text.strip():
            result = worker_results[candidate["worker_id"]]
            result["gate_passed"] = False
            result["gate_results"].append(
                {
                    "name": "candidate",
                    "exit_code": 1,
                    "autopsy": "candidate: empty diff against base",
                }
            )
            failed_workers.append(
                {
                    "worker_id": candidate["worker_id"],
                    "gate_results": result["gate_results"],
                }
            )
            continue
        label = label_chars[len(labeled)]
        label_to_worker_id[label] = candidate["worker_id"]
        candidate["label"] = label
        candidate["diff_text"] = text

        diff_path = os.path.join(artifact_dir, "candidates", "{0}.diff".format(label))
        os.makedirs(os.path.dirname(diff_path), exist_ok=True)
        with open(diff_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        labeled.append(candidate)
    candidates = labeled

    # Field divergence, recorded for M4 threshold calibration (Section 2.2):
    # content-based, because file footprints are identical in every recorded
    # round even under deliberate focus diversification.
    field_divergence = divergence([c["diff_text"] for c in candidates])

    # (g) Build run.json workers[] list for all workers (including non-candidates).
    run_workers = []
    for i, worktree_spec in enumerate(worktree_specs):
        worker_id = worktree_spec["worker_id"]
        result = worker_results[worker_id]

        # Find the label assigned to this worker (if a candidate).
        candidate_label = None
        for label, wid in label_to_worker_id.items():
            if wid == worker_id:
                candidate_label = label
                break

        run_workers.append(
            {
                "id": worker_id,
                "branch": worktree_spec["branch"],
                "worktree": worktree_spec["worktree_rel"],
                "exit_code": result["exit_code"],
                "stdout_file": result["stdout_name"],
                "focus": config.workers[i].get("focus"),
                "cost_usd": result["cost_usd"],
                "gate": {
                    "passed": result["gate_passed"],
                    "results": result["gate_results"],
                },
                "candidate_label": candidate_label,
            }
        )

    # (h) Review phase: if any candidates, run the reviewer.
    review_exit_code = None
    verdict = None
    if candidates:
        # Check that reviewer is configured.
        if not config.reviewer:
            raise LoopError(
                "candidates passed gate but no reviewer configured in config"
            )

        # Build the review briefing. Focus directives are disclosed as a
        # sorted, UNATTRIBUTED set: the reviewer should know the field was
        # deliberately diversified, but a per-candidate focus would link
        # labels back to worker specs and break anonymization.
        focus_directives = sorted(
            {w.get("focus") for w in config.workers if w.get("focus")}
        )
        review_briefing = build_review_briefing(
            brief_path,
            repo_root,
            artifact_dir,
            candidates,
            failed_workers,
            focus_directives=focus_directives,
        )

        # The reviewer runs in a constructed, anonymized environment, never
        # in the main repo (whose branches and farnsworth.json identify the
        # workers). Kept in place afterwards for inspection, like worktrees.
        _construct_review_env(
            review_env, base_commit, repo_root, artifact_dir, task_id
        )

        # Run the reviewer. A hung reviewer is an infrastructure failure:
        # the verdict is the phase's artifact and it cannot be partial.
        reviewer_command = _substitute_prompt(config.reviewer["command"], review_briefing)
        reviewer_timeout = config.reviewer.get("timeout")
        try:
            reviewer_proc = subprocess.run(
                reviewer_command,
                cwd=review_env,
                capture_output=True,
                text=True,
                timeout=reviewer_timeout,
            )
        except subprocess.TimeoutExpired:
            raise LoopError(
                "reviewer timed out after {0}s; candidate worktrees and the "
                "review environment were kept. Re-run the review or "
                "'farnsworth clean {1}' and re-dispatch".format(
                    reviewer_timeout, task_id
                )
            )
        review_exit_code = reviewer_proc.returncode

        # Bring the reviewer's artifacts back to the repo of record before
        # the verdict is parsed.
        _copy_back_review_artifacts(review_env, artifact_dir, task_id)

        # Write reviewer stdout/stderr.
        with open(os.path.join(artifact_dir, "reviewer.stdout"), "w", encoding="utf-8") as fh:
            fh.write(reviewer_proc.stdout or "")
        with open(os.path.join(artifact_dir, "reviewer.stderr"), "w", encoding="utf-8") as fh:
            fh.write(reviewer_proc.stderr or "")

        # Parse and validate verdict.json.
        verdict = load_and_validate_verdict(artifact_dir, label_to_worker_id)

    finished_at = _utcnow_iso()

    # (i) Build the final run.json.
    run_log = {
        "task_id": task_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "base_commit": base_commit,
        "divergence": field_divergence,
        "workers": run_workers,
    }

    if candidates:
        run_log["review"] = {
            "exit_code": review_exit_code,
            "environment": "../{0}-review".format(task_id),
            "cost_usd": _extract_cost_usd(reviewer_proc.stdout),
            "verdict": verdict,
        }
    else:
        run_log["review"] = None

    # (j) Write run.json and the short what-happened table in the MAIN repo.
    with open(os.path.join(artifact_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(run_log, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(artifact_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(report.summary_table(run_log))

    return run_log


def build_review_briefing(
    brief_path,
    repo_root,
    artifact_dir,
    candidates,
    failed_workers,
    focus_directives=None,
):
    """Build the anonymized review briefing.

    Contains: task brief verbatim, labels and relative paths to diffs, one-line
    autopsies of failed workers (anonymized), the round's focus directives as
    an unattributed sorted list (when any), and instructions for the verdict.
    """
    with open(brief_path, "r", encoding="utf-8") as fh:
        brief_text = fh.read()

    task_id = os.path.basename(artifact_dir)
    lines = [brief_text]
    lines.append("")
    lines.append("## Candidates")
    lines.append("")

    for candidate in candidates:
        label = candidate["label"]
        # The path the review environment actually serves the diff at.
        diff_path = ".farnsworth/{0}/candidates/{1}.diff".format(
            task_id, label
        )
        lines.append("- Candidate {0}: {1}".format(label, diff_path))

    if focus_directives:
        lines.append("")
        lines.append("## Field Diversity")
        lines.append("")
        lines.append(
            "Workers in this round were dispatched with the following focus "
            "directives (listed sorted and UNATTRIBUTED -- the mapping to "
            "candidates is sealed). Judge each candidate against the task's "
            "acceptance criteria, not against any guessed focus."
        )
        lines.append("")
        for directive in focus_directives:
            lines.append("- {0}".format(directive))

    if failed_workers:
        lines.append("")
        lines.append("## Gate Failures")
        lines.append("")
        for failed in failed_workers:
            for gate_result in failed["gate_results"]:
                autopsy = gate_result["autopsy"]
                lines.append("- a failed candidate: {0}".format(autopsy))

    lines.append("")
    lines.append("## Review Protocol")
    lines.append("")
    lines.append(
        "You are in a constructed, anonymized review environment: the "
        "project tree at the base commit plus the labeled candidate diffs "
        "and the gate notes above -- nothing else. Do not attempt to "
        "identify candidate authorship; judge every candidate against the "
        "task's acceptance criteria only."
    )
    lines.append("")
    lines.append(
        "1. BEFORE reading any candidate diff, write your own brief "
        "implementation sketch to .farnsworth/{0}/blind-sketch.md "
        "(anchoring defence; if you synthesize, your sketch counts as one "
        "more candidate).".format(task_id)
    )
    lines.append(
        "2. Examine every candidate: apply its diff (git apply), exercise "
        "the result empirically, then return to base with "
        "`git reset --hard && git clean -fd -e .farnsworth` before the "
        "next. The clean step matters: files a diff CREATES are untracked "
        "after git apply, so reset alone leaves them behind and candidates "
        "would stack (worst on greenfield tasks, where a candidate is ALL "
        "new files). The `-e .farnsworth` exclusion protects your own "
        "notes; the labeled diffs are committed in the review base and "
        "survive regardless. Record what is good AND bad in each "
        "candidate, not just a ranking."
    )
    lines.append(
        "3. Write the full review to .farnsworth/{0}/review.md.".format(
            task_id
        )
    )
    lines.append(
        "4. Distill the durable lessons of the whole field (winners and "
        "losers) into .farnsworth/{0}/code-tips.next.md: the COMPLETE next "
        "contents of the project's .code-tips.md -- existing entries "
        "preserved unless consolidated, new entries in imperative contract "
        "language with explicit scope (source, tests, or both) and "
        "provenance \"[YYYY-MM-DD, {0}]\". Lessons must be durable project "
        "truths that pay rent in every future briefing, not incident "
        "reports. The orchestrator installs this file after the "
        "merge. GENERALIZE WHILE DISTILLING: when a lesson instantiates a "
        "domain-general class (it would pay rent in ANY project, not just "
        "this one), also write the GENERAL form to "
        ".farnsworth/{0}/seed-tips.next.md -- the orchestrator routes those "
        "entries into the cross-project seed pile; the project-specific "
        "form stays in code-tips.next.md.".format(task_id)
    )
    lines.append(
        "5. Write the verdict LAST (schema below). When the outcome is "
        "adopt, include a \"progression\" key: how the adopted candidate "
        "advances the previously merged state of the project -- what it "
        "built on, what is new, what got better, and which tips it visibly "
        "absorbed."
    )
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append("Write .farnsworth/{0}/verdict.json with schema:".format(
        task_id
    ))
    lines.append("")
    lines.append('{"outcome": "adopt" | "synthesize" | "escalate",')
    lines.append(' "candidate": "A" | null,')
    lines.append(' "reasoning": "...",')
    lines.append(' "progression": "..." (required when outcome is adopt)}')
    lines.append("")

    return "\n".join(lines)
