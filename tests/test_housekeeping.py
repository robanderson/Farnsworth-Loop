"""Tests for run housekeeping: command timeouts and the clean subcommand.

Same scratch-repo discipline as test_loop: throwaway repos in temp dirs,
fake workers as ``python3 -c`` one-liners, never the real ``claude``.
"""

from __future__ import annotations

import os
import time
import unittest

from farnsworth import cli
from farnsworth.config import Config, ConfigError
from farnsworth.housekeeping import clean
from farnsworth.loop import LoopError, run

from tests.test_loop import FAKE_WORKER_PY, LoopTestBase, _git

# A worker that hangs far longer than any test timeout we set.
HUNG_WORKER_PY = "import time; time.sleep(60)"

PASS_GATE = [{"name": "ok", "command": ["python3", "-c", "raise SystemExit(0)"]}]
FAIL_GATE = [{"name": "no", "command": ["python3", "-c", "raise SystemExit(1)"]}]


class TestTimeoutConfig(unittest.TestCase):
    def test_valid_timeout_parsed(self):
        cfg = Config.from_dict(
            {
                "workers": [
                    {
                        "id": "w1",
                        "command": ["x", "{prompt}"],
                        "timeout_seconds": 5,
                    }
                ],
                "reviewer": {
                    "command": ["r", "{prompt}"],
                    "timeout_seconds": 2.5,
                },
            }
        )
        self.assertEqual(cfg.workers[0]["timeout"], 5)
        self.assertEqual(cfg.reviewer["timeout"], 2.5)

    def test_absent_timeout_is_none(self):
        cfg = Config.from_dict(
            {"workers": [{"id": "w1", "command": ["x", "{prompt}"]}]}
        )
        self.assertIsNone(cfg.workers[0]["timeout"])

    def test_invalid_timeouts_rejected(self):
        for bad in (0, -1, "5", True, []):
            with self.assertRaises(ConfigError):
                Config.from_dict(
                    {
                        "workers": [
                            {
                                "id": "w1",
                                "command": ["x"],
                                "timeout_seconds": bad,
                            }
                        ]
                    }
                )


class TestWorkerTimeout(LoopTestBase):
    def test_hung_worker_is_killed_recorded_and_gated(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {
                        "id": "w1",
                        "command": ["python3", "-c", HUNG_WORKER_PY],
                        "timeout_seconds": 1,
                    }
                ],
                "gate": FAIL_GATE,
            }
        )
        self._worktrees.append(os.path.join(self.tmp, "task-042-w1"))

        start = time.monotonic()
        run_log = run(brief, config_path=cfg_path, cwd=self.repo)
        elapsed = time.monotonic() - start

        # The 60s sleeper must have been killed at the 1s timeout.
        self.assertLess(elapsed, 30)
        worker = run_log["workers"][0]
        self.assertEqual(worker["exit_code"], -1)
        # The gate still ran and is recorded.
        self.assertFalse(worker["gate"]["passed"])
        self.assertEqual(worker["gate"]["results"][0]["name"], "no")
        # A killed worker with a failing gate means no candidates.
        self.assertIsNone(run_log["review"])
        # The stderr artifact names the timeout for the autopsy trail.
        stderr_path = os.path.join(
            self.repo, ".farnsworth", "task-042", "w1.stderr"
        )
        with open(stderr_path, "r", encoding="utf-8") as fh:
            self.assertIn("killed after 1s timeout", fh.read())


class TestReviewerTimeout(LoopTestBase):
    def test_hung_reviewer_is_infra_error(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]}
                ],
                "reviewer": {
                    "command": ["python3", "-c", HUNG_WORKER_PY],
                    "timeout_seconds": 1,
                },
                "gate": PASS_GATE,
            }
        )
        self._worktrees.append(os.path.join(self.tmp, "task-042-w1"))

        with self.assertRaises(LoopError) as ctx:
            run(brief, config_path=cfg_path, cwd=self.repo)
        self.assertIn("reviewer timed out", str(ctx.exception))


class TestClean(LoopTestBase):
    def _run_task(self, task_id="task-042"):
        """Run one fake-worker task (failing gate: no reviewer needed).

        Returns (run_log, brief_path, cfg_path) so callers can re-run the
        same task without re-committing identical fixtures.
        """
        brief = self._write_brief(name=task_id + ".md")
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]}
                ],
                "gate": FAIL_GATE,
            }
        )
        self._worktrees.append(
            os.path.join(self.tmp, "{0}-w1".format(task_id))
        )
        return run(brief, config_path=cfg_path, cwd=self.repo), brief, cfg_path

    def test_clean_removes_worktree_and_branch(self):
        self._run_task()
        worktree = os.path.join(self.tmp, "task-042-w1")
        self.assertTrue(os.path.isdir(worktree))

        report = clean("task-042", cwd=self.repo)

        # Compare resolved paths: git canonicalizes symlinked tempdirs
        # (macOS /var -> /private/var) in worktree paths.
        self.assertEqual(
            [os.path.realpath(p) for p in report["removed_worktrees"]],
            [os.path.realpath(worktree)],
        )
        self.assertEqual(report["removed_branches"], ["task-042-w1"])
        self.assertEqual(report["skipped"], [])
        self.assertFalse(os.path.exists(worktree))
        branches = _git(["branch", "--list", "task-042-w1"], self.repo)
        self.assertEqual(branches.stdout.strip(), "")

    def test_clean_enables_rerun_of_same_task(self):
        _, brief, cfg_path = self._run_task()
        clean("task-042", cwd=self.repo)
        # Commit the first run's artifacts (as a real orchestrator would)
        # so the clean-tree precondition holds for the re-dispatch.
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "task-042 artifacts"], self.repo)
        # Re-dispatch of the same task id must pass the collision pre-checks.
        run_log = run(brief, config_path=cfg_path, cwd=self.repo)
        self.assertEqual(run_log["task_id"], "task-042")

    def test_dirty_worktree_skipped_without_force(self):
        self._run_task()
        worktree = os.path.join(self.tmp, "task-042-w1")
        with open(os.path.join(worktree, "junk.txt"), "w") as fh:
            fh.write("uncommitted")

        report = clean("task-042", cwd=self.repo)
        self.assertEqual(report["removed_worktrees"], [])
        self.assertEqual(report["removed_branches"], [])
        self.assertEqual(len(report["skipped"]), 1)
        self.assertIn("uncommitted", report["skipped"][0]["reason"])
        self.assertTrue(os.path.isdir(worktree))

        report = clean("task-042", cwd=self.repo, force=True)
        self.assertEqual(
            [os.path.realpath(p) for p in report["removed_worktrees"]],
            [os.path.realpath(worktree)],
        )
        self.assertFalse(os.path.exists(worktree))

    def test_clean_ignores_other_tasks_and_main_worktree(self):
        self._run_task()
        report = clean("task-999", cwd=self.repo)
        self.assertEqual(report["removed_worktrees"], [])
        self.assertEqual(report["removed_branches"], [])
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, "task-042-w1")))

    def test_cli_clean_exit_codes(self):
        self._run_task()
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertEqual(cli.main(["clean", "task-042"]), 0)
            # Nothing left: still exit 0.
            self.assertEqual(cli.main(["clean", "task-042"]), 0)
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()


class TestCleanFromInsideWorktree(LoopTestBase):
    def test_clean_resolves_main_repo_from_linked_worktree(self):
        # Reproduces the word-garden-4 task-002 sweep failure: clean invoked
        # with cwd INSIDE a linked worktree must target the main repo, not
        # protect the worktree as "the main worktree" while deleting its
        # branch out from under it.
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]}
                ],
                "gate": FAIL_GATE,
            }
        )
        worktree = os.path.join(self.tmp, "task-042-w1")
        self._worktrees.append(worktree)
        run(brief, config_path=cfg_path, cwd=self.repo)
        self.assertTrue(os.path.isdir(worktree))

        report = clean("task-042", cwd=worktree, force=True)

        self.assertEqual(report["skipped"], [])
        self.assertEqual(len(report["removed_worktrees"]), 1)
        self.assertIn("task-042-w1", report["removed_branches"])
        self.assertFalse(os.path.exists(worktree))
        # The main repo is untouched.
        self.assertTrue(os.path.isdir(os.path.join(self.repo, ".git")))
