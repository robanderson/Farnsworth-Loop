"""Thin wrappers around the git CLI.

The Farnsworth Loop keeps all state file-based and inspectable; git is the
substrate. These helpers shell out to the system ``git`` binary rather than
depend on any third-party library (stdlib only, by contract).
"""

from __future__ import annotations

import subprocess


class GitError(RuntimeError):
    """Raised when a git invocation fails or a precondition is violated."""


def run_git(args, cwd, check=True):
    """Run ``git <args>`` in ``cwd`` and return the CompletedProcess.

    ``args`` is a list of arguments after the ``git`` program name. Output is
    captured as text. When ``check`` is true a nonzero exit raises GitError.
    """
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise GitError(
            "git {0} failed (exit {1}): {2}".format(
                " ".join(args), proc.returncode, proc.stderr.strip()
            )
        )
    return proc


def is_git_repo(cwd):
    """Return True if ``cwd`` is inside a git working tree."""
    proc = run_git(["rev-parse", "--is-inside-work-tree"], cwd, check=False)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def repo_toplevel(cwd):
    """Return the absolute path to the working tree root."""
    proc = run_git(["rev-parse", "--show-toplevel"], cwd)
    return proc.stdout.strip()


def head_commit(cwd):
    """Return the full SHA of HEAD."""
    proc = run_git(["rev-parse", "HEAD"], cwd)
    return proc.stdout.strip()


def is_clean_worktree(cwd):
    """Return True if the working tree has no staged or unstaged changes.

    Untracked files are reported by ``git status --porcelain`` as well, so a
    truly clean tree yields empty output.
    """
    proc = run_git(["status", "--porcelain"], cwd)
    return proc.stdout.strip() == ""


def branch_exists(branch, cwd):
    """Return True if a local branch named ``branch`` already exists."""
    proc = run_git(
        ["show-ref", "--verify", "--quiet", "refs/heads/" + branch],
        cwd,
        check=False,
    )
    return proc.returncode == 0


def add_worktree(path, branch, cwd):
    """Create a new worktree at ``path`` on a new branch ``branch``."""
    run_git(["worktree", "add", str(path), "-b", branch], cwd)


def list_worktrees(cwd):
    """Return the absolute paths of all worktrees of the repo at ``cwd``.

    The first entry git reports is the main worktree; callers that only
    want linked worktrees should filter it out by comparing to the repo
    toplevel.
    """
    proc = run_git(["worktree", "list", "--porcelain"], cwd)
    paths = []
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            paths.append(line[len("worktree "):])
    return paths


def remove_worktree(path, cwd, force=False):
    """Remove the worktree at ``path``. ``force`` discards local changes."""
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(str(path))
    run_git(args, cwd)


def list_branches(pattern, cwd):
    """Return local branch names matching the glob ``pattern``."""
    proc = run_git(
        ["branch", "--list", "--format=%(refname:short)", pattern], cwd
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def delete_branch(branch, cwd):
    """Delete the local branch ``branch`` even if unmerged."""
    run_git(["branch", "-D", branch], cwd)


def write_diff(base_commit, worktree_abs, output_path, repo_root):
    """Write the diff from base_commit to worktree-HEAD into output_path.

    The diff is written relative to the repo root.
    """
    proc = run_git(
        ["diff", "{0}..HEAD".format(base_commit)],
        worktree_abs,
    )
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(proc.stdout)
