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
import subprocess

from . import gitutil, report
from .config import Config


class LoopError(RuntimeError):
    """Raised on a precondition failure that aborts the run."""


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


def _run_gate(gate, worktree):
    """Run every gate command in ``worktree`` and return (passed, results).

    All gates run even if an earlier one fails. Each result records the gate
    name, the exit code, and a one-line autopsy.
    """
    results = []
    passed = True
    for entry in gate:
        name = entry["name"]
        proc = subprocess.run(
            entry["command"],
            cwd=str(worktree),
            capture_output=True,
            text=True,
        )
        autopsy = "{0}: exit {1}".format(name, proc.returncode)
        if proc.returncode != 0:
            passed = False
            tail = _one_line(proc.stderr)
            if tail:
                autopsy = "{0} | {1}".format(autopsy, tail)
        results.append(
            {
                "name": name,
                "exit_code": proc.returncode,
                "autopsy": autopsy,
            }
        )
    return passed, results


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
    }


def run(brief_path, config_path=None, cwd=None):
    """Execute the multi-worker loop body with review.

    Returns the run-log dict. Raises LoopError on a precondition failure.
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

    task_id = task_id_from_brief(brief_path)
    parent = os.path.dirname(repo_root)
    base_commit = gitutil.head_commit(repo_root)
    started_at = _utcnow_iso()

    # (b) Create all worktrees upfront (serial); must be done before parallel fan-out.
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

    # (d) Run all workers in parallel.
    worker_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(config.workers)) as executor:
        futures = {}
        for i, worktree_spec in enumerate(worktree_specs):
            worker_id = worktree_spec["worker_id"]
            worktree_abs = worktree_spec["worktree_abs"]
            worker_spec = config.workers[i]

            future = executor.submit(
                _run_worker,
                worker_spec,
                focus_briefing(briefing, worker_spec.get("focus")),
                worktree_abs,
                artifact_dir,
                config.gate,
            )
            futures[worker_id] = future

        for worker_id, future in futures.items():
            worker_results[worker_id] = future.result()

    # (e) Identify candidates (workers whose gate passed).
    candidates = []
    failed_workers = []
    for i, worktree_spec in enumerate(worktree_specs):
        worker_id = worktree_spec["worker_id"]
        result = worker_results[worker_id]
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

    # (f) Anonymize candidates: shuffle and assign labels A, B, C, ...
    random.shuffle(candidates)
    label_to_worker_id = {}
    label_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i, candidate in enumerate(candidates):
        label = label_chars[i]
        label_to_worker_id[label] = candidate["worker_id"]
        candidate["label"] = label

        # Write the diff for this candidate.
        diff_path = os.path.join(artifact_dir, "candidates", "{0}.diff".format(label))
        os.makedirs(os.path.dirname(diff_path), exist_ok=True)
        gitutil.write_diff(
            base_commit, candidate["worktree_abs"], diff_path, repo_root
        )

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

        # Run the reviewer. A hung reviewer is an infrastructure failure:
        # the verdict is the phase's artifact and it cannot be partial.
        reviewer_command = _substitute_prompt(config.reviewer["command"], review_briefing)
        reviewer_timeout = config.reviewer.get("timeout")
        try:
            reviewer_proc = subprocess.run(
                reviewer_command,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=reviewer_timeout,
            )
        except subprocess.TimeoutExpired:
            raise LoopError(
                "reviewer timed out after {0}s; candidate worktrees were kept. "
                "Re-run the review or 'farnsworth clean {1}' and re-dispatch".format(
                    reviewer_timeout, task_id
                )
            )
        review_exit_code = reviewer_proc.returncode

        # Write reviewer stdout/stderr.
        with open(os.path.join(artifact_dir, "reviewer.stdout"), "w", encoding="utf-8") as fh:
            fh.write(reviewer_proc.stdout or "")
        with open(os.path.join(artifact_dir, "reviewer.stderr"), "w", encoding="utf-8") as fh:
            fh.write(reviewer_proc.stderr or "")

        # Parse and validate verdict.json.
        verdict_path = os.path.join(artifact_dir, "verdict.json")
        try:
            with open(verdict_path, "r", encoding="utf-8") as fh:
                verdict = json.load(fh)
        except FileNotFoundError:
            raise LoopError("reviewer did not write verdict.json")
        except json.JSONDecodeError as exc:
            raise LoopError("verdict.json is not valid JSON: {0}".format(exc))

        # Validate verdict structure.
        if not isinstance(verdict, dict):
            raise LoopError("verdict.json root must be a JSON object")
        if "outcome" not in verdict:
            raise LoopError("verdict.json missing 'outcome' field")
        if "candidate" not in verdict:
            raise LoopError("verdict.json missing 'candidate' field")
        if "reasoning" not in verdict:
            raise LoopError("verdict.json missing 'reasoning' field")

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

    finished_at = _utcnow_iso()

    # (i) Build the final run.json.
    run_log = {
        "task_id": task_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "base_commit": base_commit,
        "workers": run_workers,
    }

    if candidates:
        run_log["review"] = {
            "exit_code": review_exit_code,
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

    lines = [brief_text]
    lines.append("")
    lines.append("## Candidates")
    lines.append("")

    for candidate in candidates:
        label = candidate["label"]
        diff_path = "candidates/{0}.diff".format(label)
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
    lines.append("## Verdict")
    lines.append("")
    lines.append("Write .farnsworth/{0}/verdict.json with schema:".format(
        os.path.basename(artifact_dir)
    ))
    lines.append("")
    lines.append('{"outcome": "adopt" | "synthesize" | "escalate",')
    lines.append(' "candidate": "A" | null,')
    lines.append(' "reasoning": "..."}')
    lines.append("")

    return "\n".join(lines)
