"""Tests for the goal config and the `farnsworth done` termination probe."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth import cli, config  # noqa: E402
from farnsworth.loop import check_done  # noqa: E402

WORKER = {"id": "w1", "command": ["true"]}

PASS_CHECK = {"name": "always-pass", "command": ["python3", "-c", "pass"]}
FAIL_CHECK = {
    "name": "always-fail",
    "command": ["python3", "-c", "raise SystemExit(3)"],
}


class TestGoalConfig(unittest.TestCase):
    def test_goal_absent_is_none(self):
        cfg = config.Config.from_dict({"workers": [WORKER]})
        self.assertIsNone(cfg.goal)

    def test_goal_parses_brief_and_done(self):
        cfg = config.Config.from_dict(
            {
                "workers": [WORKER],
                "goal": {"brief": "GOAL.md", "done": [PASS_CHECK]},
            }
        )
        self.assertEqual(cfg.goal["brief"], "GOAL.md")
        self.assertEqual(cfg.goal["done"][0]["name"], "always-pass")

    def test_goal_brief_is_optional(self):
        cfg = config.Config.from_dict(
            {"workers": [WORKER], "goal": {"done": [PASS_CHECK]}}
        )
        self.assertIsNone(cfg.goal["brief"])

    def test_goal_without_done_rejected(self):
        with self.assertRaises(config.ConfigError) as ctx:
            config.Config.from_dict({"workers": [WORKER], "goal": {}})
        self.assertIn("done", str(ctx.exception))

    def test_goal_with_empty_done_rejected(self):
        with self.assertRaises(config.ConfigError) as ctx:
            config.Config.from_dict(
                {"workers": [WORKER], "goal": {"done": []}}
            )
        self.assertIn("at least one", str(ctx.exception))

    def test_goal_done_entries_validated_like_gate(self):
        with self.assertRaises(config.ConfigError):
            config.Config.from_dict(
                {
                    "workers": [WORKER],
                    "goal": {"done": [{"name": "x", "command": []}]},
                }
            )


class TestCheckDone(unittest.TestCase):
    def test_all_checks_pass(self):
        goal = {"brief": None, "done": [PASS_CHECK]}
        outcome = check_done(goal, os.getcwd())
        self.assertTrue(outcome["passed"])
        self.assertEqual(outcome["results"][0]["exit_code"], 0)

    def test_failing_check_reports_not_done(self):
        goal = {"brief": None, "done": [PASS_CHECK, FAIL_CHECK]}
        outcome = check_done(goal, os.getcwd())
        self.assertFalse(outcome["passed"])
        # Every check runs and is recorded, even after a failure.
        self.assertEqual(len(outcome["results"]), 2)
        self.assertEqual(outcome["results"][1]["exit_code"], 3)


class TestDoneCommand(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        subprocess.run(
            ["git", "init", "-q", self.repo], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", self.repo, "config", "commit.gpgsign", "false"],
            check=True,
        )
        self._old_cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def _write_config(self, done_checks):
        import json

        with open("farnsworth.json", "w", encoding="utf-8") as fh:
            json.dump(
                {"workers": [WORKER], "goal": {"done": done_checks}}, fh
            )

    def test_done_exits_zero_when_goal_complete(self):
        self._write_config([PASS_CHECK])
        self.assertEqual(cli.main(["done"]), 0)

    def test_done_exits_one_when_goal_not_met(self):
        self._write_config([PASS_CHECK, FAIL_CHECK])
        self.assertEqual(cli.main(["done"]), 1)

    def test_done_exits_two_without_goal(self):
        import json

        with open("farnsworth.json", "w", encoding="utf-8") as fh:
            json.dump({"workers": [WORKER]}, fh)
        self.assertEqual(cli.main(["done"]), 2)


if __name__ == "__main__":
    unittest.main()
