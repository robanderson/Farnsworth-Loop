"""Command-line interface for the Farnsworth Loop.

Usage::

    python3 -m farnsworth run <task-brief.md> [--config <path>]
    python3 -m farnsworth gate <task-id> [--config <path>]      # delegate mode
    python3 -m farnsworth finalize <task-id>                    # delegate mode
    python3 -m farnsworth preflight [--config <path>]
    python3 -m farnsworth adopt <task-id> [--clean]
    python3 -m farnsworth report <task-id>
    python3 -m farnsworth metrics [root ...]
    python3 -m farnsworth clean <task-id> [--force]
    python3 -m farnsworth done [--config <path>]

``done`` is the loop-termination probe (PRD Section 2.4): it runs the
goal's mechanical completion checks against the merged state, records the
result to ``.farnsworth/done-checks.json``, and exits 0 when the
mechanical half of the goal is complete (writing the attestation briefing
for the semantic half), 1 when the loop should keep cycling.

Exit codes for ``run``/``gate``/``finalize``: 0 valid verdict, 1 no
candidates passed the gate, 2 infrastructure/config error, 3 PHASE
BOUNDARY — the mechanical phase is complete and an agent phase is next
(after ``run``: spawn the coders; after ``gate``: spawn the judge). The
conductor at that boundary is the dynamic workflow script
(``.claude/workflows/farnsworth-task.js``) or a host session running the
skills. ``preflight``: 0 all checks pass, 1 any failed.

``run``, ``gate``, ``finalize``, and ``done`` accept ``--json``: emit the
phase's machine-readable record on stdout (the dispatch ledger, the gated
ledger, the run log, the done outcome) instead of human-oriented text, so
a workflow conductor's agents relay structured truth verbatim rather than
paraphrasing terminal output. Exit codes are identical in both modes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import delegate
from .adopt import adopt as adopt_task
from .config import Config, ConfigError, DEFAULT_CONFIG_NAME
from .gitutil import GitError, repo_toplevel
from .housekeeping import clean
from .loop import (
    LoopError,
    check_done,
    record_done_outcome,
    run,
    write_attestation_briefing,
)
from .metrics import collect_runs, metrics_report
from .preflight import preflight
from .report import summary_table


def _resolve_config(config_arg):
    """Resolve ``--config`` the same way for every subcommand.

    Relative paths anchor at the repo root (so subcommands agree no matter
    which subdirectory they run from), and an explicitly named file that
    does not exist is an error — a typo'd ``--config`` must never silently
    dispatch the built-in default fleet. Only the default location may fall
    back when absent.
    """
    path = config_arg
    if not os.path.isabs(path):
        try:
            path = os.path.join(repo_toplevel(os.getcwd()), path)
        except GitError:
            pass  # not in a repo; the command's own precondition reports it
    if config_arg != DEFAULT_CONFIG_NAME and not os.path.exists(path):
        raise ConfigError("config not found: {0}".format(path))
    return path


def _json_flag(subparser):
    subparser.add_argument(
        "--json",
        action="store_true",
        help="emit the phase's machine-readable record (for workflow "
        "conductors) instead of human-oriented output",
    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="farnsworth",
        description="Farnsworth Loop -- the mechanical trust layer: "
        "worktrees, gates, anonymized review, artifacts (conductors "
        "drive these phases; humans use them for replay and audit).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser(
        "run",
        help="run one task (subprocess dispatch runs end-to-end; delegate "
        "dispatch prepares worktrees + briefings and exits 3: phase "
        "boundary, coder agents next)",
    )
    run_p.add_argument("brief", metavar="task-brief.md", help="path to the task brief")
    run_p.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="path to config JSON (default: {0} in repo root)".format(
            DEFAULT_CONFIG_NAME
        ),
    )
    _json_flag(run_p)

    gate_p = sub.add_parser(
        "gate",
        help="delegate mode phase 2: gate worker worktrees, anonymize "
        "candidates, write the review briefing (exit 3: phase boundary, "
        "judge agent next)",
    )
    gate_p.add_argument("task_id", metavar="task-id", help="e.g. task-042")
    gate_p.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="path to config JSON (default: {0} in repo root)".format(
            DEFAULT_CONFIG_NAME
        ),
    )
    _json_flag(gate_p)

    finalize_p = sub.add_parser(
        "finalize",
        help="delegate mode phase 3: validate verdict.json, write "
        "run.json + summary.md",
    )
    finalize_p.add_argument("task_id", metavar="task-id", help="e.g. task-042")
    _json_flag(finalize_p)

    preflight_p = sub.add_parser(
        "preflight",
        help="canary the fleet config before a tournament: parse, clean "
        "tree, green gate at base, worker edit+commit capability",
    )
    preflight_p.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="path to config JSON (default: {0} in repo root)".format(
            DEFAULT_CONFIG_NAME
        ),
    )

    adopt_p = sub.add_parser(
        "adopt",
        help="merge the verdict's adopted candidate and install the "
        "reviewer's code-tips.next.md",
    )
    adopt_p.add_argument("task_id", metavar="task-id", help="e.g. task-042")
    adopt_p.add_argument(
        "--clean",
        action="store_true",
        help="also sweep the task's worktrees and branches after the merge",
    )

    metrics_p = sub.add_parser(
        "metrics",
        help="aggregate every run.json under the given roots into the "
        "cross-run metrics table (default: current repo)",
    )
    metrics_p.add_argument(
        "roots",
        metavar="root",
        nargs="*",
        default=["."],
        help="directories to scan for .farnsworth/task-*/run.json",
    )

    clean_p = sub.add_parser(
        "clean",
        help="remove leftover worktrees/branches of a task so it can re-run",
    )
    clean_p.add_argument("task_id", metavar="task-id", help="e.g. task-042")
    clean_p.add_argument(
        "--force",
        action="store_true",
        help="also remove worktrees with uncommitted changes",
    )

    report_p = sub.add_parser(
        "report",
        help="print the short what-happened table for a completed task",
    )
    report_p.add_argument("task_id", metavar="task-id", help="e.g. task-042")

    done_p = sub.add_parser(
        "done",
        help="run the goal's completion checks: exit 0 done, 1 keep looping",
    )
    done_p.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="path to config JSON (default: {0} in repo root)".format(
            DEFAULT_CONFIG_NAME
        ),
    )
    _json_flag(done_p)
    return parser


def _emit_json(payload):
    """Print one machine-readable JSON object on stdout (conductor mode)."""
    print(json.dumps(payload, indent=2))


def _print_summary(run_log):
    """Print the short what-happened table for the run."""
    print("")
    print(summary_table(run_log))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        # Exit code contract:
        # 0: valid verdict was produced (any outcome)
        # 1: no candidates passed gate (no review, review is null)
        # 2: infrastructure/config errors
        # 3: delegate mode — dispatch prepared, awaiting host-session agents
        try:
            config_path = _resolve_config(args.config)
            cfg = Config.load(config_path)
            if cfg.mode == "delegate":
                ledger = delegate.prepare(args.brief, config_path=config_path)
                if args.json:
                    _emit_json(ledger)
                    return 3
                print(
                    "Phase boundary: {0} prepared for delegation "
                    "(subscription-billed subagents).".format(
                        ledger["task_id"]
                    )
                )
                print("Spawn one farnsworth-coder subagent per worker (in "
                      "parallel; the farnsworth-task workflow scripts "
                      "this), then run "
                      "'farnsworth gate {0}':".format(ledger["task_id"]))
                print("")
                for worker in ledger["workers"]:
                    print(
                        "  {0}  model={1}  worktree={2}  briefing={3}".format(
                            worker["id"],
                            worker["model"],
                            worker["worktree"],
                            worker["briefing"],
                        )
                    )
                return 3
            run_log = run(args.brief, config_path=config_path)
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2

        if args.json:
            _emit_json(run_log)
        else:
            _print_summary(run_log)

        review = run_log.get("review")
        if review is None:
            return 1
        else:
            return 0

    if args.command == "gate":
        def _gate_progress(line):
            # In conductor mode stdout carries exactly one JSON object;
            # live progress still streams, on stderr.
            print(line, file=sys.stderr if args.json else sys.stdout, flush=True)

        try:
            ledger = delegate.gate(
                args.task_id,
                config_path=_resolve_config(args.config),
                progress=_gate_progress,
            )
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2
        if args.json:
            _emit_json(ledger)
            return 1 if ledger["phase"] == "no-candidates" else 3
        if ledger["phase"] == "no-candidates":
            print("No candidates passed the gate; nothing to review.")
            return 1
        print(
            "Phase boundary: candidates ready. Spawn the farnsworth-judge "
            "subagent (model={0}) pinned to the review environment {1}, "
            "prompted with {2}, then "
            "run 'farnsworth finalize {3}'.".format(
                ledger["reviewer_model"],
                ledger["review_env"],
                ledger["review_briefing"],
                args.task_id,
            )
        )
        return 3

    if args.command == "finalize":
        try:
            run_log = delegate.finalize(args.task_id)
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2
        if args.json:
            _emit_json(run_log)
        else:
            _print_summary(run_log)
        return 1 if run_log.get("review") is None else 0

    if args.command == "report":
        try:
            repo_root = repo_toplevel(os.getcwd())
        except GitError as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2
        run_json = os.path.join(repo_root, ".farnsworth", args.task_id, "run.json")
        try:
            with open(run_json, "r", encoding="utf-8") as fh:
                run_log = json.load(fh)
        except FileNotFoundError:
            print("error: no run log at {0}".format(run_json), file=sys.stderr)
            return 2
        except json.JSONDecodeError as exc:
            print(
                "error: {0} is not valid JSON: {1}".format(run_json, exc),
                file=sys.stderr,
            )
            return 2
        print(summary_table(run_log))
        return 0

    if args.command == "done":
        try:
            repo_root = repo_toplevel(os.getcwd())
            config = Config.load(_resolve_config(args.config))
        except (ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2
        if config.goal is None:
            print(
                "error: no goal configured -- add a \"goal\" entry with "
                "\"done\" checks to {0} (PRD Section 2.4)".format(args.config),
                file=sys.stderr,
            )
            return 2

        outcome = check_done(config.goal, repo_root)
        record_path = record_done_outcome(outcome, repo_root)
        briefing_path = None
        if outcome["passed"]:
            briefing_path = write_attestation_briefing(config.goal, repo_root)
        if args.json:
            _emit_json(
                {
                    "passed": outcome["passed"],
                    "results": outcome["results"],
                    "recorded": os.path.relpath(record_path, repo_root),
                    "attestation_briefing": (
                        os.path.relpath(briefing_path, repo_root)
                        if briefing_path
                        else None
                    ),
                }
            )
            return 0 if outcome["passed"] else 1
        for result in outcome["results"]:
            print(result["autopsy"])
        print("recorded: {0}".format(os.path.relpath(record_path, repo_root)))
        if outcome["passed"]:
            print("GOAL COMPLETE (mechanical half): all done checks pass.")
            print(
                "Dispatch the farnsworth-attestor subagent with {0} for "
                "the semantic half; "
                "exit DONE requires both (PRD Section 2.4).".format(
                    os.path.relpath(briefing_path, repo_root)
                )
            )
            return 0
        print("GOAL NOT MET: keep looping (dispatch the next task).")
        return 1

    if args.command == "preflight":
        try:
            outcome = preflight(config_path=_resolve_config(args.config))
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2
        for check in outcome["checks"]:
            print(
                "[{0}] {1}: {2}".format(
                    check["status"].upper(), check["name"], check["detail"]
                )
            )
        if outcome["passed"]:
            print("PREFLIGHT PASS: the fleet config is runnable.")
            return 0
        print("PREFLIGHT FAIL: fix the config before dispatching a tournament.")
        return 1

    if args.command == "adopt":
        try:
            result = adopt_task(args.task_id)
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2
        print(
            "merged {0} (candidate {1}, worker {2})".format(
                result["merged_branch"], result["candidate"], result["worker_id"]
            )
        )
        if result["tips_installed"]:
            print("installed code-tips.next.md as .code-tips.md (committed)")
        else:
            print("no code-tips.next.md on record; .code-tips.md unchanged")
        if result["seed_tips_pending"]:
            print(
                "seed-tips.next.md present: route its entries into the "
                "cross-project seed pile"
            )
        if result["consolidation_due"]:
            print(
                "{0} adopted tasks on record: the consolidation pass is due "
                "(PRD Section 6)".format(result["adopted_count"])
            )
        if args.clean:
            sweep = clean(args.task_id)
            for path in sweep["removed_worktrees"]:
                print("removed worktree {0}".format(path))
            for branch in sweep["removed_branches"]:
                print("removed branch {0}".format(branch))
            if sweep.get("removed_review_env"):
                print(
                    "removed review environment {0}".format(
                        sweep["removed_review_env"]
                    )
                )
            for entry in sweep["skipped"]:
                print("skipped {0}: {1}".format(entry["path"], entry["reason"]))
        return 0

    if args.command == "metrics":
        runs = collect_runs(args.roots)
        if not runs:
            print(
                "no run logs found under: {0}".format(", ".join(args.roots)),
                file=sys.stderr,
            )
            return 1
        print(metrics_report(runs))
        return 0

    if args.command == "clean":
        try:
            report = clean(args.task_id, force=args.force)
        except GitError as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2

        for path in report["removed_worktrees"]:
            print("removed worktree {0}".format(path))
        for branch in report["removed_branches"]:
            print("removed branch {0}".format(branch))
        if report.get("removed_review_env"):
            print(
                "removed review environment {0}".format(
                    report["removed_review_env"]
                )
            )
        for entry in report["skipped"]:
            print("skipped {0}: {1}".format(entry["path"], entry["reason"]))
        if not (
            report["removed_worktrees"]
            or report["removed_branches"]
            or report.get("removed_review_env")
            or report["skipped"]
        ):
            print("nothing to clean for {0}".format(args.task_id))
        # Exit code: 0 fully clean, 1 something was skipped.
        return 1 if report["skipped"] else 0

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
