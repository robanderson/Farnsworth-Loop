"""Command-line interface for the Farnsworth Loop.

Usage::

    python3 -m farnsworth run <task-brief.md> [--config <path>]
    python3 -m farnsworth gate <task-id> [--config <path>]      # delegate mode
    python3 -m farnsworth finalize <task-id>                    # delegate mode
    python3 -m farnsworth report <task-id>
    python3 -m farnsworth clean <task-id> [--force]

Exit codes: 0 valid verdict, 1 no candidates passed the gate,
2 infrastructure/config error, 3 delegate dispatch prepared and awaiting
host-session subagents (after ``run`` and ``gate``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import delegate
from .config import Config, ConfigError, DEFAULT_CONFIG_NAME
from .gitutil import GitError, repo_toplevel
from .housekeeping import clean
from .loop import LoopError, run
from .report import summary_table


def build_parser():
    parser = argparse.ArgumentParser(
        prog="farnsworth",
        description="Farnsworth Loop -- single-task agent loop (M1 skeleton).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser(
        "run",
        help="run one task (subprocess dispatch runs end-to-end; delegate "
        "dispatch prepares worktrees + briefings and exits 3)",
    )
    run_p.add_argument("brief", metavar="task-brief.md", help="path to the task brief")
    run_p.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="path to config JSON (default: {0} in repo root)".format(
            DEFAULT_CONFIG_NAME
        ),
    )

    gate_p = sub.add_parser(
        "gate",
        help="delegate mode phase 2: gate worker worktrees, anonymize "
        "candidates, write the review briefing (exit 3: awaiting reviewer)",
    )
    gate_p.add_argument("task_id", metavar="task-id", help="e.g. task-042")
    gate_p.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="path to config JSON (default: {0} in repo root)".format(
            DEFAULT_CONFIG_NAME
        ),
    )

    finalize_p = sub.add_parser(
        "finalize",
        help="delegate mode phase 3: validate verdict.json, write "
        "run.json + summary.md",
    )
    finalize_p.add_argument("task_id", metavar="task-id", help="e.g. task-042")

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
    return parser


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
            cfg = Config.load(args.config)
            if cfg.mode == "delegate":
                ledger = delegate.prepare(args.brief, config_path=args.config)
                print(
                    "Prepared {0} for delegate dispatch (subscription-billed "
                    "subagents).".format(ledger["task_id"])
                )
                print("Spawn one subagent per worker, then run "
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
            run_log = run(args.brief, config_path=args.config)
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2

        _print_summary(run_log)

        review = run_log.get("review")
        if review is None:
            return 1
        else:
            return 0

    if args.command == "gate":
        try:
            ledger = delegate.gate(args.task_id, config_path=args.config)
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2
        for worker in ledger["workers"]:
            gate_info = worker["gate"]
            status = "PASS" if gate_info["passed"] else "FAIL"
            autopsies = "; ".join(
                r["autopsy"] for r in gate_info["results"] if r["exit_code"] != 0
            )
            print(
                "  {0}  {1}{2}".format(
                    worker["id"], status, "  ({0})".format(autopsies) if autopsies else ""
                )
            )
        if ledger["phase"] == "no-candidates":
            print("No candidates passed the gate; nothing to review.")
            return 1
        print(
            "Candidates ready. Spawn the reviewer subagent (model={0}) with "
            "{1}, then run 'farnsworth finalize {2}'.".format(
                ledger["reviewer_model"],
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
        for entry in report["skipped"]:
            print("skipped {0}: {1}".format(entry["path"], entry["reason"]))
        if not (
            report["removed_worktrees"]
            or report["removed_branches"]
            or report["skipped"]
        ):
            print("nothing to clean for {0}".format(args.task_id))
        # Exit code: 0 fully clean, 1 something was skipped.
        return 1 if report["skipped"] else 0

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
