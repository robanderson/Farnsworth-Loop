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


def _print_summary(run_log, repo_root):
    """Print ASCII-only summary of the run."""
    print("")
    print("Run summary for {0}".format(run_log["task_id"]))
    print("")
    for worker in run_log["workers"]:
        gate = worker["gate"]
        status = "PASS" if gate["passed"] else "FAIL"
        label = ""
        if worker["candidate_label"] is not None:
            label = " [candidate {0}]".format(worker["candidate_label"])
        print("worker {0}: gate {1}{2}".format(worker["id"], status, label))
        for result in gate["results"]:
            print("  - {0}".format(result["autopsy"]))
    print("")

    review = run_log.get("review")
    if review is None:
        print("No candidates passed gate; no review.")
    else:
        verdict = review["verdict"]
        print(
            "Verdict: {0} [candidate: {1}]".format(
                verdict["outcome"], verdict["candidate"]
            )
        )
        print("Reasoning: {0}".format(verdict["reasoning"]))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            run_log = run(args.brief, config_path=args.config)
        except (LoopError, ConfigError, GitError) as exc:
            print("error: {0}".format(exc), file=sys.stderr)
            return 2

        repo_root = repo_toplevel(os.getcwd())
        _print_summary(run_log, repo_root)

        # Exit code logic:
        # 0: valid verdict was produced (any outcome)
        # 1: no candidates passed gate (no review, review is null)
        # 2: infrastructure/config errors (but those raise exceptions above)
        review = run_log.get("review")
        if review is None:
            return 1
        else:
            return 0

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
