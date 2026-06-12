"""Cross-run metrics from the per-task run logs (Milestone M5).

Every number the loop's health is judged by (PRD Section 7) derives from
``run.json`` files that already exist on disk — this module aggregates them
so nobody assembles the tables by hand. ``collect_runs`` walks one or more
roots for ``.farnsworth/task-*/run.json`` (the loop's own tasks plus any
example projects under the same tree); ``metrics_report`` renders the
thirty-second cross-run view: one row per task, then the aggregate lines —
verdict distribution, first-pass gate rate over merged tasks (the chart
that matters), per-model wins where models are on record, and recorded
divergence and dollar costs where present.
"""

from __future__ import annotations

import json
import os


def collect_runs(roots):
    """Find and parse every run.json under ``roots``; sorted by start time.

    Returns a list of ``{"source": <project dir relative to its root>,
    "log": <run.json dict>}``. Unparseable files are skipped — the metrics
    view must never die on one legacy log.
    """
    runs = []
    for root in roots:
        root = os.path.abspath(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            if (
                "run.json" in filenames
                and os.path.basename(os.path.dirname(dirpath)) == ".farnsworth"
                and os.path.basename(dirpath).startswith("task-")
            ):
                path = os.path.join(dirpath, "run.json")
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        log = json.load(fh)
                except (OSError, ValueError):
                    continue
                if not isinstance(log, dict) or "workers" not in log:
                    continue
                project = os.path.relpath(
                    os.path.dirname(os.path.dirname(dirpath)), root
                )
                runs.append({"source": project, "log": log})
    runs.sort(key=lambda r: r["log"].get("started_at") or "")
    return runs


def _verdict(log):
    review = log.get("review")
    verdict = review.get("verdict") if isinstance(review, dict) else None
    if verdict is None:
        # Legacy manual-mode logs keep the verdict at the top level.
        verdict = log.get("verdict")
    return verdict


def _adopted_worker(log):
    verdict = _verdict(log)
    if not verdict or verdict.get("outcome") != "adopt":
        return None
    label = verdict.get("candidate")
    for worker in log.get("workers", []):
        if worker.get("candidate_label") == label:
            return worker
    return None


def _gate_cell(log):
    workers = log.get("workers", [])
    passed = sum(1 for w in workers if w.get("gate", {}).get("passed"))
    return "{0}/{1}".format(passed, len(workers))


def _cost_cell(log):
    total = 0.0
    seen = False
    for worker in log.get("workers", []):
        cost = worker.get("cost_usd")
        if isinstance(cost, (int, float)):
            total += cost
            seen = True
    review = log.get("review")
    if isinstance(review, dict):
        cost = review.get("cost_usd")
        if isinstance(cost, (int, float)):
            total += cost
            seen = True
    return "${0:.2f}".format(total) if seen else "-"


def _divergence_cell(log):
    div = log.get("divergence")
    if isinstance(div, dict) and isinstance(div.get("score"), (int, float)):
        return "{0:.2f}".format(div["score"])
    return "-"


def metrics_report(runs):
    """Render the cross-run metrics view as ASCII markdown."""
    lines = []
    lines.append("# Farnsworth metrics -- {0} recorded task run(s)".format(len(runs)))
    lines.append("")
    lines.append(
        "| Task | Date | Project | Gate | Verdict | Winner | Divergence | Cost |"
    )
    lines.append("|---|---|---|---|---|---|---:|---:|")

    outcomes = {"adopt": 0, "synthesize": 0, "escalate": 0, "none": 0}
    model_wins = {}
    gate_series = []
    for entry in runs:
        log = entry["log"]
        verdict = _verdict(log)
        outcome = verdict.get("outcome") if verdict else None
        outcomes[outcome if outcome in outcomes else "none"] += 1

        winner = "-"
        adopted = _adopted_worker(log)
        if adopted:
            winner = adopted.get("id", "?")
            if adopted.get("model"):
                winner += " ({0})".format(adopted["model"])
                model_wins[adopted["model"]] = model_wins.get(adopted["model"], 0) + 1
            if adopted.get("focus"):
                winner += " [{0}]".format(adopted["focus"])
        elif verdict and verdict.get("outcome") == "adopt":
            winner = verdict.get("candidate") or "-"

        gate = _gate_cell(log)
        gate_series.append(gate)
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} |".format(
                log.get("task_id", "?"),
                (log.get("started_at") or "")[:10] or "-",
                entry["source"],
                gate,
                outcome or "-",
                winner,
                _divergence_cell(log),
                _cost_cell(log),
            )
        )

    lines.append("")
    lines.append(
        "Verdicts: adopt {0} / synthesize {1} / escalate {2} / none {3}.".format(
            outcomes["adopt"],
            outcomes["synthesize"],
            outcomes["escalate"],
            outcomes["none"],
        )
    )
    if gate_series:
        # The chart that matters: first-pass gate rate over merged tasks.
        lines.append(
            "First-pass gate rate over tasks (chart data): {0}".format(
                ", ".join(gate_series)
            )
        )
    if model_wins:
        wins = ", ".join(
            "{0} {1}".format(model, count)
            for model, count in sorted(model_wins.items())
        )
        lines.append("Wins by model (adopted candidates): {0}.".format(wins))
    lines.append("")
    return "\n".join(lines)
