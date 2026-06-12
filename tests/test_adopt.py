"""Tests for `farnsworth adopt`: merge the winner, install the tips."""

from __future__ import annotations

import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth.adopt import adopt, count_adopted  # noqa: E402
from farnsworth.loop import LoopError, run  # noqa: E402

from tests.test_loop import (  # noqa: E402
    FAKE_REVIEWER_PY,
    FAKE_WORKER_PY,
    LoopTestBase,
    _git,
)

PASSING_GATE = [
    {"name": "ok", "command": ["python3", "-c", "raise SystemExit(0)"]}
]


class AdoptTestBase(LoopTestBase):
    def _run_adopted_task(self, task_name="task-042"):
        """Run one real round whose fake reviewer adopts candidate A."""
        brief = self._write_brief(name=task_name + ".md")
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]}
                ],
                "reviewer": {
                    "command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]
                },
                "gate": PASSING_GATE,
            }
        )
        self._track_worktree(task_name + "-w1")
        return run(brief, config_path=cfg_path, cwd=self.repo)


class TestAdopt(AdoptTestBase):
    def test_adopt_merges_winner_and_installs_tips(self):
        self._run_adopted_task()
        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-042")
        with open(
            os.path.join(artifact_dir, "code-tips.next.md"), "w", encoding="utf-8"
        ) as fh:
            fh.write("# Code Tips\n- [2026-06-12, task-042] DISTILLED_LESSON\n")

        result = adopt("task-042", cwd=self.repo)

        self.assertEqual(result["candidate"], "A")
        self.assertEqual(result["worker_id"], "w1")
        self.assertEqual(result["merged_branch"], "task-042-w1")
        # The winner's work landed on the current branch.
        self.assertTrue(
            os.path.exists(os.path.join(self.repo, "worker_output.txt"))
        )
        log = _git(["log", "--oneline"], self.repo).stdout
        self.assertIn("task-042: adopt candidate A", log)
        # The reviewer's tips were installed and committed.
        self.assertTrue(result["tips_installed"])
        with open(
            os.path.join(self.repo, ".code-tips.md"), "r", encoding="utf-8"
        ) as fh:
            self.assertIn("DISTILLED_LESSON", fh.read())
        self.assertIn("Good news, everyone! task-042 lessons installed", log)
        # One adopted task on record; consolidation not yet due.
        self.assertEqual(result["adopted_count"], 1)
        self.assertFalse(result["consolidation_due"])
        self.assertFalse(result["seed_tips_pending"])

    def test_untracked_artifacts_do_not_block_the_merge(self):
        # run() leaves .farnsworth/ untracked in the main repo; adoption
        # must not demand they be committed first.
        self._run_adopted_task()
        status = _git(["status", "--porcelain"], self.repo).stdout
        self.assertIn(".farnsworth", status)  # precondition: dirt exists

        result = adopt("task-042", cwd=self.repo)
        self.assertEqual(result["merged_branch"], "task-042-w1")

    def test_seed_tips_flagged_for_routing(self):
        self._run_adopted_task()
        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-042")
        with open(
            os.path.join(artifact_dir, "seed-tips.next.md"), "w", encoding="utf-8"
        ) as fh:
            fh.write("- a general lesson\n")

        result = adopt("task-042", cwd=self.repo)
        self.assertTrue(result["seed_tips_pending"])

    def test_non_adopt_verdict_refuses(self):
        self._run_adopted_task()
        run_json = os.path.join(
            self.repo, ".farnsworth", "task-042", "run.json"
        )
        with open(run_json, "r", encoding="utf-8") as fh:
            log = json.load(fh)
        log["review"]["verdict"] = {
            "outcome": "escalate",
            "candidate": None,
            "reasoning": "spec unclear",
        }
        with open(run_json, "w", encoding="utf-8") as fh:
            json.dump(log, fh)

        with self.assertRaises(LoopError) as ctx:
            adopt("task-042", cwd=self.repo)
        self.assertIn("not adopt", str(ctx.exception))

    def test_missing_branch_refuses(self):
        self._run_adopted_task()
        _git(
            ["worktree", "remove", "--force", os.path.join(self.tmp, "task-042-w1")],
            self.repo,
        )
        _git(["branch", "-D", "task-042-w1"], self.repo)

        with self.assertRaises(LoopError) as ctx:
            adopt("task-042", cwd=self.repo)
        self.assertIn("no longer exists", str(ctx.exception))

    def test_dirty_tracked_files_refuse(self):
        self._run_adopted_task()
        with open(os.path.join(self.repo, "README.md"), "a", encoding="utf-8") as fh:
            fh.write("dirty\n")

        with self.assertRaises(LoopError) as ctx:
            adopt("task-042", cwd=self.repo)
        self.assertIn("tracked", str(ctx.exception))

    def test_no_run_log_refuses(self):
        with self.assertRaises(LoopError) as ctx:
            adopt("task-999", cwd=self.repo)
        self.assertIn("no run log", str(ctx.exception))

    def test_count_adopted_counts_only_adopt_verdicts(self):
        self._run_adopted_task()
        self.assertEqual(count_adopted(self.repo), 1)


if __name__ == "__main__":
    unittest.main()
