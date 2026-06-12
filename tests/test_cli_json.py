"""Tests for the CLI's --json conductor mode (machine-readable phases)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from farnsworth import cli  # noqa: E402

PASS_CHECK = {"name": "always-pass", "command": ["python3", "-c", "pass"]}
FAIL_CHECK = {
    "name": "always-fail",
    "command": ["python3", "-c", "raise SystemExit(3)"],
}


class TestDoneJson(unittest.TestCase):
    """`done --json` emits one JSON object; exit codes match human mode."""

    def _run_done(self, check):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = tmp.name
        subprocess.run(
            ["git", "init", "-q", repo], check=True, capture_output=True
        )
        config_path = os.path.join(repo, "farnsworth.json")
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "workers": [{"id": "w1", "command": ["true"]}],
                    "goal": {"done": [check]},
                },
                fh,
            )
        cwd = os.getcwd()
        stdout = io.StringIO()
        try:
            os.chdir(repo)
            with contextlib.redirect_stdout(stdout):
                code = cli.main(["done", "--json", "--config", config_path])
        finally:
            os.chdir(cwd)
        return code, json.loads(stdout.getvalue()), repo

    def test_passing_done_emits_json_and_exits_zero(self):
        code, payload, repo = self._run_done(PASS_CHECK)
        self.assertEqual(code, 0)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["results"][0]["name"], "always-pass")
        self.assertEqual(
            payload["attestation_briefing"],
            os.path.join(".farnsworth", "attestation-briefing.md"),
        )
        self.assertTrue(
            os.path.exists(os.path.join(repo, payload["recorded"]))
        )

    def test_failing_done_emits_json_and_exits_one(self):
        code, payload, _repo = self._run_done(FAIL_CHECK)
        self.assertEqual(code, 1)
        self.assertFalse(payload["passed"])
        self.assertIsNone(payload["attestation_briefing"])
        self.assertEqual(payload["results"][0]["exit_code"], 3)


if __name__ == "__main__":
    unittest.main()
