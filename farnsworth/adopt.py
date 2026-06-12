"""Post-verdict adoption: merge the winner and install the distilled tips.

The stretch between a verdict and the next dispatch has been the loop's
most error-prone manual sequence: merge the adopted candidate's branch,
install the reviewer's ``code-tips.next.md`` as ``.code-tips.md``, route
any generalized lessons toward the seed pile, then sweep the worktrees.
Every step is mechanical, so the tool does them; the orchestrator's job
stays deriving the next task from the goal gap.

``adopt`` trusts only artifacts: the verdict comes from ``run.json`` (never
from an agent's claim), the merge target is the branch recorded for the
winning label, and the tips install is the file the reviewer actually
wrote. Untracked ``.farnsworth/`` artifacts in the main repo are expected
and do not block the merge; modified TRACKED files do.
"""

from __future__ import annotations

import json
import os
import shutil

from . import gitutil
from .loop import LoopError

# Section 6: the consolidation pass runs every N merged tasks. Nothing
# counted N before, which is why no consolidation has ever been triggered.
CONSOLIDATE_EVERY = 10


def _load_run_log(artifact_dir, task_id):
    run_json = os.path.join(artifact_dir, "run.json")
    try:
        with open(run_json, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise LoopError("no run log at {0}".format(run_json))
    except json.JSONDecodeError as exc:
        raise LoopError("{0} is not valid JSON: {1}".format(run_json, exc))


def _verdict_of(run_log):
    review = run_log.get("review")
    verdict = review.get("verdict") if isinstance(review, dict) else None
    if verdict is None:
        verdict = run_log.get("verdict")  # legacy manual-mode logs
    return verdict


def count_adopted(repo_root):
    """Count recorded tasks whose verdict was adopt (consolidation cadence)."""
    farnsworth_dir = os.path.join(repo_root, ".farnsworth")
    count = 0
    if not os.path.isdir(farnsworth_dir):
        return count
    for name in sorted(os.listdir(farnsworth_dir)):
        run_json = os.path.join(farnsworth_dir, name, "run.json")
        if not (name.startswith("task-") and os.path.exists(run_json)):
            continue
        try:
            with open(run_json, "r", encoding="utf-8") as fh:
                log = json.load(fh)
        except (OSError, ValueError):
            continue
        verdict = _verdict_of(log)
        if verdict and verdict.get("outcome") == "adopt":
            count += 1
    return count


def adopt(task_id, cwd=None):
    """Merge the adopted candidate and install the reviewer's tips.

    Returns a report dict::

        {"task_id": str, "candidate": label, "worker_id": str,
         "merged_branch": str, "tips_installed": bool,
         "seed_tips_pending": bool, "adopted_count": int,
         "consolidation_due": bool}

    Raises LoopError when there is no adopt verdict on record, the winning
    branch is gone, or tracked files are dirty.
    """
    cwd = cwd or os.getcwd()
    if not gitutil.is_git_repo(cwd):
        raise LoopError("not a git repository: {0}".format(cwd))
    repo_root = gitutil.main_repo_toplevel(cwd)
    artifact_dir = os.path.join(repo_root, ".farnsworth", task_id)

    run_log = _load_run_log(artifact_dir, task_id)
    verdict = _verdict_of(run_log)
    if verdict is None:
        raise LoopError("no verdict on record for {0}".format(task_id))
    if verdict.get("outcome") != "adopt":
        raise LoopError(
            "verdict for {0} is '{1}', not adopt; nothing to merge".format(
                task_id, verdict.get("outcome")
            )
        )
    label = verdict.get("candidate")
    winner = None
    for worker in run_log.get("workers", []):
        if worker.get("candidate_label") == label:
            winner = worker
            break
    if winner is None:
        raise LoopError(
            "run log names no worker for adopted candidate {0}".format(label)
        )
    branch = winner["branch"]
    if not gitutil.branch_exists(branch, repo_root):
        raise LoopError(
            "adopted branch {0} no longer exists (was it cleaned before "
            "adoption?)".format(branch)
        )
    if not gitutil.is_clean_tracked(repo_root):
        raise LoopError(
            "tracked files have uncommitted changes; commit or stash before adopting"
        )

    gitutil.merge_branch(
        branch,
        "{0}: adopt candidate {1}".format(task_id, label),
        repo_root,
    )

    tips_installed = False
    tips_next = os.path.join(artifact_dir, "code-tips.next.md")
    if os.path.exists(tips_next):
        shutil.copyfile(tips_next, os.path.join(repo_root, ".code-tips.md"))
        gitutil.commit_paths(
            [".code-tips.md"],
            "Good news, everyone! {0} lessons installed".format(task_id),
            repo_root,
        )
        tips_installed = True

    # Generalized lessons are routed to the seed pile by a human curator;
    # adopt only surfaces that there is something to route.
    seed_tips_pending = os.path.exists(
        os.path.join(artifact_dir, "seed-tips.next.md")
    )

    adopted_count = count_adopted(repo_root)
    return {
        "task_id": task_id,
        "candidate": label,
        "worker_id": winner["id"],
        "merged_branch": branch,
        "tips_installed": tips_installed,
        "seed_tips_pending": seed_tips_pending,
        "adopted_count": adopted_count,
        "consolidation_due": adopted_count > 0
        and adopted_count % CONSOLIDATE_EVERY == 0,
    }
