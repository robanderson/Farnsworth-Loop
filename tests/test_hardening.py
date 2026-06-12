"""Tests for the process-hardening upgrades.

Covers: explicit-config-must-exist, the shared worker preamble in
subprocess dispatch, mechanical hygiene enforcement at the gate, stdout
fallback in gate autopsies, per-worker cost capture, recorded field
divergence, and the generalize-while-distilling instruction in the review
briefing.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth import cli, config  # noqa: E402
from farnsworth.divergence import divergence  # noqa: E402
from farnsworth.loop import (  # noqa: E402
    _extract_cost_usd,
    build_review_briefing,
    run,
)

from tests.test_loop import (  # noqa: E402
    FAKE_REVIEWER_PY,
    FAKE_WORKER_PY,
    LoopTestBase,
    _git,
)

PASSING_GATE = [
    {"name": "ok", "command": ["python3", "-c", "raise SystemExit(0)"]}
]


class TestExplicitConfig(unittest.TestCase):
    def test_explicit_missing_path_is_an_error(self):
        with self.assertRaises(config.ConfigError) as ctx:
            config.Config.load("/definitely/not/there.json", explicit=True)
        self.assertIn("not found", str(ctx.exception))

    def test_default_location_still_falls_back(self):
        cfg = config.Config.load("/definitely/not/there.json")
        self.assertEqual(cfg.workers[0]["id"], "w1")

    def test_default_fleet_is_delegate_not_subprocess(self):
        # word-garden-4 pre-flight found the old subprocess default fatal
        # twice over (--bare kills OAuth; headless acceptEdits denies all
        # Bash). The strongest fix landed with the June 2026 subscription
        # caps on `claude -p`: the default fleet carries no subprocess
        # command at all — Anthropic models dispatch as host-session
        # subagents (delegate mode), and `command` workers exist only as
        # the third-party adapter.
        cfg = config.Config.load(None)
        self.assertEqual(cfg.mode, "delegate")
        self.assertIsNone(cfg.workers[0]["command"])


class TestExplicitConfigCli(LoopTestBase):
    def test_cli_run_with_typoed_config_exits_2(self):
        brief = self._write_brief()
        old_cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            rc = cli.main(["run", brief, "--config", "no-such-config.json"])
        finally:
            os.chdir(old_cwd)
        self.assertEqual(rc, 2)
        # Nothing was dispatched on the silent default fleet.
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, "task-042-w1")))


class TestWorkerPreamble(LoopTestBase):
    def test_subprocess_workers_get_rules_of_engagement(self):
        brief = self._write_brief(body="UNIQUE_TASK_BODY")
        echo_worker = (
            "import sys,subprocess,pathlib;"
            "pathlib.Path('briefing.txt').write_text(sys.argv[1]);"
            "subprocess.run(['git','add','-A']);"
            "subprocess.run(['git','commit','-m','echo'])"
        )
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", echo_worker, "{prompt}"]}
                ],
                "reviewer": {
                    "command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]
                },
                "gate": PASSING_GATE,
            }
        )
        self._track_worktree("task-042-w1")

        run(brief, config_path=cfg_path, cwd=self.repo)

        with open(
            os.path.join(self.tmp, "task-042-w1", "briefing.txt"),
            "r",
            encoding="utf-8",
        ) as fh:
            briefing = fh.read()
        self.assertIn("You are worker w1", briefing)
        self.assertIn("task-042-w1", briefing)  # the branch to commit to
        self.assertIn("COMMIT all of your work", briefing)
        self.assertIn(".code-tips.md", briefing)
        self.assertIn("UNIQUE_TASK_BODY", briefing)


class TestHygieneGate(LoopTestBase):
    TIPS_EDIT_WORKER_PY = (
        "import subprocess,pathlib;"
        "pathlib.Path('.code-tips.md').write_text('corrupted by worker');"
        "pathlib.Path('real_work.txt').write_text('work');"
        "subprocess.run(['git','add','-A']);"
        "subprocess.run(['git','commit','-m','work plus tips edit'])"
    )

    def test_candidate_modifying_code_tips_fails_gate(self):
        with open(
            os.path.join(self.repo, ".code-tips.md"), "w", encoding="utf-8"
        ) as fh:
            fh.write("# Code Tips\n")
        brief = self._write_brief()
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {
                        "id": "w1",
                        "command": ["python3", "-c", self.TIPS_EDIT_WORKER_PY],
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
        self.assertTrue(
            any("hygiene: modified protected file(s)" in a for a in autopsies),
            autopsies,
        )
        self.assertTrue(any(".code-tips.md" in a for a in autopsies), autopsies)

    def test_clean_candidate_passes_hygiene(self):
        brief = self._write_brief()
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
        self._track_worktree("task-042-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)
        self.assertTrue(run_log["workers"][0]["gate"]["passed"])


class TestGateAutopsyStdout(LoopTestBase):
    def test_stdout_only_failure_reaches_the_autopsy(self):
        brief = self._write_brief()
        gate = [
            {
                "name": "tests",
                "command": [
                    "python3",
                    "-c",
                    "print('FAILED: 3 assertions'); raise SystemExit(1)",
                ],
            }
        ]
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", FAKE_WORKER_PY]}
                ],
                "gate": gate,
            }
        )
        self._track_worktree("task-042-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        autopsy = run_log["workers"][0]["gate"]["results"][0]["autopsy"]
        self.assertIn("tests: exit 1", autopsy)
        self.assertIn("FAILED: 3 assertions", autopsy)


COST_WORKER_PY = (
    "import subprocess,pathlib,json;"
    "pathlib.Path('worker_output.txt').write_text('costed work');"
    "subprocess.run(['git','add','-A']);"
    "subprocess.run(['git','commit','-m','work']);"
    "print(json.dumps({'result': 'done', 'total_cost_usd': 0.42}))"
)


class TestCostCapture(LoopTestBase):
    def test_extract_cost_usd(self):
        self.assertEqual(_extract_cost_usd('{"total_cost_usd": 1.5}'), 1.5)
        self.assertEqual(
            _extract_cost_usd('noise\n{"total_cost_usd": 0.07}'), 0.07
        )
        self.assertIsNone(_extract_cost_usd('{"total_cost_usd": true}'))
        self.assertIsNone(_extract_cost_usd("not json at all"))
        self.assertIsNone(_extract_cost_usd(""))
        self.assertIsNone(_extract_cost_usd(None))

    def test_worker_cost_recorded_in_run_json(self):
        brief = self._write_brief()
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", COST_WORKER_PY]}
                ],
                "reviewer": {
                    "command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]
                },
                "gate": PASSING_GATE,
            }
        )
        self._track_worktree("task-042-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        self.assertEqual(run_log["workers"][0]["cost_usd"], 0.42)
        # The fake reviewer prints no JSON; its cost is honestly absent.
        self.assertIsNone(run_log["review"]["cost_usd"])


DIVERGENT_WORKER_A = (
    "import subprocess,pathlib;"
    "pathlib.Path('approach.py').write_text('alpha beta gamma delta\\n');"
    "subprocess.run(['git','add','-A']);"
    "subprocess.run(['git','commit','-m','a'])"
)
DIVERGENT_WORKER_B = (
    "import subprocess,pathlib;"
    "pathlib.Path('approach.py').write_text('epsilon zeta eta theta\\n');"
    "subprocess.run(['git','add','-A']);"
    "subprocess.run(['git','commit','-m','b'])"
)


class TestDivergence(unittest.TestCase):
    def test_fewer_than_two_candidates_is_none(self):
        self.assertIsNone(divergence([]))
        self.assertIsNone(divergence(["+line\n"]))

    def test_identical_diffs_score_zero(self):
        diff = "+++ b/x.py\n+alpha beta\n"
        score = divergence([diff, diff])
        self.assertEqual(score["score"], 0.0)
        self.assertEqual(score["candidates"], 2)
        self.assertEqual(score["metric"], "token-jaccard")

    def test_disjoint_diffs_score_one(self):
        score = divergence(["+alpha beta\n", "+gamma delta\n"])
        self.assertEqual(score["score"], 1.0)


class TestDivergenceRecorded(LoopTestBase):
    def test_two_candidate_round_records_divergence(self):
        brief = self._write_brief()
        cfg_path = self._config_file_dict(
            {
                "workers": [
                    {"id": "w1", "command": ["python3", "-c", DIVERGENT_WORKER_A]},
                    {"id": "w2", "command": ["python3", "-c", DIVERGENT_WORKER_B]},
                ],
                "reviewer": {
                    "command": ["python3", "-c", FAKE_REVIEWER_PY, "{prompt}"]
                },
                "gate": PASSING_GATE,
            }
        )
        self._track_worktree("task-042-w1")
        self._track_worktree("task-042-w2")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)

        div = run_log["divergence"]
        self.assertEqual(div["candidates"], 2)
        self.assertGreater(div["score"], 0.0)
        # And it survives in the on-disk contract of record.
        run_json = os.path.join(
            self.repo, ".farnsworth", "task-042", "run.json"
        )
        with open(run_json, "r", encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["divergence"], div)

    def test_single_candidate_round_records_none(self):
        brief = self._write_brief()
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
        self._track_worktree("task-042-w1")

        run_log = run(brief, config_path=cfg_path, cwd=self.repo)
        self.assertIsNone(run_log["divergence"])


class TestDistillationInstruction(LoopTestBase):
    def test_review_briefing_routes_general_lessons_to_seed_pile(self):
        brief = self._write_brief()
        artifact_dir = os.path.join(self.repo, ".farnsworth", "task-042")
        os.makedirs(artifact_dir, exist_ok=True)

        briefing = build_review_briefing(
            brief, self.repo, artifact_dir, [{"label": "A"}], []
        )
        self.assertIn("GENERALIZE WHILE DISTILLING", briefing)
        self.assertIn("seed-tips.next.md", briefing)
        self.assertIn("code-tips.next.md", briefing)


if __name__ == "__main__":
    unittest.main()
