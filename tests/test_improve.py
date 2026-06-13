"""Tests for improvement rounds (PRD Section 2.7): config, briefing,
round counting from committed artifacts, the additive-only apply
validation, and the `improve` / `done` CLI surfaces."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth import cli, config, improve  # noqa: E402

WORKER = {"id": "w1", "command": ["true"]}
PASS_CHECK = {"name": "always-pass", "command": ["python3", "-c", "pass"]}
FAIL_CHECK = {
    "name": "always-fail",
    "command": ["python3", "-c", "raise SystemExit(3)"],
}

GOAL_TEXT = "# Goal\n\nShip the thing.\n"


class TestImprovementRoundsConfig(unittest.TestCase):
    def _goal(self, **extra):
        goal = {"brief": "GOAL.md", "done": [PASS_CHECK]}
        goal.update(extra)
        return config.Config.from_dict({"workers": [WORKER], "goal": goal})

    def test_default_is_zero(self):
        cfg = self._goal()
        self.assertEqual(cfg.goal["improvement_rounds"], 0)

    def test_parses_positive_count(self):
        cfg = self._goal(improvement_rounds=3)
        self.assertEqual(cfg.goal["improvement_rounds"], 3)

    def test_rejects_negative(self):
        with self.assertRaises(config.ConfigError):
            self._goal(improvement_rounds=-1)

    def test_rejects_non_integer(self):
        with self.assertRaises(config.ConfigError):
            self._goal(improvement_rounds="2")

    def test_rejects_bool(self):
        with self.assertRaises(config.ConfigError):
            self._goal(improvement_rounds=True)


class _RepoCase(unittest.TestCase):
    """A throwaway git repo with a goal config, as the CLI sees one."""

    rounds = 2

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        subprocess.run(
            ["git", "init", "-q", self.repo], check=True, capture_output=True
        )
        for key, value in (
            ("commit.gpgsign", "false"),
            ("user.email", "test@example.com"),
            ("user.name", "Test"),
        ):
            subprocess.run(
                ["git", "-C", self.repo, "config", key, value], check=True
            )
        self._old_cwd = os.getcwd()
        os.chdir(self.repo)
        self._write_config([PASS_CHECK])
        with open("GOAL.md", "w", encoding="utf-8") as fh:
            fh.write(GOAL_TEXT)
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed"],
            check=True,
            capture_output=True,
        )

    def tearDown(self):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def _write_config(self, done_checks):
        with open("farnsworth.json", "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "workers": [WORKER],
                    "goal": {
                        "brief": "GOAL.md",
                        "done": done_checks,
                        "improvement_rounds": self.rounds,
                    },
                },
                fh,
            )

    def _attest(self, goal_met=True):
        os.makedirs(".farnsworth", exist_ok=True)
        with open(
            ".farnsworth/attestation.json", "w", encoding="utf-8"
        ) as fh:
            json.dump({"goal_met": goal_met, "reasoning": "test"}, fh)

    def _green_probe(self):
        self.assertEqual(cli.main(["done"]), 0)

    def _proposal(self, round_number=1, text="Better errors.\n", checks=None):
        rel = ".farnsworth/{0}".format(improve.round_dir_name(round_number))
        os.makedirs(rel, exist_ok=True)
        with open(
            os.path.join(rel, "proposal.md"), "w", encoding="utf-8"
        ) as fh:
            fh.write(text)
        if checks is not None:
            with open(
                os.path.join(rel, "done-checks.json"), "w", encoding="utf-8"
            ) as fh:
                json.dump(checks, fh)
        return rel

    def _amend_goal(self, round_number=1):
        with open("GOAL.md", "a", encoding="utf-8") as fh:
            fh.write(
                "\n## Improvement round {0}\n\n- friendlier errors\n".format(
                    round_number
                )
            )


class TestImproveBare(_RepoCase):
    def test_requires_green_probe(self):
        self._attest()
        self.assertEqual(cli.main(["improve"]), 2)

    def test_requires_attestation(self):
        self._green_probe()
        self.assertEqual(cli.main(["improve"]), 2)

    def test_refused_attestation_blocks_round(self):
        self._green_probe()
        self._attest(goal_met=False)
        self.assertEqual(cli.main(["improve"]), 2)

    def test_writes_briefing_and_exits_three(self):
        self._green_probe()
        self._attest()
        self.assertEqual(cli.main(["improve"]), 3)
        with open(
            ".farnsworth/improvement-briefing.md", "r", encoding="utf-8"
        ) as fh:
            briefing = fh.read()
        self.assertIn("round 1 of 2", briefing)
        self.assertIn("APPEND-ONLY", briefing)
        self.assertIn("improvement: none", briefing)
        self.assertIn("improvement-001", briefing)

    def test_no_rounds_remaining_exits_one(self):
        self._green_probe()
        self._attest()
        self._proposal(1)
        self._proposal(2)
        self.assertEqual(cli.main(["improve"]), 1)

    def test_rounds_override_extends_the_budget(self):
        self._green_probe()
        self._attest()
        self._proposal(1)
        self._proposal(2)
        self.assertEqual(cli.main(["improve", "--rounds", "3"]), 3)

    def test_completed_rounds_counted_from_artifacts(self):
        self._proposal(1)
        # An empty proposal dir is an attempt, not a completed round.
        os.makedirs(".farnsworth/improvement-002", exist_ok=True)
        self.assertEqual(improve.completed_rounds(self.repo), 1)


class TestImproveApply(_RepoCase):
    def setUp(self):
        super().setUp()
        self._green_probe()
        self._attest()

    def test_semantic_only_round_installs(self):
        rel = self._proposal(1)
        self._amend_goal(1)
        self.assertEqual(cli.main(["improve", "--apply", rel]), 0)

    def test_mechanical_checks_merge_into_config(self):
        new_check = {
            "name": "friendly-errors",
            "command": ["python3", "-c", "pass"],
        }
        rel = self._proposal(1, checks=[new_check])
        self._amend_goal(1)
        self.assertEqual(cli.main(["improve", "--apply", rel]), 0)
        with open("farnsworth.json", "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        names = [check["name"] for check in raw["goal"]["done"]]
        self.assertEqual(names, ["always-pass", "friendly-errors"])
        # The amended contract parses: the ratchet is a valid config.
        cfg = config.Config.load("farnsworth.json")
        self.assertEqual(len(cfg.goal["done"]), 2)

    def test_non_additive_goal_amendment_rejected(self):
        rel = self._proposal(1)
        with open("GOAL.md", "w", encoding="utf-8") as fh:
            fh.write("# Goal\n\nShip a DIFFERENT thing.\n")
        self.assertEqual(cli.main(["improve", "--apply", rel]), 1)

    def test_unchanged_goal_brief_rejected(self):
        rel = self._proposal(1)
        self.assertEqual(cli.main(["improve", "--apply", rel]), 1)

    def test_check_name_collision_rejected(self):
        rel = self._proposal(1, checks=[PASS_CHECK])
        self._amend_goal(1)
        self.assertEqual(cli.main(["improve", "--apply", rel]), 1)

    def test_malformed_checks_rejected(self):
        rel = self._proposal(1, checks=[{"name": "x", "command": []}])
        self._amend_goal(1)
        self.assertEqual(cli.main(["improve", "--apply", rel]), 1)

    def test_decline_proposal_rejected_by_apply(self):
        rel = self._proposal(1, text="improvement: none\n\nIt is done.\n")
        self.assertEqual(cli.main(["improve", "--apply", rel]), 1)

    def test_missing_proposal_rejected(self):
        os.makedirs(".farnsworth/improvement-001", exist_ok=True)
        self.assertEqual(
            cli.main(["improve", "--apply", ".farnsworth/improvement-001"]),
            1,
        )

    def test_misnamed_dir_rejected(self):
        os.makedirs(".farnsworth/round-1", exist_ok=True)
        with open(
            ".farnsworth/round-1/proposal.md", "w", encoding="utf-8"
        ) as fh:
            fh.write("x\n")
        self.assertEqual(
            cli.main(["improve", "--apply", ".farnsworth/round-1"]), 1
        )


class TestDecline(unittest.TestCase):
    def test_first_nonblank_line_decides(self):
        self.assertTrue(improve.is_decline("\n improvement: none \nwhy\n"))
        self.assertFalse(improve.is_decline("Better errors.\n"))
        self.assertFalse(improve.is_decline("note: improvement: none\n"))


class TestDonePayloadExtension(_RepoCase):
    def test_done_json_carries_round_accounting(self):
        proc = subprocess.run(
            [sys.executable, "-m", "farnsworth", "done", "--json"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": REPO_ROOT},
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["improvement_rounds"],
            {"configured": 2, "completed": 0, "remaining": 2},
        )


if __name__ == "__main__":
    unittest.main()
