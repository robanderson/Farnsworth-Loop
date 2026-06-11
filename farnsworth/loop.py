"""The single-worker loop body (Milestone M1, Skeleton).

One invocation:

  1. Verify the CWD is a clean git repo.
  2. Create a worktree ``../<task-id>-w1`` on branch ``<task-id>-w1``.
  3. Run the worker command in the worktree, capturing stdout/stderr/exit.
  4. Run each gate command, in order, in the worktree.
  5. Write ``.farnsworth/<task-id>/run.json`` in the MAIN repo.
  6. Leave the worktree in place; print a summary.

No review, no tips writing, no parallelism. This proves the plumbing.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess

from . import gitutil
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


def _substitute_prompt(command, prompt):
    """Replace any ``{prompt}`` token within each argv element with ``prompt``."""
    return [arg.replace("{prompt}", prompt) for arg in command]


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


def run(brief_path, config_path=None, cwd=None):
    """Execute the single-worker loop body.

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
    branch = "{0}-w1".format(task_id)
    worktree_rel = "../{0}-w1".format(task_id)
    parent = os.path.dirname(repo_root)
    worktree_abs = os.path.join(parent, "{0}-w1".format(task_id))

    base_commit = gitutil.head_commit(repo_root)
    started_at = _utcnow_iso()

    # (b) Create worktree on a fresh branch; fail clearly on collisions.
    if gitutil.branch_exists(branch, repo_root):
        raise LoopError("branch already exists: {0}".format(branch))
    if os.path.exists(worktree_abs):
        raise LoopError("worktree path already exists: {0}".format(worktree_abs))

    briefing = build_briefing(repo_root, brief_path)
    gitutil.add_worktree(worktree_abs, branch, repo_root)

    # Per-task artifact directory lives in the MAIN repo.
    artifact_dir = os.path.join(repo_root, ".farnsworth", task_id)
    os.makedirs(artifact_dir, exist_ok=True)

    # (c) Run the worker in the worktree.
    worker_command = _substitute_prompt(config.worker_command, briefing)
    worker_proc = subprocess.run(
        worker_command,
        cwd=worktree_abs,
        capture_output=True,
        text=True,
    )

    stdout_name = "w1.stdout"
    stderr_name = "w1.stderr"
    with open(os.path.join(artifact_dir, stdout_name), "w", encoding="utf-8") as fh:
        fh.write(worker_proc.stdout or "")
    with open(os.path.join(artifact_dir, stderr_name), "w", encoding="utf-8") as fh:
        fh.write(worker_proc.stderr or "")

    # (d) Run the mechanical gate.
    gate_passed, gate_results = _run_gate(config.gate, worktree_abs)

    finished_at = _utcnow_iso()

    run_log = {
        "task_id": task_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "base_commit": base_commit,
        "workers": [
            {
                "id": "w1",
                "branch": branch,
                "worktree": worktree_rel,
                "exit_code": worker_proc.returncode,
                "stdout_file": stdout_name,
                "gate": {"passed": gate_passed, "results": gate_results},
            }
        ],
    }

    # (e) Write run.json in the MAIN repo.
    with open(os.path.join(artifact_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(run_log, fh, indent=2)
        fh.write("\n")

    return run_log
