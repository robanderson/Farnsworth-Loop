"""Command-line interface: argument parsing, interactive prompts, orchestration.

The CLI is the only module that touches the terminal, and all of its I/O is
injectable (``input_fn``/``output_fn``) so tests run hermetically. Argparse
owns usage handling: ``--help`` exits 0 and a usage error exits 2 — we never
wrap ``parse_args`` in ``try/except SystemExit``. Data/file problems surface as
a one-line ``Error: ...`` on stderr with exit code 1 and no traceback.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from typing import Callable, List, Optional

from .csv_loader import DataError, load_csv
from .models import (
    BASIS_AVAILABLE,
    BASIS_ON_HAND,
    GROUP_VARIETY,
    TYPE_DRY_GOODS,
    TYPE_FINISHED_GOODS,
    VALID_BASES,
    VALID_GROUPINGS,
    ReportOptions,
    StockRow,
)
from .report import render_report
from .validation import validate_rows

PROG = "wine_stock_reporter"
DEFAULT_OUTPUT = "stock-report.md"
DEFAULT_THRESHOLD = "10"

# User-facing fixed strings (single-sourced; imported by tests).
DETECTED_HEADER = "Detected:"
REPORT_OPTIONS_HEADER = "Report options:"
WRITTEN_MSG = "Report written to {path}"
LOADED_MSG = "Loaded {path}."
INVALID_CHOICE_MSG = "Please answer one of: {choices}."
INVALID_YES_NO_MSG = "Please answer yes or no."
INVALID_NUMBER_MSG = "Please enter a number (e.g. 10 or 12.5)."

_YES = {"y", "yes", "true", "1"}
_NO = {"n", "no", "false", "0"}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser. The flag set is exact and closed."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Convert a warehouse stock-on-hand CSV into a readable Markdown "
            "stock report (9LE totals, grouping summaries, low-stock and data "
            "warnings)."
        ),
    )
    parser.add_argument("csv_path", metavar="CSV_PATH", help="path to the stock CSV")
    parser.add_argument(
        "--basis",
        choices=VALID_BASES,
        default=BASIS_AVAILABLE,
        help="stock basis for wine totals (default: %(default)s)",
    )
    parser.add_argument(
        "--group-by",
        choices=VALID_GROUPINGS,
        default=GROUP_VARIETY,
        help="grouping for the primary wine summary (default: %(default)s)",
    )

    dry = parser.add_mutually_exclusive_group()
    dry.add_argument(
        "--include-dry-goods",
        dest="include_dry_goods",
        action="store_true",
        default=True,
        help="include the Dry Goods section (default)",
    )
    dry.add_argument(
        "--no-dry-goods",
        dest="include_dry_goods",
        action="store_false",
        help="omit the Dry Goods section",
    )

    low = parser.add_mutually_exclusive_group()
    low.add_argument(
        "--low-stock-warnings",
        dest="low_stock_warnings",
        action="store_true",
        default=True,
        help="show low-stock warnings (default)",
    )
    low.add_argument(
        "--no-low-stock-warnings",
        dest="low_stock_warnings",
        action="store_false",
        help="hide low-stock warnings",
    )

    parser.add_argument(
        "--low-stock-threshold",
        type=_threshold_type,
        default=Decimal(DEFAULT_THRESHOLD),
        metavar="N",
        help="low-stock threshold in 9LE (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        metavar="PATH",
        help="output Markdown path (default: %(default)s)",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="skip all prompts and use the effective option values",
    )
    return parser


def _threshold_type(value: str) -> Decimal:
    try:
        return Decimal(value.strip().replace(",", ""))
    except (InvalidOperation, ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            f"invalid threshold {value!r}: expected a number"
        )


def options_from_args(args: argparse.Namespace) -> ReportOptions:
    """Build the effective :class:`ReportOptions` from parsed CLI args."""
    return ReportOptions(
        basis=args.basis,
        group_by=args.group_by,
        include_dry_goods=args.include_dry_goods,
        low_stock_warnings=args.low_stock_warnings,
        low_stock_threshold=args.low_stock_threshold,
        output_path=args.output,
    )


# --------------------------------------------------------------------------- #
# Interactive prompting (all I/O injectable).
# --------------------------------------------------------------------------- #


def _detected_summary(rows: List[StockRow]) -> List[str]:
    types: List[str] = []
    if any(r.type1 == TYPE_FINISHED_GOODS for r in rows):
        types.append("Finished Goods rows")
    if any(r.type1 == TYPE_DRY_GOODS for r in rows):
        types.append("Dry Goods rows")
    warehouses: List[str] = []
    for r in rows:
        if r.warehouse and r.warehouse not in warehouses:
            warehouses.append(r.warehouse)
    units: List[str] = []
    for r in rows:
        if r.units and r.units not in units:
            units.append(r.units)

    lines = [DETECTED_HEADER]
    for t in types:
        lines.append(f"- {t}")
    lines.append(f"- Warehouse: {', '.join(warehouses) if warehouses else 'Unknown'}")
    lines.append(f"- Units: {', '.join(units) if units else 'Unknown'}")
    return lines


class _EOFReached(Exception):
    """Raised internally when the input stream ends; accept all defaults."""


def _ask(
    prompt: str,
    default_display: str,
    convert: Callable[[str], object],
    error_msg_provider: Callable[[], str],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
):
    """Prompt until a valid answer is given; Enter accepts the default.

    ``convert`` returns the converted value or raises ``ValueError`` to
    re-prompt. EOF raises :class:`_EOFReached` so the caller can accept the
    default for this and all remaining questions.
    """
    full_prompt = f"{prompt} [{default_display}]: "
    while True:
        try:
            raw = input_fn(full_prompt)
        except EOFError:
            raise _EOFReached
        if raw is None:
            raise _EOFReached
        text = raw.strip()
        if text == "":
            return _DEFAULT
        try:
            return convert(text)
        except ValueError:
            output_fn(error_msg_provider())


# Sentinel meaning "user accepted the default".
_DEFAULT = object()


def _convert_choice(valid: List[str]) -> Callable[[str], str]:
    lowered = {v.lower(): v for v in valid}

    def convert(text: str) -> str:
        match = lowered.get(text.lower())
        if match is None:
            raise ValueError(text)
        return match

    return convert


def _convert_yes_no(text: str) -> bool:
    low = text.lower()
    if low in _YES:
        return True
    if low in _NO:
        return False
    raise ValueError(text)


def _convert_threshold(text: str) -> Decimal:
    try:
        return Decimal(text.replace(",", ""))
    except (InvalidOperation, ValueError):
        raise ValueError(text)


def _convert_filename(text: str) -> str:
    return text


def prompt_options(
    rows: List[StockRow],
    defaults: ReportOptions,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> ReportOptions:
    """Run the six PRD section 17 questions and return effective options.

    Each question's default is the corresponding value in ``defaults`` (the
    effective CLI option value). EOF at any point accepts the default for that
    question and all remaining questions.
    """
    for line in _detected_summary(rows):
        output_fn(line)
    output_fn("")
    output_fn(REPORT_OPTIONS_HEADER)

    result = ReportOptions(
        basis=defaults.basis,
        group_by=defaults.group_by,
        include_dry_goods=defaults.include_dry_goods,
        low_stock_warnings=defaults.low_stock_warnings,
        low_stock_threshold=defaults.low_stock_threshold,
        output_path=defaults.output_path,
    )

    questions = [
        (
            "1. Use OnHand or Available stock for wine totals?",
            defaults.basis,
            _convert_choice(list(VALID_BASES)),
            lambda: INVALID_CHOICE_MSG.format(choices=", ".join(VALID_BASES)),
            "basis",
        ),
        (
            "2. Include Dry Goods section?",
            "yes" if defaults.include_dry_goods else "no",
            _convert_yes_no,
            lambda: INVALID_YES_NO_MSG,
            "include_dry_goods",
        ),
        (
            "3. Group primary wine summary by variety, vintage, market, "
            "pack_size, lot, or none?",
            defaults.group_by,
            _convert_choice(list(VALID_GROUPINGS)),
            lambda: INVALID_CHOICE_MSG.format(choices=", ".join(VALID_GROUPINGS)),
            "group_by",
        ),
        (
            "4. Include low-stock warnings?",
            "yes" if defaults.low_stock_warnings else "no",
            _convert_yes_no,
            lambda: INVALID_YES_NO_MSG,
            "low_stock_warnings",
        ),
        (
            "5. Low-stock threshold in 9LE?",
            str(defaults.low_stock_threshold),
            _convert_threshold,
            lambda: INVALID_NUMBER_MSG,
            "low_stock_threshold",
        ),
        (
            "6. Output filename?",
            defaults.output_path,
            _convert_filename,
            lambda: INVALID_NUMBER_MSG,
            "output_path",
        ),
    ]

    try:
        for prompt, default_display, convert, err, attr in questions:
            answer = _ask(prompt, default_display, convert, err, input_fn, output_fn)
            if answer is not _DEFAULT:
                setattr(result, attr, answer)
    except _EOFReached:
        # Accept the default for this and all remaining questions.
        pass

    return result


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #


def run(
    argv: Optional[List[str]] = None,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Parse args, load the CSV, (optionally) prompt, render, and write.

    Returns the process exit code. ``SystemExit`` from argparse propagates so
    ``--help`` exits 0 and a usage error exits 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        rows = load_csv(args.csv_path)
    except DataError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_fn(LOADED_MSG.format(path=args.csv_path))

    defaults = options_from_args(args)
    if args.no_interactive:
        options = defaults
    else:
        output_fn("")
        options = prompt_options(rows, defaults, input_fn, output_fn)

    warnings = validate_rows(rows)
    report_text = render_report(
        rows,
        options,
        extra_warnings=warnings,
        source_file=args.csv_path,
    )

    try:
        with open(options.output_path, "w", encoding="utf-8") as handle:
            handle.write(report_text)
    except OSError as exc:
        print(f"Error: could not write report to '{options.output_path}': {exc}",
              file=sys.stderr)
        return 1

    output_fn(WRITTEN_MSG.format(path=options.output_path))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Console entry point used by ``python -m wine_stock_reporter``."""
    return run(argv)
