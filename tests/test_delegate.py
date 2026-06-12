"""Tests for delegate dispatch: the phased prepare/gate/finalize flow.

Same scratch-repo discipline as test_loop. The "subagents" are simulated by
the test itself doing (or deliberately not doing) work in the worktrees
between phases — which is exactly the trust model: the CLI never observes
agents, only their artifacts.
"""

from __future__ import annotations

import json
import os
import unittest

from farnsworth import cli, delegate
from farnsworth.config import Config, ConfigError
from farnsworth.loop import LoopError, run

from tests.test_loop import LoopTestBase, _git

PASS_GATE = [{"name": "ok", "command": ["python3", "-c", "raise SystemExit(0)"]}]

DELEGATE_CFG = {
    "workers": [
        {
            "id": "w1",
            "model": "claude-haiku-4-5",
            "focus": "Focus on minimal code",
        },
        {"id": "w2", "model": "claude-opus-4-8"},
    ],
    "reviewer": {"model": "claude-opus-4-8"},
    "gate": PASS_GATE,
}


class TestDelegateConfig(unittest.TestCase):
    def test_model_entries_parse_as_delegate(self):
        cfg = Config.from_dict(DELEGATE_CFG)
        self.assertEqual(cfg.mode, "delegate")
        self.assertEqual(cfg.workers[0]["model"], "claude-haiku-4-5")
        self.assertIsNone(cfg.workers[0]["command"])
        self.assertEqual(cfg.reviewer["model"], "claude-opus-4-8")

    def test_command_entries_remain_subprocess(self):
        cfg = Config.from_dict(
            {"workers": [{"id": "w1", "command": ["x", "{prompt}"]}]}
        )
        self.assertEqual(cfg.mode, "subprocess")

    def test_command_and_model_together_rejected(self):
        with self.assertRaises(ConfigError):
            Config.from_dict(
                {
                    "workers": [
                        {"id": "w1", "command": ["x"], "model": "claude-haiku-4-5"}
                    ]
                }
            )

    def test_neither_command_nor_model_rejected(self):
        with self.assertRaises(ConfigError):
            Config.from_dict({"workers": [{"id": "w1"}]})

    def test_mixed_worker_modes_rejected(self):
        with self.assertRaises(ConfigError):
            Config.from_dict(
                {
                    "workers": [
                        {"id": "w1", "model": "claude-haiku-4-5"},
                        {"id": "w2", "command": ["x", "{prompt}"]},
                    ]
                }
            )

    def test_reviewer_mode_must_match_workers(self):
        with self.assertRaises(ConfigError):
            Config.from_dict(
                {
                    "workers": [{"id": "w1", "model": "claude-haiku-4-5"}],
                    "reviewer": {"command": ["x", "{prompt}"]},
                }
            )


class DelegateTestBase(LoopTestBase):
    def _delegate_config(self, cfg=None):
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg or DELEGATE_CFG, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "add config"], self.repo)
        return cfg_path

    def _simulate_worker(self, task_id, worker_id, commit=True):
        """Play the subagent: do work in the worktree, optionally commit."""
        worktree = os.path.join(self.tmp, "{0}-{1}".format(task_id, worker_id))
        out = os.path.join(worktree, "work_{0}.txt".format(worker_id))
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("work by {0}\n".format(worker_id))
        if commit:
            _git(["add", "-A"], worktree)
            _git(["commit", "-m", "work by {0}".format(worker_id)], worktree)
        return worktree

    def _write_verdict(self, task_id, verdict):
        path = os.path.join(
            self.repo, ".farnsworth", task_id, "verdict.json"
        )
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(verdict, fh)


class TestPrepare(DelegateTestBase):
    def test_prepare_creates_worktrees_briefings_and_ledger(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._delegate_config()
        self._track_worktree("task-042-w1")
        self._track_worktree("task-042-w2")

        ledger = delegate.prepare(brief, config_path=cfg_path, cwd=self.repo)

        self.assertEqual(ledger["phase"], "awaiting-workers")
        self.assertEqual(ledger["mode"], "delegate")
        self.assertEqual(len(ledger["workers"]), 2)
        for worker in ledger["workers"]:
            self.assertTrue(
                os.path.isdir(os.path.join(self.tmp, worker["branch"]))
            )
            briefing_path = os.path.join(self.repo, worker["briefing"])
            with open(briefing_path, "r", encoding="utf-8") as fh:
                text = fh.read()
            # The briefing carries the task, the commit contract, and only
            # this worker's own focus.
            self.assertIn("do the thing", text)
            self.assertIn("COMMIT all of your work", text)
        w1_text = open(
            os.path.join(self.repo, ledger["workers"][0]["briefing"]),
            encoding="utf-8",
        ).read()
        w2_text = open(
            os.path.join(self.repo, ledger["workers"][1]["briefing"]),
            encoding="utf-8",
        ).read()
        self.assertIn("Focus on minimal code", w1_text)
        self.assertNotIn("Focus on minimal code", w2_text)

    def test_loop_run_refuses_delegate_config(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._delegate_config()
        with self.assertRaises(LoopError):
            run(brief, config_path=cfg_path, cwd=self.repo)

    def test_cli_run_returns_3_for_delegate(self):
        self._write_brief(name="task-042.md")
        self._delegate_config()
        self._track_worktree("task-042-w1")
        self._track_worktree("task-042-w2")
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertEqual(cli.main(["run", "task-042.md"]), 3)
        finally:
            os.chdir(cwd)


class TestDelegateCycle(DelegateTestBase):
    def test_full_cycle_with_no_commit_worker(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._delegate_config()
        self._track_worktree("task-042-w1")
        self._track_worktree("task-042-w2")

        delegate.prepare(brief, config_path=cfg_path, cwd=self.repo)
        # w1 behaves; w2 does the work but never commits (the live
        # word-garden-4 failure shape).
        self._simulate_worker("task-042", "w1", commit=True)
        self._simulate_worker("task-042", "w2", commit=False)

        ledger = delegate.gate("task-042", config_path=cfg_path, cwd=self.repo)

        self.assertEqual(ledger["phase"], "awaiting-review")
        by_id = {w["id"]: w for w in ledger["workers"]}
        self.assertTrue(by_id["w1"]["gate"]["passed"])
        self.assertEqual(by_id["w1"]["candidate_label"], "A")
        self.assertFalse(by_id["w2"]["gate"]["passed"])
        autopsies = [r["autopsy"] for r in by_id["w2"]["gate"]["results"]]
        self.assertTrue(
            any(a.startswith("commits: no commits on branch") for a in autopsies)
        )
        # The no-commit worker's leftovers are archived.
        archived = os.path.join(
            self.repo, ".farnsworth", "task-042", "w2-uncommitted.diff"
        )
        with open(archived, "r", encoding="utf-8") as fh:
            self.assertIn("work_w2.txt", fh.read())
        # The review briefing exists and carries protocol + candidates +
        # the failure autopsy, with the verdict schema from the body.
        review_path = os.path.join(self.repo, ledger["review_briefing"])
        with open(review_path, "r", encoding="utf-8") as fh:
            review_text = fh.read()
        self.assertIn("BLIND SKETCH FIRST", review_text)
        self.assertIn("Candidate A", review_text)
        self.assertIn("no commits on branch", review_text)
        self.assertIn("verdict.json", review_text)

        # Finalize before the reviewer wrote a verdict: hard error.
        with self.assertRaises(LoopError):
            delegate.finalize("task-042", cwd=self.repo)

        # Simulate the reviewer subagent.
        self._write_verdict(
            "task-042",
            {"outcome": "adopt", "candidate": "A", "reasoning": "ok"},
        )
        run_log = delegate.finalize("task-042", cwd=self.repo)

        self.assertEqual(run_log["mode"], "delegate")
        self.assertEqual(run_log["review"]["verdict"]["candidate"], "A")
        workers = {w["id"]: w for w in run_log["workers"]}
        self.assertEqual(workers["w1"]["candidate_label"], "A")
        self.assertIsNone(workers["w1"]["exit_code"])
        self.assertEqual(workers["w1"]["model"], "claude-haiku-4-5")
        # run.json and summary.md are on disk; summary renders '-' for the
        # agent exit code.
        summary_path = os.path.join(
            self.repo, ".farnsworth", "task-042", "summary.md"
        )
        with open(summary_path, "r", encoding="utf-8") as fh:
            summary = fh.read()
        self.assertIn("ADOPTED", summary)
        self.assertIn("| w1 | Focus on minimal code | - | PASS | A | ADOPTED |", summary)

    def test_gate_with_no_candidates(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._delegate_config()
        self._track_worktree("task-042-w1")
        self._track_worktree("task-042-w2")
        delegate.prepare(brief, config_path=cfg_path, cwd=self.repo)
        # Nobody commits anything.
        ledger = delegate.gate("task-042", config_path=cfg_path, cwd=self.repo)
        self.assertEqual(ledger["phase"], "no-candidates")
        run_log = delegate.finalize("task-042", cwd=self.repo)
        self.assertIsNone(run_log["review"])

    def test_cli_gate_and_finalize_exit_codes(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._delegate_config()
        self._track_worktree("task-042-w1")
        self._track_worktree("task-042-w2")
        delegate.prepare(brief, config_path=cfg_path, cwd=self.repo)
        self._simulate_worker("task-042", "w1", commit=True)
        self._simulate_worker("task-042", "w2", commit=True)
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertEqual(cli.main(["gate", "task-042"]), 3)
            self._write_verdict(
                "task-042",
                {"outcome": "adopt", "candidate": "A", "reasoning": "ok"},
            )
            self.assertEqual(cli.main(["finalize", "task-042"]), 0)
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
