"""CSV loading, required-column validation, and numeric normalisation.

A :class:`DataError` is raised for fatal conditions (missing file, unreadable
CSV, missing required column). The CLI turns these into a one-line
``Error: ...`` on stderr with exit code 1 and no traceback. Per-cell numeric
problems are non-fatal: they leave the value ``None`` and are surfaced as
validation warnings downstream, not exceptions here.
"""

from __future__ import annotations

import csv
import os
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from .models import StockRow

# Columns that MUST be present for processing to proceed.
REQUIRED_COLUMNS = (
    "Type1",
    "Item",
    "Description",
    "OnHand",
    "Warehouse",
    "Allocated",
    "Pending",
    "Available",
    "Units",
)

# Optional columns: may be absent or empty.
OPTIONAL_COLUMNS = ("ClientStockCode", "ClientStockDescription", "Lot")

# Message templates (single-sourced; imported by tests).
MISSING_FILE_MSG = "input file '{path}' was not found."
NOT_A_FILE_MSG = "input path '{path}' is not a readable file."
MISSING_COLUMN_MSG = "required column '{column}' was not found in CSV."
EMPTY_CSV_MSG = "CSV file '{path}' has no header row."


class DataError(Exception):
    """Fatal data/file error. Carries a clean, user-facing message."""


def clean_numeric(value: Optional[str]) -> Optional[Decimal]:
    """Parse a possibly-messy numeric cell into a :class:`~decimal.Decimal`.

    Handles thousands separators (``"2,216.50"``), surrounding whitespace,
    and blank cells (which return ``None``). Returns ``None`` when the cell
    cannot be parsed as a number (the caller decides whether that warrants a
    warning); negative values parse normally (warned about elsewhere, never
    crash here).
    """
    if value is None:
        return None
    text = value.strip().replace(",", "")
    if text == "":
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def load_csv(path: str) -> List[StockRow]:
    """Load and normalise a stock CSV into :class:`StockRow` objects.

    Raises :class:`DataError` for a missing file, unreadable file, empty
    header, or any missing required column.
    """
    if not os.path.exists(path):
        raise DataError(MISSING_FILE_MSG.format(path=path))
    if not os.path.isfile(path):
        raise DataError(NOT_A_FILE_MSG.format(path=path))

    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise DataError(EMPTY_CSV_MSG.format(path=path))
            _validate_columns(fieldnames)
            rows: List[StockRow] = []
            # line_number: 1 is the header, so data starts at 2.
            for offset, record in enumerate(reader, start=2):
                rows.append(_to_stock_row(record, offset))
            return rows
    except DataError:
        raise
    except OSError as exc:
        raise DataError(NOT_A_FILE_MSG.format(path=path)) from exc
    except csv.Error as exc:
        raise DataError(f"could not read CSV '{path}': {exc}") from exc


def _validate_columns(fieldnames) -> None:
    present = {name.strip() for name in fieldnames if name is not None}
    for column in REQUIRED_COLUMNS:
        if column not in present:
            raise DataError(MISSING_COLUMN_MSG.format(column=column))


def _to_stock_row(record: dict, line_number: int) -> StockRow:
    def cell(name: str) -> str:
        value = record.get(name)
        return value.strip() if isinstance(value, str) else ""

    return StockRow(
        type1=cell("Type1"),
        item=cell("Item"),
        description=cell("Description"),
        client_stock_code=cell("ClientStockCode"),
        client_stock_description=cell("ClientStockDescription"),
        lot=cell("Lot"),
        on_hand=clean_numeric(record.get("OnHand")),
        warehouse=cell("Warehouse"),
        allocated=clean_numeric(record.get("Allocated")),
        pending=clean_numeric(record.get("Pending")),
        available=clean_numeric(record.get("Available")),
        units=cell("Units"),
        line_number=line_number,
        raw=dict(record),
    )
