"""Tests for the run summary table (farnsworth.report)."""

from __future__ import annotations

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth.report import summary_table  # noqa: E402


def _worker(worker_id, focus=None, passed=True, label=None, exit_code=0,
            autopsy="tests: exit 0", gate_exit=0):
    return {
        "id": worker_id,
        "branch": "task-001-{0}".format(worker_id),
        "worktree": "../task-001-{0}".format(worker_id),
        "exit_code": exit_code,
        "stdout_file": "{0}.stdout".format(worker_id),
        "focus": focus,
        "gate": {
            "passed": passed,
            "results": [
                {"name": "tests", "exit_code": gate_exit, "autopsy": autopsy}
            ],
        },
        "candidate_label": label,
    }


def _run_log(workers, review):
    return {
        "task_id": "task-001",
        "started_at": "2026-06-12T00:00:00Z",
        "finished_at": "2026-06-12T01:00:00Z",
        "base_commit": "ba1153c9f9e2309bd17f12c78f72296d8c214fce",
        "workers": workers,
        "review": review,
    }


class TestSummaryTable(unittest.TestCase):
    def test_adopt_run_marks_winner_and_shows_focus(self):
        workers = [
            _worker("w1", focus="Focus on runtime speed", label="B"),
            _worker("w2", label="A"),
        ]
        review = {
            "exit_code": 0,
            "verdict": {
                "outcome": "adopt",
                "candidate": "A",
                "reasoning": "A is correct and complete.",
            },
        }
        table = summary_table(_run_log(workers, review))

        self.assertIn("# Run summary -- task-001", table)
        self.assertIn("| Worker | Focus | Exit | Gate | Candidate | Result |", table)
        self.assertIn("| w1 | Focus on runtime speed | 0 | PASS | B |  |", table)
        # The adopted candidate's row is positively marked.
        self.assertIn("| w2 | - | 0 | PASS | A | ADOPTED |", table)
        self.assertIn("**Verdict:** adopt candidate A", table)
        self.assertIn("**Reasoning:** A is correct and complete.", table)
        # Truncated base commit, not the full sha.
        self.assertIn("`ba1153c9f9e2`", table)
        self.assertTrue(table.isascii())

    def test_gate_failure_row_carries_autopsy(self):
        workers = [
            _worker(
                "w1",
                passed=False,
                exit_code=1,
                gate_exit=1,
                autopsy="tests: exit 1 | boom",
            ),
        ]
        table = summary_table(_run_log(workers, None))

        self.assertIn("| w1 | - | 1 | FAIL (tests: exit 1 | boom) | - |  |", table)
        self.assertIn("No candidates passed the gate; no review was run.", table)
        self.assertNotIn("ADOPTED", table)

    def test_progression_note_rendered_when_present(self):
        workers = [_worker("w1", label="A")]
        review = {
            "exit_code": 0,
            "verdict": {
                "outcome": "adopt",
                "candidate": "A",
                "reasoning": "A is correct and complete.",
            },
            "progression": (
                "Built on the task-001 engine (frozen); adds the UI layer "
                "and raises the suite from 80 to 105 tests."
            ),
        }
        table = summary_table(_run_log(workers, review))

        self.assertIn(
            "**Progression:** Built on the task-001 engine (frozen); "
            "adds the UI layer and raises the suite from 80 to 105 tests.",
            table,
        )
        # Progression follows the verdict block, never precedes it.
        self.assertLess(table.index("**Verdict:**"), table.index("**Progression:**"))

    def test_progression_absent_renders_no_block(self):
        workers = [_worker("w1", label="A")]
        review = {
            "exit_code": 0,
            "verdict": {
                "outcome": "adopt",
                "candidate": "A",
                "reasoning": "A is correct and complete.",
            },
        }
        table = summary_table(_run_log(workers, review))

        self.assertNotIn("**Progression:**", table)

    def test_synthesize_verdict_has_no_adopted_row(self):
        workers = [_worker("w1", label="A")]
        review = {
            "exit_code": 0,
            "verdict": {
                "outcome": "synthesize",
                "candidate": None,
                "reasoning": "No candidate is adequate.",
            },
        }
        table = summary_table(_run_log(workers, review))

        self.assertIn("**Verdict:** synthesize", table)
        self.assertNotIn("ADOPTED", table)
        self.assertNotIn("candidate None", table)


if __name__ == "__main__":
    unittest.main()
