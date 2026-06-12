"""Delegate dispatch: workers and reviewer as host-session subagents.

Subprocess dispatch (``claude -p``) bills to API / Agent-SDK credit. When a
worker runs an Anthropic model, the cheaper path is standard agent
delegation: the Claude Code session that orchestrates the loop spawns one
subagent per worker, which draws on the subscription. A Python CLI cannot
spawn those subagents itself — delegation is a capability of the host
session — so the loop becomes PHASED around the two points where agents do
the work. Every mechanical phase stays in the CLI; only dispatch is handed
to the session:

  1. ``farnsworth run <brief>``   (delegate config) -> worktrees, per-worker
     briefing files, dispatch ledger. Exit 3: awaiting worker delegation.
  2. The host session spawns one subagent per briefing (model per the
     ledger, pinned to its worktree, blind to the other workers).
  3. ``farnsworth gate <task-id>`` -> commit-as-artifact check, mechanical
     gate, anonymization, candidate diffs, review briefing (with the full
     reviewer protocol). Exit 3: awaiting reviewer delegation. Exit 1: no
     candidates.
  4. The host session spawns the reviewer subagent with the review
     briefing.
  5. ``farnsworth finalize <task-id>`` -> validate verdict.json, write
     run.json + summary.md. Exit 0.

The phase boundary remains the artifact, never the agent (PRD 4.3):
``gate`` trusts only commits in worktrees, ``finalize`` trusts only a
validating verdict.json. Hung, duplicated, or vanished subagents are
therefore harmless: re-spawn and re-run the phase.
"""

from __future__ import annotations

import json
import os
import random
import shutil

from . import gitutil, report
from .config import Config
from .divergence import divergence
from .loop import (
    LoopError,
    WORKER_PREAMBLE,
    _construct_review_env,
    _copy_back_review_artifacts,
    _run_gate,
    _utcnow_iso,
    build_briefing,
    build_review_briefing,
    focus_briefing,
    hygiene_violations,
    load_and_validate_verdict,
    protected_paths,
    review_env_path,
    task_id_from_brief,
)

DISPATCH_FILE = "dispatch.json"

REVIEWER_PREAMBLE = """\
You are the REVIEWER in a Farnsworth Loop tournament ({date}). You have
been started inside a constructed, anonymized review environment (a fresh
single-commit repo: the project tree at the base commit plus the labeled
candidate diffs and gate notes — nothing else). Work ONLY in this
directory. Follow the Review Protocol in the briefing below exactly,
writing every artifact at the path it names; the orchestrator copies your
artifacts back to the repo of record and installs code-tips.next.md after
the merge. Use `git apply` to try a candidate and `git reset --hard &&
git clean -fd -e .farnsworth` to return to base between candidates (reset
alone leaves a candidate's newly created files behind as untracked debris;
the exclusion protects your notes); never `git add` or `git commit`.

{briefing}
"""


def _artifact_dir(repo_root, task_id):
    return os.path.join(repo_root, ".farnsworth", task_id)


def _ledger_path(repo_root, task_id):
    return os.path.join(_artifact_dir(repo_root, task_id), DISPATCH_FILE)


def _load_ledger(repo_root, task_id):
    path = _ledger_path(repo_root, task_id)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise LoopError(
            "no dispatch ledger at {0}; run 'farnsworth run <brief>' first".format(
                path
            )
        )
    except json.JSONDecodeError as exc:
        raise LoopError("dispatch ledger is not valid JSON: {0}".format(exc))


def _save_ledger(repo_root, task_id, ledger):
    with open(_ledger_path(repo_root, task_id), "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2)
        fh.write("\n")


def prepare(brief_path, config_path=None, cwd=None):
    """Phase 1: worktrees, per-worker briefing files, dispatch ledger.

    Returns the ledger dict. The host session then spawns one subagent per
    worker entry (its ``model``, pinned to its ``worktree``, prompted with
    the contents of its ``briefing`` file).
    """
    cwd = cwd or os.getcwd()
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
    if config.mode != "delegate":
        raise LoopError(
            "config uses subprocess dispatch; plain 'farnsworth run' handles it"
        )

    task_id = task_id_from_brief(brief_path)
    parent = os.path.dirname(repo_root)
    base_commit = gitutil.head_commit(repo_root)

    # Collision pre-checks for ALL workers before creating anything. The
    # review environment's path is claimed now too: discovering the
    # collision only after the agents have run would waste the whole field.
    if os.path.exists(review_env_path(task_id, repo_root)):
        raise LoopError(
            "review environment path already exists: {0}".format(
                review_env_path(task_id, repo_root)
            )
        )
    for worker_spec in config.workers:
        branch = "{0}-{1}".format(task_id, worker_spec["id"])
        worktree_abs = os.path.join(parent, branch)
        if gitutil.branch_exists(branch, repo_root):
            raise LoopError("branch already exists: {0}".format(branch))
        if os.path.exists(worktree_abs):
            raise LoopError(
                "worktree path already exists: {0}".format(worktree_abs)
            )

    artifact_dir = _artifact_dir(repo_root, task_id)
    briefings_dir = os.path.join(artifact_dir, "briefings")
    os.makedirs(briefings_dir, exist_ok=True)

    briefing = build_briefing(repo_root, brief_path)

    ledger_workers = []
    for worker_spec in config.workers:
        worker_id = worker_spec["id"]
        branch = "{0}-{1}".format(task_id, worker_id)
        worktree_abs = os.path.join(parent, branch)
        gitutil.add_worktree(worktree_abs, branch, repo_root)

        briefing_path = os.path.join(briefings_dir, worker_id + ".md")
        with open(briefing_path, "w", encoding="utf-8") as fh:
            fh.write(
                WORKER_PREAMBLE.format(
                    worker_id=worker_id,
                    branch=branch,
                    briefing=focus_briefing(briefing, worker_spec.get("focus")),
                )
            )

        ledger_workers.append(
            {
                "id": worker_id,
                "model": worker_spec["model"],
                "branch": branch,
                "worktree": "../{0}".format(branch),
                "worktree_abs": worktree_abs,
                "briefing": os.path.relpath(briefing_path, repo_root),
                "focus": worker_spec.get("focus"),
                "deadline_seconds": worker_spec.get("timeout"),
                "status": "dispatched",
            }
        )

    ledger = {
        "task_id": task_id,
        "mode": "delegate",
        "phase": "awaiting-workers",
        "brief_path": os.path.relpath(
            os.path.abspath(brief_path), repo_root
        ),
        "base_commit": base_commit,
        "dispatched_at": _utcnow_iso(),
        "reviewer_model": config.reviewer["model"] if config.reviewer else None,
        "reviewer_deadline_seconds": (
            config.reviewer.get("timeout") if config.reviewer else None
        ),
        "workers": ledger_workers,
    }
    _save_ledger(repo_root, task_id, ledger)
    return ledger


def gate(task_id, config_path=None, cwd=None):
    """Phase 3: enforce commits-as-artifact, gate, anonymize, review briefing.

    Returns the updated ledger. Idempotent: re-running re-derives gate
    results and candidate diffs from the worktrees.
    """
    cwd = cwd or os.getcwd()
    if not gitutil.is_git_repo(cwd):
        raise LoopError("not a git repository: {0}".format(cwd))
    repo_root = gitutil.main_repo_toplevel(cwd)

    config = Config.load(config_path)
    ledger = _load_ledger(repo_root, task_id)
    artifact_dir = _artifact_dir(repo_root, task_id)
    base_commit = ledger["base_commit"]

    protected = protected_paths(
        repo_root, os.path.join(repo_root, ledger["brief_path"]), config_path
    )
    candidates = []
    failed_workers = []
    for worker in ledger["workers"]:
        worktree_abs = worker.get("worktree_abs") or os.path.join(
            os.path.dirname(repo_root), os.path.basename(worker["worktree"])
        )
        if not os.path.isdir(worktree_abs):
            raise LoopError(
                "worktree missing for {0}: {1} (was it cleaned?)".format(
                    worker["id"], worktree_abs
                )
            )

        gate_passed, gate_results = _run_gate(config.gate, worktree_abs)

        # PRD 4.3: commits are the phase artifact. Same enforcement as
        # subprocess mode — a no-commit worker is not a candidate, and its
        # uncommitted leftovers are archived for the forensic record.
        if (
            gate_passed
            and gitutil.head_commit(worktree_abs) == base_commit
        ):
            uncommitted = gitutil.snapshot_uncommitted_diff(worktree_abs)
            autopsy = "commits: no commits on branch"
            if uncommitted.strip():
                with open(
                    os.path.join(
                        artifact_dir,
                        "{0}-uncommitted.diff".format(worker["id"]),
                    ),
                    "w",
                    encoding="utf-8",
                ) as fh:
                    fh.write(uncommitted)
                autopsy += " (uncommitted work archived)"
            gate_passed = False
            gate_results.append(
                {"name": "commits", "exit_code": 1, "autopsy": autopsy}
            )

        if gate_passed:
            # Hygiene contract, enforced mechanically (same rule as
            # subprocess dispatch): tips file, fleet config, brief.
            violations = hygiene_violations(base_commit, worktree_abs, protected)
            if violations:
                gate_passed = False
                gate_results.append(
                    {
                        "name": "hygiene",
                        "exit_code": 1,
                        "autopsy": "hygiene: modified protected file(s): "
                        + ", ".join(violations),
                    }
                )

        worker["gate"] = {"passed": gate_passed, "results": gate_results}
        worker["status"] = "gated"
        if gate_passed:
            candidates.append(
                {"worker_id": worker["id"], "worktree_abs": worktree_abs}
            )
        else:
            failed_workers.append(
                {"worker_id": worker["id"], "gate_results": gate_results}
            )

    # Anonymize: shuffle, drop empty diffs, assign labels, write diffs.
    # Re-gating relabels from scratch, so first sweep any diffs a previous
    # gate run wrote: a stale label whose worker has since failed would
    # otherwise survive on disk and reach the reviewer.
    candidates_dir = os.path.join(artifact_dir, "candidates")
    if os.path.isdir(candidates_dir):
        shutil.rmtree(candidates_dir)
    random.shuffle(candidates)
    label_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    label_to_worker_id = {}
    labeled = []
    workers_by_id = {w["id"]: w for w in ledger["workers"]}
    for candidate in candidates:
        text = gitutil.diff_text(base_commit, candidate["worktree_abs"])
        if not text.strip():
            worker = workers_by_id[candidate["worker_id"]]
            worker["gate"]["passed"] = False
            worker["gate"]["results"].append(
                {
                    "name": "candidate",
                    "exit_code": 1,
                    "autopsy": "candidate: empty diff against base",
                }
            )
            failed_workers.append(
                {
                    "worker_id": candidate["worker_id"],
                    "gate_results": worker["gate"]["results"],
                }
            )
            continue
        label = label_chars[len(labeled)]
        label_to_worker_id[label] = candidate["worker_id"]
        candidate["label"] = label
        candidate["diff_text"] = text
        diff_path = os.path.join(
            artifact_dir, "candidates", "{0}.diff".format(label)
        )
        os.makedirs(os.path.dirname(diff_path), exist_ok=True)
        with open(diff_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        labeled.append(candidate)
    candidates = labeled

    # Content-based field divergence, recorded for M4 calibration.
    ledger["divergence"] = divergence([c["diff_text"] for c in candidates])

    for worker in ledger["workers"]:
        worker["candidate_label"] = None
        for label, wid in label_to_worker_id.items():
            if wid == worker["id"]:
                worker["candidate_label"] = label

    # The label mapping is sealed in the ledger until finalize unseals it
    # into run.json; the reviewer never sees the ledger — it works in a
    # constructed environment with no attribution surfaces at all.
    if candidates:
        if ledger.get("reviewer_model") is None:
            raise LoopError(
                "candidates passed gate but no reviewer configured in config"
            )
        review_env = review_env_path(task_id, repo_root)
        if not os.path.isdir(review_env):
            _construct_review_env(
                review_env, base_commit, repo_root, artifact_dir, task_id
            )
        else:
            # The env was built by an earlier gate run; this run relabeled
            # the field, so refresh the served diffs or the briefing and the
            # environment disagree (the word-garden-5 briefed-path bug class,
            # from the other side).
            env_candidates = os.path.join(
                review_env, ".farnsworth", task_id, "candidates"
            )
            if os.path.isdir(env_candidates):
                shutil.rmtree(env_candidates)
            shutil.copytree(candidates_dir, env_candidates)
        focus_directives = sorted(
            {w.get("focus") for w in ledger["workers"] if w.get("focus")}
        )
        brief_abs = os.path.join(repo_root, ledger["brief_path"])
        review_body = build_review_briefing(
            brief_abs,
            repo_root,
            artifact_dir,
            candidates,
            failed_workers,
            focus_directives=focus_directives,
        )
        review_briefing = REVIEWER_PREAMBLE.format(
            date=_utcnow_iso()[:10],
            briefing=review_body,
        )
        review_path = os.path.join(artifact_dir, "review-briefing.md")
        with open(review_path, "w", encoding="utf-8") as fh:
            fh.write(review_briefing)
        ledger["phase"] = "awaiting-review"
        ledger["review_briefing"] = os.path.relpath(review_path, repo_root)
        ledger["review_env"] = review_env
    else:
        ledger["phase"] = "no-candidates"

    ledger["gated_at"] = _utcnow_iso()
    _save_ledger(repo_root, task_id, ledger)
    return ledger


def finalize(task_id, cwd=None):
    """Phase 5: validate verdict.json, write run.json and summary.md.

    Returns the run-log dict. Idempotent.
    """
    cwd = cwd or os.getcwd()
    if not gitutil.is_git_repo(cwd):
        raise LoopError("not a git repository: {0}".format(cwd))
    repo_root = gitutil.main_repo_toplevel(cwd)

    ledger = _load_ledger(repo_root, task_id)
    artifact_dir = _artifact_dir(repo_root, task_id)

    if ledger["phase"] == "awaiting-workers":
        raise LoopError(
            "task {0} has not been gated; run 'farnsworth gate {0}' first".format(
                task_id
            )
        )

    label_to_worker_id = {
        w["candidate_label"]: w["id"]
        for w in ledger["workers"]
        if w.get("candidate_label")
    }

    run_workers = []
    for worker in ledger["workers"]:
        run_workers.append(
            {
                "id": worker["id"],
                "model": worker["model"],
                "branch": worker["branch"],
                "worktree": worker["worktree"],
                "exit_code": None,  # agents are managed by the host session
                "focus": worker.get("focus"),
                # Delegate dispatch has no per-worker cost stream; the
                # orchestrator may record what the host session reports by
                # writing cost_usd into the ledger's worker entries.
                "cost_usd": worker.get("cost_usd"),
                "gate": worker["gate"],
                "candidate_label": worker.get("candidate_label"),
            }
        )

    run_log = {
        "task_id": task_id,
        "started_at": ledger["dispatched_at"],
        "finished_at": _utcnow_iso(),
        "base_commit": ledger["base_commit"],
        "mode": "delegate",
        "divergence": ledger.get("divergence"),
        "workers": run_workers,
    }

    if ledger["phase"] == "no-candidates":
        run_log["review"] = None
    else:
        # The reviewer subagent wrote its artifacts inside the constructed
        # review environment; bring them back to the repo of record before
        # the verdict is parsed. Idempotent on re-runs.
        review_env = ledger.get("review_env") or review_env_path(
            task_id, repo_root
        )
        if os.path.isdir(review_env):
            _copy_back_review_artifacts(review_env, artifact_dir, task_id)
        verdict = load_and_validate_verdict(artifact_dir, label_to_worker_id)
        run_log["review"] = {
            "exit_code": None,
            "cost_usd": ledger.get("review_cost_usd"),
            "verdict": verdict,
        }

    with open(
        os.path.join(artifact_dir, "run.json"), "w", encoding="utf-8"
    ) as fh:
        json.dump(run_log, fh, indent=2)
        fh.write("\n")
    with open(
        os.path.join(artifact_dir, "summary.md"), "w", encoding="utf-8"
    ) as fh:
        fh.write(report.summary_table(run_log))

    ledger["phase"] = "finalized"
    _save_ledger(repo_root, task_id, ledger)
    return run_log
