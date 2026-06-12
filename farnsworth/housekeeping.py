"""Housekeeping for tournament leftovers.

A loop run leaves one worktree and one branch per worker
(``../<task-id>-<worker-id>``) in place for manual inspection and merge.
A hung or aborted run leaves the same debris, and a re-dispatch of the
same task id then fails the branch/worktree pre-checks. ``clean`` sweeps
both so the task can run again.

Candidate diffs are archived under ``.farnsworth/<task-id>/candidates/``
by the run itself, so removing worktrees and branches loses no evidence;
the only guarded case is a worktree with uncommitted changes, which is
skipped unless ``force`` is set.
"""

from __future__ import annotations

import os

from . import gitutil


def clean(task_id, cwd=None, force=False):
    """Remove worktrees and branches left behind by ``task_id``.

    Returns a report dict::

        {"task_id": str,
         "removed_worktrees": [path, ...],
         "removed_branches": [name, ...],
         "skipped": [{"path": str, "reason": str}, ...]}

    Worktrees with uncommitted changes are skipped (with a reason) unless
    ``force`` is true. Branches matching ``<task-id>-*`` are deleted once
    their worktree is gone. Raises GitError on infrastructure failures.
    """
    cwd = cwd or os.getcwd()
    if not gitutil.is_git_repo(cwd):
        raise gitutil.GitError("not a git repository: {0}".format(cwd))
    repo_root = gitutil.repo_toplevel(cwd)

    prefix = task_id + "-"
    report = {
        "task_id": task_id,
        "removed_worktrees": [],
        "removed_branches": [],
        "skipped": [],
    }

    for path in gitutil.list_worktrees(repo_root):
        if os.path.realpath(path) == os.path.realpath(repo_root):
            continue  # never touch the main worktree
        if not os.path.basename(path).startswith(prefix):
            continue
        if not force and not gitutil.is_clean_worktree(path):
            report["skipped"].append(
                {"path": path, "reason": "uncommitted changes (use --force)"}
            )
            continue
        gitutil.remove_worktree(path, repo_root, force=force)
        report["removed_worktrees"].append(path)

    skipped_names = {
        os.path.basename(entry["path"]) for entry in report["skipped"]
    }
    for branch in gitutil.list_branches(prefix + "*", repo_root):
        if branch in skipped_names:
            continue  # its worktree survived; keep the branch with it
        gitutil.delete_branch(branch, repo_root)
        report["removed_branches"].append(branch)

    return report
