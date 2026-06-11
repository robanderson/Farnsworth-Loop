"""End-to-end tests for the Farnsworth M1 skeleton.

Each test builds a throwaway git repo in a temp dir, runs the loop with a
*fake* worker command (a ``python3 -c`` one-liner -- never the real ``claude``
binary), and asserts the resulting worktree, gate behavior, and run.json.

The repo under test is wholly contained in a TemporaryDirectory, so nothing
leaks into this project's tree. Worktrees created by the loop live as siblings
of the scratch repo (also inside the temp dir) and are removed on teardown.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

# Make the package importable regardless of where the tests are discovered.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth import config, gitutil  # noqa: E402
from farnsworth.loop import LoopError, run, task_id_from_brief  # noqa: E402


def _git(args, cwd):
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise AssertionError(
            "git {0} failed: {1}".format(" ".join(args), proc.stderr)
        )
    return proc


# A fake worker that writes a file in the worktree and commits it. Stands in
# for ``claude``; tests must never invoke the real binary.
FAKE_WORKER_PY = (
    "import subprocess,pathlib;"
    "pathlib.Path('worker_output.txt').write_text('hello from fake worker');"
    "subprocess.run(['git','add','-A']);"
    "subprocess.run(['git','commit','-m','fake worker change']);"
    "print('FAKE_WORKER_RAN')"
)


class LoopTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        # The scratch repo is a subdirectory so worktrees ('../<id>-w1') land
        # inside the temp dir and not in the system temp root proper.
        self.repo = os.path.join(self.tmp, "scratch-repo")
        os.makedirs(self.repo)
        self._init_repo(self.repo)
        self._worktrees = []

    def tearDown(self):
        # Best-effort: prune any worktrees the loop created before cleanup.
        for wt in self._worktrees:
            subprocess.run(
                ["git", "worktree", "remove", "--force", wt],
                cwd=self.repo,
                capture_output=True,
                text=True,
            )
        self._tmp.cleanup()

    def _init_repo(self, path):
        _git(["init", "-b", "main"], path)
        _git(["config", "user.email", "test@example.com"], path)
        _git(["config", "user.name", "Test Runner"], path)
        # Ensure fake-worker commits succeed inside the worktree too: set a
        # global-ish identity via the repo's own config is enough because
        # worktrees share the repo config.
        with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("# scratch\n")
        _git(["add", "-A"], path)
        _git(["commit", "-m", "initial"], path)

    def _write_brief(self, name="task-042.md", body="do the thing"):
        brief_path = os.path.join(self.repo, name)
        with open(brief_path, "w", encoding="utf-8") as fh:
            fh.write("# Brief\n\n" + body + "\n")
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "add brief"], self.repo)
        return brief_path

    def _config_file(self, gate):
        """Write a config with the fake worker and the given gate list."""
        cfg = {
            "worker": {
                "command": ["python3", "-c", FAKE_WORKER_PY],
            },
            "gate": gate,
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "add config"], self.repo)
        return cfg_path

    def _track_worktree(self, task_id):
        wt = os.path.join(self.tmp, "{0}-w1".format(task_id))
        self._worktrees.append(wt)
        return wt


class TestTaskId(unittest.TestCase):
    def test_stem_extraction(self):
        self.assertEqual(task_id_from_brief("task-042.md"), "task-042")
        self.assertEqual(task_id_from_brief("/a/b/task-7.markdown"), "task-7")
        self.assertEqual(task_id_from_brief("plain"), "plain")


class TestGatePass(LoopTestBase):
    def test_worktree_created_and_gate_passes(self):
        brief = self._write_brief()
        gate = [{"name": "tests", "command": ["python3", "-c", "import sys; sys.exit(0)"]}]
        cfg = self._config_file(gate)
        self._track_worktree("task-042")

        run_log = run(brief, config_path=cfg, cwd=self.repo)

        # Worktree exists with the worker's committed file.
        wt = os.path.join(self.tmp, "task-042-w1")
        self.assertTrue(os.path.isdir(wt))
        self.assertTrue(os.path.exists(os.path.join(wt, "worker_output.txt")))

        # Branch was created.
        self.assertTrue(gitutil.branch_exists("task-042-w1", self.repo))

        # Gate passed.
        worker = run_log["workers"][0]
        self.assertTrue(worker["gate"]["passed"])
        self.assertEqual(worker["gate"]["results"][0]["exit_code"], 0)
        self.assertEqual(
            worker["gate"]["results"][0]["autopsy"], "tests: exit 0"
        )

        # Worker stdout captured verbatim.
        stdout_file = os.path.join(
            self.repo, ".farnsworth", "task-042", "w1.stdout"
        )
        with open(stdout_file, "r", encoding="utf-8") as fh:
            self.assertIn("FAKE_WORKER_RAN", fh.read())

    def test_briefing_includes_tips_and_task(self):
        # Drop a .code-tips.md in the repo; the worker should be briefed with
        # its contents followed by the task. We capture the prompt by using a
        # worker that echoes its received text into a file.
        tips_path = os.path.join(self.repo, ".code-tips.md")
        with open(tips_path, "w", encoding="utf-8") as fh:
            fh.write("# Code Tips\nSOME_TIP\n")
        # _write_brief commits all pending changes, including the tips file,
        # leaving a clean tree.
        brief = self._write_brief(body="UNIQUE_TASK_BODY")

        echo_worker = (
            "import sys;"
            "open('briefing.txt','w').write(sys.argv[1])"
        )
        cfg = {
            "worker": {"command": ["python3", "-c", echo_worker, "{prompt}"]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "cfg"], self.repo)
        self._track_worktree("task-042")

        run(brief, config_path=cfg_path, cwd=self.repo)

        wt = os.path.join(self.tmp, "task-042-w1")
        with open(os.path.join(wt, "briefing.txt"), "r", encoding="utf-8") as fh:
            briefing = fh.read()
        self.assertIn("SOME_TIP", briefing)
        self.assertIn("\n\nTASK: ", briefing)
        self.assertIn("UNIQUE_TASK_BODY", briefing)
        self.assertLess(briefing.index("SOME_TIP"), briefing.index("UNIQUE_TASK_BODY"))


class TestGateFail(LoopTestBase):
    def test_gate_failure_recorded(self):
        brief = self._write_brief()
        gate = [
            {"name": "tests", "command": ["python3", "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(1)"]},
            {"name": "lint", "command": ["python3", "-c", "import sys; sys.exit(0)"]},
        ]
        cfg = self._config_file(gate)
        self._track_worktree("task-042")

        run_log = run(brief, config_path=cfg, cwd=self.repo)
        gate_res = run_log["workers"][0]["gate"]

        self.assertFalse(gate_res["passed"])
        # All gates ran even though the first failed.
        self.assertEqual(len(gate_res["results"]), 2)
        first = gate_res["results"][0]
        self.assertEqual(first["exit_code"], 1)
        self.assertIn("tests: exit 1", first["autopsy"])
        self.assertIn("boom", first["autopsy"])
        # Second gate still recorded and passing.
        self.assertEqual(gate_res["results"][1]["exit_code"], 0)


class TestRunLogSchema(LoopTestBase):
    def test_schema_fields_present(self):
        brief = self._write_brief(name="task-099.md")
        gate = [{"name": "tests", "command": ["python3", "-c", ""]}]
        cfg = self._config_file(gate)
        self._track_worktree("task-099")

        run_log = run(brief, config_path=cfg, cwd=self.repo)

        # Top-level fields.
        for key in ("task_id", "started_at", "finished_at", "base_commit", "workers"):
            self.assertIn(key, run_log)
        self.assertEqual(run_log["task_id"], "task-099")
        self.assertEqual(len(run_log["base_commit"]), 40)

        worker = run_log["workers"][0]
        for key in ("id", "branch", "worktree", "exit_code", "stdout_file", "gate"):
            self.assertIn(key, worker)
        self.assertEqual(worker["id"], "w1")
        self.assertEqual(worker["branch"], "task-099-w1")
        self.assertEqual(worker["worktree"], "../task-099-w1")
        self.assertEqual(worker["stdout_file"], "w1.stdout")
        self.assertIn("passed", worker["gate"])
        self.assertIn("results", worker["gate"])

        # run.json written to disk in the MAIN repo and parses.
        run_json = os.path.join(self.repo, ".farnsworth", "task-099", "run.json")
        self.assertTrue(os.path.exists(run_json))
        with open(run_json, "r", encoding="utf-8") as fh:
            disk = json.load(fh)
        self.assertEqual(disk, run_log)

        # stderr also captured.
        self.assertTrue(
            os.path.exists(
                os.path.join(self.repo, ".farnsworth", "task-099", "w1.stderr")
            )
        )

    def test_does_not_write_code_tips(self):
        brief = self._write_brief()
        gate = [{"name": "tests", "command": ["python3", "-c", ""]}]
        cfg = self._config_file(gate)
        self._track_worktree("task-042")

        run(brief, config_path=cfg, cwd=self.repo)

        # The loop must never author .code-tips.md (workers are read-only).
        self.assertFalse(
            os.path.exists(os.path.join(self.repo, ".code-tips.md"))
        )
        wt = os.path.join(self.tmp, "task-042-w1")
        self.assertFalse(os.path.exists(os.path.join(wt, ".code-tips.md")))


class TestPreconditions(LoopTestBase):
    def test_dirty_tree_aborts(self):
        brief = self._write_brief()
        gate = [{"name": "tests", "command": ["python3", "-c", ""]}]
        cfg = self._config_file(gate)
        # Dirty the tree.
        with open(os.path.join(self.repo, "dirt.txt"), "w", encoding="utf-8") as fh:
            fh.write("uncommitted")

        with self.assertRaises(LoopError) as ctx:
            run(brief, config_path=cfg, cwd=self.repo)
        self.assertIn("clean", str(ctx.exception).lower())

        # No worktree should have been created.
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, "task-042-w1")))

    def test_non_git_dir_aborts(self):
        plain = os.path.join(self.tmp, "not-a-repo")
        os.makedirs(plain)
        brief = os.path.join(plain, "task-1.md")
        with open(brief, "w", encoding="utf-8") as fh:
            fh.write("x")

        with self.assertRaises(LoopError) as ctx:
            run(brief, config_path=None, cwd=plain)
        self.assertIn("git", str(ctx.exception).lower())

    def test_existing_branch_aborts(self):
        brief = self._write_brief()
        gate = [{"name": "tests", "command": ["python3", "-c", ""]}]
        cfg = self._config_file(gate)
        # Pre-create the branch the loop would want.
        _git(["branch", "task-042-w1"], self.repo)

        with self.assertRaises(LoopError) as ctx:
            run(brief, config_path=cfg, cwd=self.repo)
        self.assertIn("branch already exists", str(ctx.exception).lower())


class TestConfig(unittest.TestCase):
    def test_default_config_when_absent(self):
        cfg = config.Config.load(None)
        self.assertEqual(cfg.worker_command[0], "claude")
        self.assertTrue(any("{prompt}" in a for a in cfg.worker_command))
        self.assertEqual(cfg.gate[0]["name"], "tests")

    def test_invalid_config_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.Config.from_dict({"worker": {"command": []}})
        with self.assertRaises(config.ConfigError):
            config.Config.from_dict({"gate": []})


if __name__ == "__main__":
    unittest.main()
