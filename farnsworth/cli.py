"""Command-line interface for the Farnsworth Loop.

Usage::

    python3 -m farnsworth run <task-brief.md> [--config <path>]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .config import ConfigError, DEFAULT_CONFIG_NAME
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

    run_p = sub.add_parser("run", help="run one task with one worker")
    run_p.add_argument("brief", metavar="task-brief.md", help="path to the task brief")
    run_p.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="path to config JSON (default: {0} in repo root)".format(
            DEFAULT_CONFIG_NAME
        ),
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
    return parser


def _print_summary(run_log):
    """Print the short what-happened table for the run."""
    print("")
    print(summary_table(run_log))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            run_log = run(args.brief, config_path=args.config)
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2

        _print_summary(run_log)

        # Exit code logic:
        # 0: valid verdict was produced (any outcome)
        # 1: no candidates passed gate (no review, review is null)
        # 2: infrastructure/config errors (but those raise exceptions above)
        review = run_log.get("review")
        if review is None:
            return 1
        else:
            return 0

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
