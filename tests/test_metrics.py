"""Tests for the cross-run metrics aggregation (M5)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth.metrics import collect_runs, metrics_report  # noqa: E402


def _run_log(
    task_id,
    started_at,
    outcome="adopt",
    candidate="A",
    winner_id="w1",
    model=None,
    divergence=None,
    cost=None,
):
    workers = [
        {
            "id": winner_id,
            "branch": "{0}-{1}".format(task_id, winner_id),
            "gate": {"passed": True, "results": []},
            "candidate_label": candidate,
        },
        {
            "id": "w2",
            "branch": "{0}-w2".format(task_id),
            "gate": {"passed": False, "results": []},
            "candidate_label": None,
        },
    ]
    if model:
        workers[0]["model"] = model
    if cost is not None:
        workers[0]["cost_usd"] = cost
    verdict = None
    if outcome:
        verdict = {
            "outcome": outcome,
            "candidate": candidate if outcome == "adopt" else None,
            "reasoning": "test",
        }
    log = {
        "task_id": task_id,
        "started_at": started_at,
        "finished_at": started_at,
        "base_commit": "0" * 40,
        "workers": workers,
        "review": {"exit_code": 0, "verdict": verdict} if verdict else None,
    }
    if divergence is not None:
        log["divergence"] = divergence
    return log


def _write_log(root, project, task_id, log):
    task_dir = os.path.join(root, project, ".farnsworth", task_id)
    os.makedirs(task_dir, exist_ok=True)
    with open(os.path.join(task_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh)


class TestCollectRuns(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_finds_runs_across_projects_sorted_by_start(self):
        _write_log(
            self.root, ".", "task-002", _run_log("task-002", "2026-06-12T10:00:00Z")
        )
        _write_log(
            self.root,
            "examples/word-garden-1",
            "task-001",
            _run_log("task-001", "2026-06-11T09:00:00Z"),
        )

        runs = collect_runs([self.root])

        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["log"]["task_id"], "task-001")
        self.assertEqual(runs[0]["source"], "examples/word-garden-1")
        self.assertEqual(runs[1]["source"], ".")

    def test_unparseable_and_foreign_files_skipped(self):
        task_dir = os.path.join(self.root, ".farnsworth", "task-bad")
        os.makedirs(task_dir)
        with open(os.path.join(task_dir, "run.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        # A run.json outside a .farnsworth/task-* layout is ignored.
        os.makedirs(os.path.join(self.root, "elsewhere"))
        with open(
            os.path.join(self.root, "elsewhere", "run.json"), "w", encoding="utf-8"
        ) as fh:
            json.dump({"workers": []}, fh)

        self.assertEqual(collect_runs([self.root]), [])

    def test_legacy_top_level_verdict_counted(self):
        log = _run_log("task-001", "2026-06-11T09:00:00Z", outcome=None)
        log["review"] = None
        log["verdict"] = {
            "outcome": "adopt",
            "candidate": "A",
            "reasoning": "legacy",
        }
        _write_log(self.root, ".", "task-001", log)

        runs = collect_runs([self.root])
        report = metrics_report(runs)
        self.assertIn("adopt 1", report)


class TestMetricsReport(unittest.TestCase):
    def test_report_rows_and_aggregates(self):
        runs = [
            {
                "source": ".",
                "log": _run_log(
                    "task-001",
                    "2026-06-11T09:00:00Z",
                    model="claude-haiku-4-5",
                    divergence={
                        "metric": "token-jaccard",
                        "score": 0.5731,
                        "candidates": 2,
                    },
                    cost=3.03,
                ),
            },
            {
                "source": "examples/word-garden-1",
                "log": _run_log(
                    "task-002", "2026-06-12T09:00:00Z", outcome="escalate"
                ),
            },
        ]

        report = metrics_report(runs)

        self.assertIn("2 recorded task run(s)", report)
        self.assertIn("| task-001 | 2026-06-11 | . | 1/2 | adopt |", report)
        self.assertIn("w1 (claude-haiku-4-5)", report)
        self.assertIn("0.57", report)
        self.assertIn("$3.03", report)
        self.assertIn("adopt 1 / synthesize 0 / escalate 1 / none 0", report)
        self.assertIn("chart data): 1/2, 1/2", report)
        self.assertIn("claude-haiku-4-5 1", report)


if __name__ == "__main__":
    unittest.main()
