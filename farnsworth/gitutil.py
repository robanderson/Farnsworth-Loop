"""Thin wrappers around the git CLI.

The Farnsworth Loop keeps all state file-based and inspectable; git is the
substrate. These helpers shell out to the system ``git`` binary rather than
depend on any third-party library (stdlib only, by contract).
"""

from __future__ import annotations

import os
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


def main_repo_toplevel(cwd):
    """Return the toplevel of the MAIN repository, even from a linked worktree.

    ``repo_toplevel`` resolves to the nearest working tree, which inside a
    linked worktree is the worktree itself — housekeeping that runs there
    would mistake the worktree for the main repo. The common git dir
    (``<main>/.git``) is shared by all worktrees, so its parent is the main
    working tree.
    """
    top = repo_toplevel(cwd)
    proc = run_git(["rev-parse", "--git-common-dir"], cwd)
    common = proc.stdout.strip()
    if not os.path.isabs(common):
        common = os.path.join(str(cwd), common)
    main = os.path.dirname(os.path.abspath(common))
    # When cwd is already in the main worktree, keep git's own toplevel
    # spelling: --git-common-dir may canonicalize symlinks (macOS /var ->
    # /private/var) where --show-toplevel does not, and downstream code
    # compares these paths against git worktree list output.
    if os.path.realpath(main) == os.path.realpath(top):
        return top
    return main


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


def diff_text(base_commit, worktree_abs):
    """Return the diff from base_commit to worktree-HEAD as a string."""
    proc = run_git(
        ["diff", "{0}..HEAD".format(base_commit)],
        worktree_abs,
    )
    return proc.stdout


def export_tree(commit, dest, repo_root):
    """Extract the tree of ``commit`` into the existing directory ``dest``.

    Uses ``git archive`` piped to ``tar``, so the result carries no ``.git``
    directory, no refs, and no worktree metadata -- the raw file tree only.
    """
    archive = subprocess.Popen(
        ["git", "archive", commit],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
    )
    tar = subprocess.run(
        ["tar", "-x", "-C", str(dest)],
        stdin=archive.stdout,
        capture_output=True,
    )
    archive.stdout.close()
    if archive.wait() != 0 or tar.returncode != 0:
        raise GitError(
            "exporting tree of {0} to {1} failed".format(commit, dest)
        )


def init_review_repo(path):
    """Turn ``path`` into a fresh single-commit git repo.

    The review environment needs git so the reviewer can ``git apply``
    candidate diffs and ``git reset --hard`` between candidates, but it must
    be a FRESH repo: a clone or linked worktree would carry worker-named
    branches that de-anonymize the field. Identity and signing are set
    repo-locally so commits succeed under any host git config.
    """
    run_git(["init", "-b", "main"], path)
    run_git(["config", "user.email", "reviewer@farnsworth.invalid"], path)
    run_git(["config", "user.name", "Farnsworth Review Environment"], path)
    run_git(["config", "commit.gpgsign", "false"], path)
    run_git(["add", "-A"], path)
    run_git(["commit", "-m", "review base"], path)


def write_diff(base_commit, worktree_abs, output_path, repo_root):
    """Write the diff from base_commit to worktree-HEAD into output_path.

    The diff is written relative to the repo root.
    """
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(diff_text(base_commit, worktree_abs))


def snapshot_uncommitted_diff(worktree_abs):
    """Return uncommitted work (staged, unstaged, and untracked) as a diff.

    Stages everything, diffs the index against HEAD, then unstages. Used to
    archive a worker's leftovers when its branch carries no commits — the
    candidate diff would be empty and ``clean --force`` would otherwise
    destroy the only copy of whatever the worker actually did.
    """
    run_git(["add", "-A"], worktree_abs)
    proc = run_git(["diff", "--cached"], worktree_abs)
    run_git(["reset", "-q"], worktree_abs)
    return proc.stdout
