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
        # Hermetic against host git config: managed environments may force
        # commit signing globally (commit.gpgsign=true with a signing helper
        # that rejects repos outside the session), which would fail every
        # scratch-repo commit. Worktrees share this repo-local config, so the
        # fake worker's commits are covered too.
        _git(["config", "commit.gpgsign", "false"], path)
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

    def _config_file(self, gate, reviewer=None):
        """Write a config with the fake worker and the given gate list."""
        cfg = {
            "worker": {
                "command": ["python3", "-c", FAKE_WORKER_PY],
            },
            "gate": gate,
        }
        if reviewer is not None:
            cfg["reviewer"] = reviewer
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "add config"], self.repo)
        return cfg_path

    def _config_file_dict(self, cfg):
        """Write an arbitrary config dict as farnsworth.json and commit it."""
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "add config"], self.repo)
        return cfg_path

    def _track_worktree(self, worktree_id):
        """Track a worktree for cleanup (e.g., 'task-042-w1')."""
        wt = os.path.join(self.tmp, worktree_id)
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
        # M1 tests need a fake reviewer since candidates now trigger review.
        fake_reviewer = {"command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]}
        cfg = self._config_file(gate, reviewer=fake_reviewer)
        self._track_worktree("task-042-w1")

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
            "reviewer": {"command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "cfg"], self.repo)
        self._track_worktree("task-042-w1")

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
        # When gate fails, no review is needed (no candidates).
        cfg = self._config_file(gate)
        self._track_worktree("task-042-w1")

        run_log = run(brief, config_path=cfg, cwd=self.repo)
        self._track_worktree("task-042-w1")
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
        fake_reviewer = {"command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]}
        cfg = self._config_file(gate, reviewer=fake_reviewer)
        self._track_worktree("task-099")

        run_log = run(brief, config_path=cfg, cwd=self.repo)
        self._track_worktree("task-099-w1")

        # Top-level fields.
        for key in ("task_id", "started_at", "finished_at", "base_commit", "workers"):
            self.assertIn(key, run_log)
        self.assertEqual(run_log["task_id"], "task-099")
        self.assertEqual(len(run_log["base_commit"]), 40)

        worker = run_log["workers"][0]
        for key in ("id", "branch", "worktree", "exit_code", "stdout_file", "gate", "candidate_label"):
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
        fake_reviewer = {"command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]}
        cfg = self._config_file(gate, reviewer=fake_reviewer)
        self._track_worktree("task-042-w1")

        run(brief, config_path=cfg, cwd=self.repo)
        self._track_worktree("task-042-w1")

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


class TestMultiWorkerParallel(LoopTestBase):
    """Test M2: multi-worker dispatch with gate and review."""

    def test_two_passing_one_failing_worker(self):
        """Two workers pass gate; review is called with multiple candidates."""
        brief = self._write_brief(name="task-m2.md", body="task body")

        # Config with 2 workers that both pass gate.
        passing_worker_py = FAKE_WORKER_PY
        gate = [{"name": "tests", "command": ["python3", "-c", "import sys; sys.exit(0)"]}]

        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", passing_worker_py]},
                {"id": "w2", "command": ["python3", "-c", passing_worker_py]},
            ],
            "reviewer": {"command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]},
            "gate": gate,
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "add m2 config"], self.repo)

        # Track worktrees.
        self._track_worktree("task-m2-w1")
        self._track_worktree("task-m2-w2")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        # Both workers in the log.
        self.assertEqual(len(run_log["workers"]), 2)
        w1 = [w for w in run_log["workers"] if w["id"] == "w1"][0]
        w2 = [w for w in run_log["workers"] if w["id"] == "w2"][0]

        # Both passed gate.
        self.assertTrue(w1["gate"]["passed"])
        self.assertTrue(w2["gate"]["passed"])

        # Both are candidates with different labels.
        self.assertIsNotNone(w1["candidate_label"])
        self.assertIsNotNone(w2["candidate_label"])
        self.assertNotEqual(w1["candidate_label"], w2["candidate_label"])

        # Diffs exist for both candidates.
        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-m2")
        for label in (w1["candidate_label"], w2["candidate_label"]):
            diff_path = os.path.join(artifact_dir, "candidates", "{0}.diff".format(label))
            self.assertTrue(os.path.exists(diff_path))
            with open(diff_path, "r", encoding="utf-8") as fh:
                diff = fh.read()
            self.assertIn("worker_output.txt", diff)  # Fake worker creates this file

        # Review happened.
        self.assertIsNotNone(run_log.get("review"))
        review = run_log["review"]
        self.assertIsNotNone(review["verdict"])
        verdict = review["verdict"]
        self.assertIn(verdict["outcome"], ("adopt", "synthesize", "escalate"))
        if verdict["outcome"] == "adopt":
            self.assertIn(verdict["candidate"], (w1["candidate_label"], w2["candidate_label"]))

    def test_briefing_to_reviewer_contains_no_worker_ids(self):
        """Reviewer briefing must not contain worker ids."""
        brief = self._write_brief(name="task-m2.md", body="task body")

        # A reviewer that records the briefing it receives.
        reviewer_record_py = (
            "exec(\"import sys,json,os,glob\\n"
            "briefing = sys.argv[1] if len(sys.argv) > 1 else ''\\n"
            "open('reviewer_briefing.txt', 'w').write(briefing)\\n"
            "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
            "if task_dirs:\\n"
            "  task_dir=task_dirs[0]\\n"
            "  with open(os.path.join(task_dir, 'verdict.json'), 'w') as f:\\n"
            "    json.dump({'outcome': 'escalate', 'candidate': None, 'reasoning': 'test'}, f)\")"
        )

        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {"command": ["python3", "-c", reviewer_record_py, "{prompt}"]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "add config"], self.repo)
        self._track_worktree("task-m2-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        # The reviewer runs inside the constructed review environment, so
        # that is where its recording lands.
        review_env = os.path.join(self.tmp, "task-m2-review")
        with open(os.path.join(review_env, "reviewer_briefing.txt"), "r", encoding="utf-8") as fh:
            reviewer_briefing = fh.read()

        # Must contain the task brief text and candidate labels.
        self.assertIn("task body", reviewer_briefing)
        self.assertIn("Candidate", reviewer_briefing)

        # Must NOT contain worker ids.
        self.assertNotIn("w1", reviewer_briefing)
        self.assertNotIn("w2", reviewer_briefing)

        # The mapping is never leaked.
        self.assertNotIn("w1 -> A", reviewer_briefing)

    def test_all_workers_fail_gate_no_review(self):
        """If all workers fail gate, no review is called; exit 1."""
        brief = self._write_brief(name="task-m2.md")

        failing_gate = [
            {"name": "tests", "command": ["python3", "-c", "import sys; sys.exit(1)"]}
        ]
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
                {"id": "w2", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {"command": ["echo", "should-not-run"]},
            "gate": failing_gate,
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "add config"], self.repo)
        self._track_worktree("task-m2-w1")
        self._track_worktree("task-m2-w2")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        # No candidates.
        for worker in run_log["workers"]:
            self.assertIsNone(worker["candidate_label"])

        # No review.
        self.assertIsNone(run_log.get("review"))

    def test_legacy_single_worker_still_end_to_end(self):
        """Legacy single-worker config still works end to end."""
        brief = self._write_brief(name="task-legacy.md")

        # Use legacy "worker" key instead of "workers".
        cfg_dict = {
            "worker": {
                "command": ["python3", "-c", FAKE_WORKER_PY],
            },
            "reviewer": {"command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]},
            "gate": [{"name": "tests", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)
        self._track_worktree("task-legacy-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        # Single worker with id "w1".
        self.assertEqual(len(run_log["workers"]), 1)
        self.assertEqual(run_log["workers"][0]["id"], "w1")
        self.assertTrue(run_log["workers"][0]["gate"]["passed"])

    def test_verdict_adoption_recorded(self):
        """Adopt verdict is parsed and recorded in run.json."""
        brief = self._write_brief(name="task-m2.md")

        # Use a custom verdict writer that uses the generic approach.
        adopting_reviewer_py = (
            "exec(\"import sys,json,os\\n"
            "import glob\\n"
            "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
            "if task_dirs:\\n"
            "  task_dir=task_dirs[0]\\n"
            "  verdict_path=os.path.join(task_dir, 'verdict.json')\\n"
            "  with open(verdict_path, 'w') as f:\\n"
            "    json.dump({'outcome': 'adopt', 'candidate': 'A', 'reasoning': 'looks good'}, f)\")"
        )
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {"command": ["python3", "-c", adopting_reviewer_py, "{prompt}"]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)
        self._track_worktree("task-m2-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        verdict = run_log["review"]["verdict"]
        self.assertEqual(verdict["outcome"], "adopt")
        self.assertEqual(verdict["candidate"], "A")
        self.assertIn("looks", verdict["reasoning"])

    def test_verdict_synthesize_recorded(self):
        """Synthesize verdict is parsed and recorded."""
        brief = self._write_brief(name="task-m2.md")

        synth_reviewer_py = (
            "exec(\"import sys,json,os\\n"
            "import glob\\n"
            "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
            "if task_dirs:\\n"
            "  task_dir=task_dirs[0]\\n"
            "  verdict_path=os.path.join(task_dir, 'verdict.json')\\n"
            "  with open(verdict_path, 'w') as f:\\n"
            "    json.dump({'outcome': 'synthesize', 'candidate': None, 'reasoning': 'combining ideas'}, f)\")"
        )
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {"command": ["python3", "-c", synth_reviewer_py, "{prompt}"]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)
        self._track_worktree("task-m2-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        verdict = run_log["review"]["verdict"]
        self.assertEqual(verdict["outcome"], "synthesize")
        self.assertIsNone(verdict["candidate"])

    def test_verdict_escalate_recorded(self):
        """Escalate verdict is parsed and recorded."""
        brief = self._write_brief(name="task-m2.md")

        esc_reviewer_py = (
            "exec(\"import sys,json,os\\n"
            "import glob\\n"
            "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
            "if task_dirs:\\n"
            "  task_dir=task_dirs[0]\\n"
            "  verdict_path=os.path.join(task_dir, 'verdict.json')\\n"
            "  with open(verdict_path, 'w') as f:\\n"
            "    json.dump({'outcome': 'escalate', 'candidate': None, 'reasoning': 'spec unclear'}, f)\")"
        )
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {"command": ["python3", "-c", esc_reviewer_py]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)
        self._track_worktree("task-m2-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        verdict = run_log["review"]["verdict"]
        self.assertEqual(verdict["outcome"], "escalate")
        self.assertIsNone(verdict["candidate"])

    def test_invalid_verdict_rejects(self):
        """Invalid verdict.json causes LoopError."""
        brief = self._write_brief(name="task-m2.md")

        bad_verdict_py = (
            "exec(\"import sys,json,os\\n"
            "import glob\\n"
            "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
            "if task_dirs:\\n"
            "  task_dir=task_dirs[0]\\n"
            "  verdict_path=os.path.join(task_dir, 'verdict.json')\\n"
            "  with open(verdict_path, 'w') as f:\\n"
            "    json.dump({'outcome': 'unknown', 'candidate': None, 'reasoning': 'test'}, f)\")"
        )
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {"command": ["python3", "-c", bad_verdict_py]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)
        self._track_worktree("task-m2-w1")

        with self.assertRaises(LoopError) as ctx:
            run(brief, config_path=cfg_path, cwd=self.repo)
        self.assertIn("outcome", str(ctx.exception).lower())

    def test_adopt_with_bad_label_rejects(self):
        """Adopt verdict with invalid candidate label is rejected."""
        brief = self._write_brief(name="task-m2.md")

        bad_label_py = (
            "exec(\"import sys,json,os\\n"
            "import glob\\n"
            "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
            "if task_dirs:\\n"
            "  task_dir=task_dirs[0]\\n"
            "  verdict_path=os.path.join(task_dir, 'verdict.json')\\n"
            "  with open(verdict_path, 'w') as f:\\n"
            "    json.dump({'outcome': 'adopt', 'candidate': 'Z', 'reasoning': 'oops'}, f)\")"
        )
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {"command": ["python3", "-c", bad_label_py]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)
        self._track_worktree("task-m2-w1")

        with self.assertRaises(LoopError) as ctx:
            run(brief, config_path=cfg_path, cwd=self.repo)
        self.assertIn("candidate", str(ctx.exception).lower())

    def test_run_json_equals_disk(self):
        """run.json on disk equals the returned dict."""
        brief = self._write_brief(name="task-m2.md")

        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {"command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = os.path.join(self.repo, "farnsworth.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg_dict, fh)
        _git(["add", "-A"], self.repo)
        _git(["commit", "-m", "config"], self.repo)
        self._track_worktree("task-m2-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-m2")
        with open(os.path.join(artifact_dir, "run.json"), "r", encoding="utf-8") as fh:
            disk = json.load(fh)

        self.assertEqual(disk, run_log)


# Fake reviewer that writes a valid verdict.
# Reads briefing from argv[1] and extracts task_id.
FAKE_REVIEWER_PY = (
    "exec(\"import sys,json,os\\n"
    "briefing=sys.argv[1] if len(sys.argv)>1 else ''\\n"
    "import glob\\n"
    "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
    "if task_dirs:\\n"
    "  task_dir=task_dirs[0]\\n"
    "  verdict_path=os.path.join(task_dir, 'verdict.json')\\n"
    "  with open(verdict_path, 'w') as f:\\n"
    "    json.dump({'outcome': 'adopt', 'candidate': 'A', 'reasoning': 'test'}, f)\")"
)


class TestConfig(unittest.TestCase):
    def test_default_config_when_absent(self):
        cfg = config.Config.load(None)
        # New default uses "workers" list with one entry.
        self.assertEqual(len(cfg.workers), 1)
        self.assertEqual(cfg.workers[0]["id"], "w1")
        self.assertTrue(any("{prompt}" in a for a in cfg.workers[0]["command"]))
        self.assertEqual(cfg.gate[0]["name"], "tests")

    def test_invalid_config_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.Config.from_dict({"workers": []})
        with self.assertRaises(config.ConfigError):
            config.Config.from_dict({"workers": [{"id": "w1", "command": []}]})

    def test_legacy_single_worker_still_works(self):
        """Back-compat: single 'worker' becomes workers[0] with id w1."""
        cfg_dict = {
            "worker": {"command": ["test", "{prompt}"]},
            "gate": [{"name": "noop", "command": ["true"]}],
        }
        cfg = config.Config.from_dict(cfg_dict)
        self.assertEqual(len(cfg.workers), 1)
        self.assertEqual(cfg.workers[0]["id"], "w1")
        self.assertEqual(cfg.workers[0]["command"], ["test", "{prompt}"])

    def test_new_workers_list_schema(self):
        """New schema with multiple workers."""
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["cmd1", "{prompt}"]},
                {"id": "w2", "command": ["cmd2"]},
            ],
            "gate": [{"name": "tests", "command": ["pytest"]}],
        }
        cfg = config.Config.from_dict(cfg_dict)
        self.assertEqual(len(cfg.workers), 2)
        self.assertEqual(cfg.workers[0]["id"], "w1")
        self.assertEqual(cfg.workers[1]["id"], "w2")

    def test_worker_id_must_be_filesystem_safe(self):
        """Worker ids must be alphanumeric or underscore."""
        cfg_dict = {
            "workers": [
                {"id": "w1-dash", "command": ["cmd"]},
            ]
        }
        with self.assertRaises(config.ConfigError) as ctx:
            config.Config.from_dict(cfg_dict)
        self.assertIn("filesystem-safe", str(ctx.exception))

    def test_duplicate_worker_ids_rejected(self):
        """Duplicate worker ids are an error."""
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["cmd1"]},
                {"id": "w1", "command": ["cmd2"]},
            ]
        }
        with self.assertRaises(config.ConfigError) as ctx:
            config.Config.from_dict(cfg_dict)
        self.assertIn("duplicate", str(ctx.exception))

    def test_reviewer_config_optional(self):
        """Reviewer is optional in config."""
        cfg_dict = {
            "workers": [{"id": "w1", "command": ["cmd"]}],
            "gate": [],
        }
        cfg = config.Config.from_dict(cfg_dict)
        self.assertIsNone(cfg.reviewer)

    def test_reviewer_config_with_command(self):
        """Reviewer can be configured with a command."""
        cfg_dict = {
            "workers": [{"id": "w1", "command": ["cmd"]}],
            "reviewer": {"command": ["reviewer", "{prompt}"]},
            "gate": [],
        }
        cfg = config.Config.from_dict(cfg_dict)
        self.assertIsNotNone(cfg.reviewer)
        self.assertEqual(cfg.reviewer["command"], ["reviewer", "{prompt}"])

    def test_focus_parsed_and_optional(self):
        """Per-worker focus is optional; present focus is kept verbatim."""
        cfg_dict = {
            "workers": [
                {
                    "id": "w1",
                    "command": ["cmd"],
                    "focus": "Focus on runtime speed",
                },
                {"id": "w2", "command": ["cmd"]},
            ],
            "gate": [],
        }
        cfg = config.Config.from_dict(cfg_dict)
        self.assertEqual(cfg.workers[0]["focus"], "Focus on runtime speed")
        self.assertIsNone(cfg.workers[1]["focus"])

    def test_invalid_focus_rejected(self):
        """Focus must be a non-empty string when present."""
        for bad in ["", "   ", 7, ["Focus on security"]]:
            cfg_dict = {
                "workers": [{"id": "w1", "command": ["cmd"], "focus": bad}],
                "gate": [],
            }
            with self.assertRaises(config.ConfigError):
                config.Config.from_dict(cfg_dict)


# A fake worker that records the briefing it received AND commits, so the
# focus tests can assert per-worker briefing content on gate-passing branches.
ECHO_COMMIT_WORKER_PY = (
    "import sys,subprocess,pathlib;"
    "pathlib.Path('briefing.txt').write_text(sys.argv[1]);"
    "subprocess.run(['git','add','-A']);"
    "subprocess.run(['git','commit','-m','echo briefing'])"
)


class TestFocusDirectives(LoopTestBase):
    """Per-worker focus directives widen the searched code space (blind field
    diversity); each worker sees only its own directive."""

    def _focus_config(self):
        return {
            "workers": [
                {
                    "id": "w1",
                    "command": ["python3", "-c", ECHO_COMMIT_WORKER_PY, "{prompt}"],
                    "focus": "Focus on runtime speed",
                },
                {
                    "id": "w2",
                    "command": ["python3", "-c", ECHO_COMMIT_WORKER_PY, "{prompt}"],
                    "focus": "Focus on security",
                },
                {
                    "id": "w3",
                    "command": ["python3", "-c", ECHO_COMMIT_WORKER_PY, "{prompt}"],
                },
            ],
            "reviewer": {"command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]},
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }

    def test_each_worker_briefed_with_only_its_own_focus(self):
        brief = self._write_brief(body="UNIQUE_TASK_BODY")
        cfg_path = self._config_file_dict(self._focus_config())
        for w in ("w1", "w2", "w3"):
            self._track_worktree("task-042-{0}".format(w))

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        briefings = {}
        for w in ("w1", "w2", "w3"):
            path = os.path.join(self.tmp, "task-042-{0}".format(w), "briefing.txt")
            with open(path, "r", encoding="utf-8") as fh:
                briefings[w] = fh.read()

        # Each focused worker got exactly its own directive, after the task.
        self.assertIn("FOCUS DIRECTIVE: Focus on runtime speed", briefings["w1"])
        self.assertNotIn("Focus on security", briefings["w1"])
        self.assertIn("FOCUS DIRECTIVE: Focus on security", briefings["w2"])
        self.assertNotIn("runtime speed", briefings["w2"])
        # The directive never outranks the brief, and says so.
        self.assertIn("take precedence", briefings["w1"])
        # An unfocused worker gets the plain briefing.
        self.assertNotIn("FOCUS DIRECTIVE", briefings["w3"])
        self.assertIn("UNIQUE_TASK_BODY", briefings["w3"])

        # run.json records each worker's focus (null when absent).
        by_id = {w["id"]: w for w in run_log["workers"]}
        self.assertEqual(by_id["w1"]["focus"], "Focus on runtime speed")
        self.assertEqual(by_id["w2"]["focus"], "Focus on security")
        self.assertIsNone(by_id["w3"]["focus"])

    def test_summary_table_written_and_shows_focus(self):
        brief = self._write_brief()
        cfg_path = self._config_file_dict(self._focus_config())
        for w in ("w1", "w2", "w3"):
            self._track_worktree("task-042-{0}".format(w))

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        summary_path = os.path.join(
            self.repo, ".farnsworth", "task-042", "summary.md"
        )
        with open(summary_path, "r", encoding="utf-8") as fh:
            summary = fh.read()
        # The on-disk table is exactly the rendering of the run log.
        from farnsworth.report import summary_table

        self.assertEqual(summary, summary_table(run_log))
        self.assertIn("| Worker | Focus | Exit | Gate | Candidate | Result |", summary)
        self.assertIn("Focus on runtime speed", summary)
        self.assertIn("ADOPTED", summary)
        self.assertIn("**Verdict:** adopt candidate A", summary)

    def test_review_briefing_lists_directives_unattributed(self):
        """Focus directives reach the reviewer as a sorted set, never mapped
        to candidates or worker ids."""
        from farnsworth.loop import build_review_briefing

        brief = self._write_brief()
        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-042")
        os.makedirs(artifact_dir, exist_ok=True)
        candidates = [{"label": "A"}, {"label": "B"}]

        briefing = build_review_briefing(
            brief,
            self.repo,
            artifact_dir,
            candidates,
            [],
            focus_directives=["Focus on runtime speed", "Focus on security"],
        )

        self.assertIn("## Field Diversity", briefing)
        self.assertIn("- Focus on runtime speed", briefing)
        self.assertIn("- Focus on security", briefing)
        self.assertIn("UNATTRIBUTED", briefing)
        # No worker ids anywhere near the directives.
        self.assertNotIn("w1", briefing)
        self.assertNotIn("w2", briefing)

    def test_review_briefing_omits_section_without_focus(self):
        from farnsworth.loop import build_review_briefing

        brief = self._write_brief()
        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-042")
        os.makedirs(artifact_dir, exist_ok=True)

        briefing = build_review_briefing(
            brief, self.repo, artifact_dir, [{"label": "A"}], [], focus_directives=[]
        )
        self.assertNotIn("Field Diversity", briefing)


# A worker that does the work but never commits: the gate (which runs in the
# worktree) sees the files, while the candidate diff (base..HEAD) is empty.
# Observed live in word-garden-4 task-002.
FAKE_NOCOMMIT_WORKER_PY = (
    "import pathlib;"
    "pathlib.Path('worker_output.txt').write_text('uncommitted work');"
    "print('FAKE_NOCOMMIT_WORKER_RAN')"
)

# A worker that commits nothing of substance: HEAD moves but the diff is empty.
FAKE_EMPTYCOMMIT_WORKER_PY = (
    "import subprocess;"
    "subprocess.run(['git','commit','--allow-empty','-m','empty']);"
    "print('FAKE_EMPTYCOMMIT_WORKER_RAN')"
)

PASSING_GATE = [
    {"name": "ok", "command": ["python3", "-c", "raise SystemExit(0)"]}
]


class TestNoCommitWorker(LoopTestBase):
    def test_gate_passing_worker_without_commits_is_not_a_candidate(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {
                        "id": "w1",
                        "command": ["python3", "-c", FAKE_NOCOMMIT_WORKER_PY],
                    }
                ],
                "gate": PASSING_GATE,
            }
        )
        self._track_worktree("task-042-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        worker = run_log["workers"][0]
        # The artifact rule is enforced: no commits means no candidate, even
        # though every configured gate command passed.
        self.assertFalse(worker["gate"]["passed"])
        self.assertIsNone(worker["candidate_label"])
        autopsies = [r["autopsy"] for r in worker["gate"]["results"]]
        self.assertTrue(
            any(a.startswith("commits: no commits on branch") for a in autopsies),
            autopsies,
        )
        self.assertIsNone(run_log["review"])
        # The uncommitted work is archived for the forensic record.
        archived = os.path.join(
            self.repo, ".farnsworth", "task-042", "w1-uncommitted.diff"
        )
        with open(archived, "r", encoding="utf-8") as fh:
            self.assertIn("worker_output.txt", fh.read())

    def test_empty_diff_candidate_is_dropped_before_labeling(self):
        brief = self._write_brief(name="task-042.md")
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {
                        "id": "w1",
                        "command": ["python3", "-c", FAKE_EMPTYCOMMIT_WORKER_PY],
                    }
                ],
                "gate": PASSING_GATE,
            }
        )
        self._track_worktree("task-042-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        worker = run_log["workers"][0]
        self.assertFalse(worker["gate"]["passed"])
        self.assertIsNone(worker["candidate_label"])
        autopsies = [r["autopsy"] for r in worker["gate"]["results"]]
        self.assertIn("candidate: empty diff against base", autopsies)
        self.assertIsNone(run_log["review"])
        # No candidate diff file was written for the vacuous candidate.
        candidates_dir = os.path.join(
            self.repo, ".farnsworth", "task-042", "candidates"
        )
        if os.path.isdir(candidates_dir):
            self.assertEqual(os.listdir(candidates_dir), [])


class TestReviewEnvironment(LoopTestBase):
    """The reviewer runs in a constructed, anonymized environment: base tree
    + labeled diffs + gate notes only (PRD Section 8, reviewer-leak risk)."""

    def _run_with_recording_reviewer(self, reviewer_py=None):
        """Run one task with a fake worker and the given fake reviewer."""
        brief = self._write_brief(name="task-rev.md", body="task body")
        cfg_dict = {
            "workers": [
                {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
            ],
            "reviewer": {
                "command": [
                    "python3", "-c", reviewer_py or FAKE_REVIEWER_PY, "{prompt}"
                ]
            },
            "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
        }
        cfg_path = self._config_file_dict(cfg_dict)
        self._track_worktree("task-rev-w1")
        return run(brief, config_path=cfg_path, cwd=self.repo)

    def test_review_env_constructed_and_stripped(self):
        run_log = self._run_with_recording_reviewer()

        env = os.path.join(self.tmp, "task-rev-review")
        self.assertTrue(os.path.isdir(env))
        # Base tree content is present...
        self.assertTrue(os.path.exists(os.path.join(env, "README.md")))
        # ...but the attribution surfaces are not.
        self.assertFalse(os.path.exists(os.path.join(env, "farnsworth.json")))
        # The env is a FRESH repo: exactly one commit, no worker branches.
        log = _git(["log", "--oneline"], env).stdout.strip().splitlines()
        self.assertEqual(len(log), 1)
        branches = _git(["branch", "--list"], env).stdout
        self.assertNotIn("task-rev-w1", branches)
        # Labeled diffs are available at the briefing's relative path.
        label = run_log["workers"][0]["candidate_label"]
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    env, ".farnsworth", "task-rev", "candidates",
                    "{0}.diff".format(label),
                )
            )
        )
        # The run log records the environment.
        self.assertEqual(run_log["review"]["environment"], "../task-rev-review")

    def test_review_artifacts_copied_back(self):
        # A reviewer that writes review.md and a verdict with a progression
        # note, like the real protocol asks.
        reviewer_py = (
            "exec(\"import sys,json,os,glob\\n"
            "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
            "task_dir=task_dirs[0]\\n"
            "open(os.path.join(task_dir,'review.md'),'w').write('REVIEW_BODY')\\n"
            "open(os.path.join(task_dir,'blind-sketch.md'),'w').write('SKETCH')\\n"
            "with open(os.path.join(task_dir,'verdict.json'),'w') as f:\\n"
            "  json.dump({'outcome':'adopt','candidate':'A',"
            "'reasoning':'fine','progression':'PROGRESSION_NOTE'}, f)\")"
        )
        run_log = self._run_with_recording_reviewer(reviewer_py)

        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-rev")
        for name in ("review.md", "blind-sketch.md", "verdict.json"):
            self.assertTrue(
                os.path.exists(os.path.join(artifact_dir, name)),
                "missing copied-back artifact: {0}".format(name),
            )
        # The progression note travels inside the verdict and reaches the
        # summary table.
        self.assertEqual(
            run_log["review"]["verdict"]["progression"], "PROGRESSION_NOTE"
        )
        with open(os.path.join(artifact_dir, "summary.md"), "r", encoding="utf-8") as fh:
            summary = fh.read()
        self.assertIn("**Progression:** PROGRESSION_NOTE", summary)

    def test_preexisting_review_env_aborts_before_dispatch(self):
        brief = self._write_brief(name="task-rev.md")
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]},
                ],
                "reviewer": {
                    "command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]
                },
                "gate": [{"name": "noop", "command": ["python3", "-c", ""]}],
            }
        )
        os.makedirs(os.path.join(self.tmp, "task-rev-review"))

        with self.assertRaises(LoopError) as ctx:
            run(brief, config_path=cfg_path, cwd=self.repo)
        self.assertIn("review environment", str(ctx.exception).lower())
        # The collision was caught before any worktree was created.
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, "task-rev-w1")))

    def test_briefed_diff_paths_resolve_in_review_env(self):
        """The paths the briefing names must exist where the reviewer runs.

        Word Garden 5 lesson: a fake reviewer that GLOBS for artifacts
        validates the plumbing but not the briefing contract -- the first
        live reviewer followed the briefed path and found nothing there.
        This test reads the briefing the way a real reviewer does.
        """
        reviewer_py = (
            "exec(\"import sys,json,os,re,glob\\n"
            "briefing = sys.argv[1] if len(sys.argv) > 1 else ''\\n"
            "open('reviewer_briefing.txt','w').write(briefing)\\n"
            "task_dirs=[d for d in glob.glob('.farnsworth/task-*') if os.path.isdir(d)]\\n"
            "task_dir=task_dirs[0]\\n"
            "with open(os.path.join(task_dir,'verdict.json'),'w') as f:\\n"
            "  json.dump({'outcome':'escalate','candidate':None,'reasoning':'t'}, f)\")"
        )
        self._run_with_recording_reviewer(reviewer_py)

        env = os.path.join(self.tmp, "task-rev-review")
        with open(os.path.join(env, "reviewer_briefing.txt"), "r", encoding="utf-8") as fh:
            briefing = fh.read()
        briefed_paths = [
            line.split(": ", 1)[1].strip()
            for line in briefing.splitlines()
            if line.startswith("- Candidate ")
        ]
        self.assertTrue(briefed_paths, "briefing lists no candidates")
        for path in briefed_paths:
            self.assertTrue(
                os.path.exists(os.path.join(env, path)),
                "briefed diff path missing in review env: {0}".format(path),
            )

    def test_review_briefing_carries_the_protocol(self):
        from farnsworth.loop import build_review_briefing

        brief = self._write_brief(name="task-rev.md")
        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-rev")
        os.makedirs(artifact_dir, exist_ok=True)

        briefing = build_review_briefing(
            brief, self.repo, artifact_dir, [{"label": "A"}], []
        )
        self.assertIn("blind-sketch.md", briefing)
        self.assertIn("review.md", briefing)
        self.assertIn("code-tips.next.md", briefing)
        self.assertIn("progression", briefing)
        self.assertIn("git reset --hard", briefing)
        # The sketch comes before the diffs may be read.
        self.assertIn("BEFORE reading any candidate diff", briefing)


if __name__ == "__main__":
    unittest.main()
