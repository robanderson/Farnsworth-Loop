"""Command-line interface for the Farnsworth Loop.

Usage::

    python3 -m farnsworth run <task-brief.md> [--config <path>]
"""

from __future__ import annotations

import argparse
import os
import sys

from .config import ConfigError, DEFAULT_CONFIG_NAME
from .gitutil import GitError, repo_toplevel
from .loop import LoopError, run


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
    return parser


def _print_summary(run_log, worktree_abs):
    worker = run_log["workers"][0]
    gate = worker["gate"]
    print("worktree: {0}".format(worktree_abs))
    print("worker exit: {0}".format(worker["exit_code"]))
    print("gate: {0}".format("PASS" if gate["passed"] else "FAIL"))
    for result in gate["results"]:
        print("  - {0}".format(result["autopsy"]))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            run_log = run(args.brief, config_path=args.config)
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2

        # Reconstruct the absolute worktree path (sibling of the repo root).
        repo_root = repo_toplevel(os.getcwd())
        worktree_abs = os.path.normpath(
            os.path.join(repo_root, run_log["workers"][0]["worktree"])
        )
        _print_summary(run_log, worktree_abs)

        return 0 if run_log["workers"][0]["gate"]["passed"] else 1

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
