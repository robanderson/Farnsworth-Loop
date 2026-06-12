"""Pre-flight canary: prove the fleet config is runnable before a tournament.

A dispatch config is a runtime contract, and the recorded ones have a track
record of never having executed: word-garden-4's pre-flight found the fleet
config 100% fatal twice over (`--bare` kills OAuth; headless acceptEdits
denies all Bash), and word-garden-5 found auth turning intermittent
mid-project ("canary every phase"). This module mechanizes the canary the
PRD queued there.

Checks, in order:

  1. config     -- the config parses (a typo'd path is already an error
                   at the CLI layer, never a silent default).
  2. git        -- the CWD is a clean git repo (what ``run`` requires).
  3. gate-at-base -- every gate command exits 0 against the merged state.
                   A red base gates every candidate against noise.
  4. goal       -- informational: whether a termination contract exists
                   (a loop without one "either stops early or never").
  5. canary-<worker> -- subprocess mode only: each worker command runs in
                   a scratch worktree with a trivial prompt and must
                   demonstrate edit + Bash + commit (the two observed
                   fatality classes). Delegate-mode fleets are spawned by
                   the host session, which the CLI cannot canary; that
                   check is reported as a skip with instructions.

Exit contract (CLI): 0 all checks pass, 1 any check failed, 2 infra error.
"""

from __future__ import annotations

import os
import subprocess

from . import gitutil
from .config import Config
from .loop import _substitute_prompt

CANARY_TIMEOUT_SECONDS = 300

CANARY_PROMPT = (
    "PREFLIGHT CANARY: create a file named canary.txt containing the single "
    "line OK, run python3 -c \"print('canary')\", then commit canary.txt to "
    "the current branch with the commit message 'preflight canary'. "
    "Do nothing else."
)


def _check(name, status, detail):
    return {"name": name, "status": status, "detail": detail}


def _sweep_canary_debris(branch, worktree_abs, repo_root):
    """Remove a canary worktree/branch, before and after the canary runs."""
    if os.path.isdir(worktree_abs):
        try:
            gitutil.remove_worktree(worktree_abs, repo_root, force=True)
        except gitutil.GitError:
            pass
    if gitutil.branch_exists(branch, repo_root):
        try:
            gitutil.delete_branch(branch, repo_root)
        except gitutil.GitError:
            pass


def _canary_worker(worker, repo_root):
    """Run one worker command against the canary contract.

    Pass requires the two capabilities whose absence killed real fleets:
    the worker edited the tree (canary.txt exists) AND committed (HEAD moved
    off base). Returns a check dict; always sweeps its debris.
    """
    worker_id = worker["id"]
    name = "canary-{0}".format(worker_id)
    branch = "preflight-{0}".format(worker_id)
    worktree_abs = os.path.join(os.path.dirname(repo_root), branch)

    _sweep_canary_debris(branch, worktree_abs, repo_root)
    try:
        gitutil.add_worktree(worktree_abs, branch, repo_root)
    except gitutil.GitError as exc:
        return _check(name, "fail", "could not create canary worktree: {0}".format(exc))

    base = gitutil.head_commit(repo_root)
    command = _substitute_prompt(worker["command"], CANARY_PROMPT)
    timeout = worker.get("timeout") or CANARY_TIMEOUT_SECONDS
    try:
        proc = subprocess.run(
            command,
            cwd=worktree_abs,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        edited = os.path.exists(os.path.join(worktree_abs, "canary.txt"))
        committed = gitutil.head_commit(worktree_abs) != base
        if edited and committed:
            return _check(
                name,
                "pass",
                "edit + commit verified (exit {0})".format(proc.returncode),
            )
        missing = []
        if not edited:
            missing.append("no canary.txt (edit/Bash denied?)")
        if not committed:
            missing.append("no commit on branch (git denied or auth failed?)")
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        detail = "exit {0}: {1}".format(proc.returncode, "; ".join(missing))
        if tail:
            detail += " | " + tail[-1].strip()
        return _check(name, "fail", detail)
    except subprocess.TimeoutExpired:
        return _check(name, "fail", "canary timed out after {0}s".format(timeout))
    finally:
        _sweep_canary_debris(branch, worktree_abs, repo_root)


def preflight(config_path=None, cwd=None):
    """Run all pre-flight checks; returns {"passed": bool, "checks": [...]}."""
    cwd = cwd or os.getcwd()
    checks = []

    config = Config.load(config_path)
    checks.append(
        _check(
            "config",
            "pass",
            "{0} dispatch, {1} worker(s), {2} gate check(s)".format(
                config.mode, len(config.workers), len(config.gate)
            ),
        )
    )

    if not gitutil.is_git_repo(cwd):
        checks.append(_check("git", "fail", "not a git repository: {0}".format(cwd)))
        return {"passed": False, "checks": checks}
    repo_root = gitutil.repo_toplevel(cwd)
    if gitutil.is_clean_worktree(repo_root):
        checks.append(_check("git", "pass", "clean working tree"))
    else:
        checks.append(
            _check("git", "fail", "working tree is not clean; run would refuse")
        )

    failing = []
    for entry in config.gate:
        proc = subprocess.run(
            entry["command"], cwd=repo_root, capture_output=True, text=True
        )
        if proc.returncode != 0:
            failing.append("{0}: exit {1}".format(entry["name"], proc.returncode))
    if failing:
        checks.append(
            _check(
                "gate-at-base",
                "fail",
                "gate is red on the merged state ({0}); every candidate "
                "would gate against noise".format("; ".join(failing)),
            )
        )
    elif config.gate:
        checks.append(
            _check("gate-at-base", "pass", "all gate checks green on the merged state")
        )
    else:
        checks.append(_check("gate-at-base", "skip", "no gate configured"))

    if config.goal:
        checks.append(
            _check(
                "goal",
                "pass",
                "termination contract present ({0} done check(s))".format(
                    len(config.goal["done"])
                ),
            )
        )
    else:
        checks.append(
            _check(
                "goal",
                "skip",
                "no goal configured: 'farnsworth done' will exit 2 "
                "(a loop without a termination contract stops early or never)",
            )
        )

    if config.mode == "delegate":
        checks.append(
            _check(
                "canary",
                "skip",
                "delegate dispatch: the host session spawns the subagents; "
                "canary one cheap subagent manually before the tournament",
            )
        )
    else:
        for worker in config.workers:
            checks.append(_canary_worker(worker, repo_root))

    passed = all(check["status"] != "fail" for check in checks)
    return {"passed": passed, "checks": checks}
