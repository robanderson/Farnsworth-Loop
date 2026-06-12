"""Tests for `farnsworth preflight`: the fleet-config canary.

The canary "workers" are python one-liners standing in for `claude`,
exactly like the loop tests: a compliant one edits and commits, the
failure modes mirror the two observed config fatalities (could not edit;
could not commit).
"""

from __future__ import annotations

import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth import cli  # noqa: E402
from farnsworth.preflight import preflight  # noqa: E402

from tests.test_loop import LoopTestBase, _git  # noqa: E402

PASSING_GATE = [
    {"name": "ok", "command": ["python3", "-c", "raise SystemExit(0)"]}
]
FAILING_GATE = [
    {"name": "tests", "command": ["python3", "-c", "raise SystemExit(1)"]}
]

CANARY_OK_WORKER = (
    "import subprocess,pathlib;"
    "pathlib.Path('canary.txt').write_text('OK');"
    "subprocess.run(['git','add','-A']);"
    "subprocess.run(['git','commit','-m','preflight canary'])"
)
CANARY_NO_COMMIT_WORKER = (
    "import pathlib;" "pathlib.Path('canary.txt').write_text('OK')"
)
CANARY_NO_EDIT_WORKER = "pass"


def _status_by_name(outcome):
    return {check["name"]: check["status"] for check in outcome["checks"]}


class PreflightTestBase(LoopTestBase):
    def _preflight_config(self, worker_py, gate=None, extra=None):
        cfg = {
            "workers": [{"id": "w1", "command": ["python3", "-c", worker_py]}],
            "gate": gate if gate is not None else PASSING_GATE,
        }
        if extra:
            cfg.update(extra)
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)
        return cfg_path


class TestPreflight(PreflightTestBase):
    def test_runnable_config_passes(self):
        cfg = self._preflight_config(CANARY_OK_WORKER)

        outcome = preflight(config_path=cfg, cwd=self.repo)

        self.assertTrue(outcome["passed"], outcome["checks"])
        statuses = _status_by_name(outcome)
        self.assertEqual(statuses["config"], "pass")
        self.assertEqual(statuses["git"], "pass")
        self.assertEqual(statuses["gate-at-base"], "pass")
        self.assertEqual(statuses["canary-w1"], "pass")
        # No goal configured is a skip with a warning, never a hard failure.
        self.assertEqual(statuses["goal"], "skip")
        # Canary debris is swept.
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, "preflight-w1")))
        branches = _git(["branch", "--list", "preflight-*"], self.repo).stdout
        self.assertEqual(branches.strip(), "")

    def test_noncommitting_worker_fails_canary(self):
        cfg = self._preflight_config(CANARY_NO_COMMIT_WORKER)

        outcome = preflight(config_path=cfg, cwd=self.repo)

        self.assertFalse(outcome["passed"])
        statuses = _status_by_name(outcome)
        self.assertEqual(statuses["canary-w1"], "fail")
        detail = [
            c["detail"] for c in outcome["checks"] if c["name"] == "canary-w1"
        ][0]
        self.assertIn("no commit", detail)
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, "preflight-w1")))

    def test_nonediting_worker_fails_canary(self):
        cfg = self._preflight_config(CANARY_NO_EDIT_WORKER)

        outcome = preflight(config_path=cfg, cwd=self.repo)

        self.assertFalse(outcome["passed"])
        detail = [
            c["detail"] for c in outcome["checks"] if c["name"] == "canary-w1"
        ][0]
        self.assertIn("no canary.txt", detail)

    def test_red_gate_at_base_fails(self):
        cfg = self._preflight_config(CANARY_OK_WORKER, gate=FAILING_GATE)

        outcome = preflight(config_path=cfg, cwd=self.repo)

        self.assertFalse(outcome["passed"])
        self.assertEqual(_status_by_name(outcome)["gate-at-base"], "fail")

    def test_dirty_tree_fails(self):
        cfg = self._preflight_config(CANARY_OK_WORKER)
        with open(os.path.join(self.repo, "dirt.txt"), "w", encoding="utf-8") as fh:
            fh.write("uncommitted")

        outcome = preflight(config_path=cfg, cwd=self.repo)

        self.assertFalse(outcome["passed"])
        self.assertEqual(_status_by_name(outcome)["git"], "fail")

    def test_goal_present_passes_goal_check(self):
        cfg = self._preflight_config(
            CANARY_OK_WORKER,
            extra={
                "goal": {
                    "done": [
                        {"name": "x", "command": ["python3", "-c", "pass"]}
                    ]
                }
            },
        )
        outcome = preflight(config_path=cfg, cwd=self.repo)
        self.assertEqual(_status_by_name(outcome)["goal"], "pass")

    def test_delegate_mode_skips_canary(self):
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "workers": [{"id": "w1", "model": "claude-haiku-4-5"}],
                    "reviewer": {"model": "claude-opus-4-8"},
                    "gate": PASSING_GATE,
                },
                fh,
            )
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)

        outcome = preflight(config_path=cfg_path, cwd=self.repo)

        self.assertTrue(outcome["passed"])
        statuses = _status_by_name(outcome)
        self.assertEqual(statuses["canary"], "skip")

    def test_leftover_canary_debris_is_swept_first(self):
        cfg = self._preflight_config(CANARY_OK_WORKER)
        # A previous preflight died mid-canary: branch and worktree linger.
        _git(
            ["worktree", "add", os.path.join(self.tmp, "preflight-w1"), "-b", "preflight-w1"],
            self.repo,
        )

        outcome = preflight(config_path=cfg, cwd=self.repo)

        self.assertEqual(_status_by_name(outcome)["canary-w1"], "pass")


class TestPreflightCli(PreflightTestBase):
    def _run_cli(self, argv):
        old_cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            return cli.main(argv)
        finally:
            os.chdir(old_cwd)

    def test_cli_exit_codes(self):
        self._preflight_config(CANARY_OK_WORKER)
        self.assertEqual(self._run_cli(["preflight"]), 0)

        self._preflight_config(CANARY_NO_COMMIT_WORKER)
        self.assertEqual(self._run_cli(["preflight"]), 1)

    def test_cli_typoed_config_exits_2(self):
        self._preflight_config(CANARY_OK_WORKER)
        self.assertEqual(
            self._run_cli(["preflight", "--config", "nope.json"]), 2
        )


if __name__ == "__main__":
    unittest.main()
