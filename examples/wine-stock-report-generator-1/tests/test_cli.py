"""CLI tests: argparse contract, interactive prompts, exit codes, smoke test."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from decimal import Decimal

from wine_stock_reporter import cli
from wine_stock_reporter.models import (
    BASIS_AVAILABLE,
    BASIS_ON_HAND,
    GROUP_VINTAGE,
    ReportOptions,
)

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "stock_sample.csv",
)


def _scripted_input(answers):
    """Return an input_fn that yields ``answers`` then raises EOFError."""
    it = iter(answers)

    def input_fn(_prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return input_fn


def _collector():
    lines = []
    return lines, lambda line="": lines.append(line)


class ArgparseContractTests(unittest.TestCase):
    def test_help_exits_zero(self):
        import contextlib

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                cli.build_parser().parse_args(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_unknown_flag_exits_two(self):
        import contextlib

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                cli.build_parser().parse_args(["x.csv", "--nope"])
        self.assertEqual(ctx.exception.code, 2)

    def test_defaults(self):
        args = cli.build_parser().parse_args(["x.csv"])
        opts = cli.options_from_args(args)
        self.assertEqual(opts.basis, BASIS_AVAILABLE)
        self.assertEqual(opts.group_by, "variety")
        self.assertTrue(opts.include_dry_goods)
        self.assertTrue(opts.low_stock_warnings)
        self.assertEqual(opts.low_stock_threshold, Decimal("10"))
        self.assertEqual(opts.output_path, "stock-report.md")

    def test_no_dry_goods_flag(self):
        args = cli.build_parser().parse_args(["x.csv", "--no-dry-goods"])
        self.assertFalse(args.include_dry_goods)

    def test_threshold_with_separator(self):
        args = cli.build_parser().parse_args(["x.csv", "--low-stock-threshold", "1,000"])
        self.assertEqual(args.low_stock_threshold, Decimal("1000"))


class MissingFileTests(unittest.TestCase):
    def test_missing_file_exits_one_with_error(self):
        err = io.StringIO()
        import contextlib

        missing = os.path.join(tempfile.gettempdir(), "no-such-file-abc.csv")
        with contextlib.redirect_stderr(err):
            code = cli.run([missing, "--no-interactive"], output_fn=lambda *_: None)
        self.assertEqual(code, 1)
        self.assertTrue(err.getvalue().startswith("Error: "))
        self.assertNotIn("Traceback", err.getvalue())


class InteractivePromptTests(unittest.TestCase):
    def _rows(self):
        from tests.helpers import make_row

        return [make_row(item="1")]

    def test_enter_accepts_defaults(self):
        rows = self._rows()
        _lines, out = _collector()
        defaults = ReportOptions(basis=BASIS_AVAILABLE, group_by="variety")
        # Six empty answers -> all defaults kept.
        result = cli.prompt_options(
            rows, defaults, _scripted_input(["", "", "", "", "", ""]), out
        )
        self.assertEqual(result.basis, BASIS_AVAILABLE)
        self.assertEqual(result.group_by, "variety")
        self.assertTrue(result.include_dry_goods)

    def test_answers_override_defaults(self):
        rows = self._rows()
        _lines, out = _collector()
        defaults = ReportOptions()
        result = cli.prompt_options(
            rows,
            defaults,
            _scripted_input(["OnHand", "no", "vintage", "no", "25", "out.md"]),
            out,
        )
        self.assertEqual(result.basis, BASIS_ON_HAND)
        self.assertFalse(result.include_dry_goods)
        self.assertEqual(result.group_by, GROUP_VINTAGE)
        self.assertFalse(result.low_stock_warnings)
        self.assertEqual(result.low_stock_threshold, Decimal("25"))
        self.assertEqual(result.output_path, "out.md")

    def test_invalid_then_valid_reprompts(self):
        rows = self._rows()
        lines, out = _collector()
        defaults = ReportOptions()
        # First answer to Q1 invalid, then valid; rest default.
        result = cli.prompt_options(
            rows, defaults, _scripted_input(["bogus", "OnHand", "", "", "", "", ""]), out
        )
        self.assertEqual(result.basis, BASIS_ON_HAND)
        self.assertIn(
            cli.INVALID_CHOICE_MSG.format(choices="OnHand, Available"), lines
        )

    def test_eof_accepts_remaining_defaults(self):
        rows = self._rows()
        _lines, out = _collector()
        defaults = ReportOptions(basis=BASIS_AVAILABLE, group_by="variety")
        # No answers at all -> EOF immediately -> all defaults.
        result = cli.prompt_options(rows, defaults, _scripted_input([]), out)
        self.assertEqual(result.basis, BASIS_AVAILABLE)
        self.assertEqual(result.output_path, defaults.output_path)


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def _out(self, name="report.md"):
        return os.path.join(self._tmp, name)

    def test_no_interactive_writes_report(self):
        out = self._out()
        _lines, sink = _collector()
        code = cli.run(
            [FIXTURE, "--no-interactive", "--output", out],
            output_fn=sink,
        )
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out))
        with open(out, encoding="utf-8") as handle:
            text = handle.read()
        self.assertTrue(text.strip())
        for heading in (
            "# Wine Stock Report",
            "## Executive Summary",
            "## Detailed Finished Goods",
            "## Data Warnings",
        ):
            self.assertIn(heading, text)

    def test_eof_run_uses_all_defaults_and_writes(self):
        # Simulate `printf '' | ...` -> interactive but immediate EOF.
        _lines, sink = _collector()
        # Run interactively (no --no-interactive) with an EOF input stream.
        # Output goes to default path; redirect cwd to the temp dir.
        cwd = os.getcwd()
        os.chdir(self._tmp)
        try:
            code = cli.run(
                [FIXTURE],
                input_fn=_scripted_input([]),
                output_fn=sink,
            )
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "stock-report.md")))

    def test_group_none_omits_grouping_but_keeps_other_sections(self):
        out = self._out("none.md")
        _lines, sink = _collector()
        code = cli.run(
            [FIXTURE, "--no-interactive", "--group-by", "none", "--output", out],
            output_fn=sink,
        )
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("## Stock by", text)
        self.assertIn("## Detailed Finished Goods", text)


if __name__ == "__main__":
    unittest.main()
