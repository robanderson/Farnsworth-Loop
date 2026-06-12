"""Row-level validation producing non-fatal :class:`Warning` objects.

Validation never stops processing (only :class:`~wine_stock_reporter.csv_loader.DataError`
does that, upstream). Every check here returns warnings that the report layer
renders verbatim in its Data Warnings section. Message strings are single-sourced
as module-level constants and imported by tests — never re-typed.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List

from .models import (
    TYPE_DRY_GOODS,
    TYPE_FINISHED_GOODS,
    UNITS_CASES,
    UNITS_EACHES,
    StockRow,
    Warning,
    WineItem,
)
from .parser import (
    EMPTY_DESCRIPTION_MSG,
    UNKNOWN_VARIETY_MSG,
    UNPARSEABLE_BOTTLE_MSG,
    UNPARSEABLE_PACK_MSG,
    parse_description,
)

# Numeric column names checked for blank/non-numeric/negative.
_NUMERIC_FIELDS = ("OnHand", "Allocated", "Pending", "Available")

# Warning message templates (single-sourced; imported by tests).
UNKNOWN_TYPE_MSG = "Unknown Type1 value '{type1}' for item {item}."
UNKNOWN_UNITS_MSG = "Unknown units '{units}' for item {item}."
NON_NUMERIC_MSG = "Non-numeric {field} value '{value}' for item {item}."
NEGATIVE_VALUE_MSG = "Negative {field} value ({value}) for item {item}."
FINISHED_NOT_CASES_MSG = (
    "Finished Goods item {item} is measured in '{units}', not Cases."
)
DRY_GOODS_UNEXPECTED_UNITS_MSG = (
    "Dry Goods item {item} is measured in '{units}', not Eaches."
)
AVAILABLE_GT_ON_HAND_MSG = (
    "Available ({available}) exceeds OnHand ({on_hand}) for item {item}."
)
BALANCE_MISMATCH_MSG = (
    "OnHand - Allocated - Pending ({computed}) does not equal Available "
    "({available}) for item {item}."
)

_KNOWN_TYPES = (TYPE_FINISHED_GOODS, TYPE_DRY_GOODS)
_KNOWN_UNITS = (UNITS_CASES, UNITS_EACHES)


def _raw_cell(row: StockRow, field: str) -> str:
    value = row.raw.get(field)
    return value.strip() if isinstance(value, str) else ""


def validate_rows(rows: List[StockRow]) -> List[Warning]:
    """Validate normalised rows and return all non-fatal warnings.

    Covers (PRD section 20): empty descriptions, non-numeric and negative
    quantities, unknown Type1/Units, Finished Goods not in Cases, Dry Goods in
    unexpected units, unparseable bottle/pack size, unknown variety codes,
    Available greater than OnHand, and the balance mismatch
    ``OnHand - Allocated - Pending != Available``.
    """
    warnings: List[Warning] = []
    for row in rows:
        item = row.item
        line = row.line_number

        # Unknown row type.
        if row.type1 not in _KNOWN_TYPES:
            warnings.append(
                Warning(
                    UNKNOWN_TYPE_MSG.format(type1=row.type1, item=item),
                    item=item,
                    line_number=line,
                )
            )

        # Unknown units.
        if row.units not in _KNOWN_UNITS:
            warnings.append(
                Warning(
                    UNKNOWN_UNITS_MSG.format(units=row.units, item=item),
                    item=item,
                    line_number=line,
                )
            )

        # Units expected per row type.
        if row.is_finished_goods and row.units and row.units != UNITS_CASES:
            warnings.append(
                Warning(
                    FINISHED_NOT_CASES_MSG.format(item=item, units=row.units),
                    item=item,
                    line_number=line,
                )
            )
        if row.is_dry_goods and row.units and row.units != UNITS_EACHES:
            warnings.append(
                Warning(
                    DRY_GOODS_UNEXPECTED_UNITS_MSG.format(item=item, units=row.units),
                    item=item,
                    line_number=line,
                )
            )

        # Numeric cells: non-numeric (raw non-blank but cleaned to None) and
        # negative values.
        _check_numeric(row, warnings)

        # Available > OnHand.
        if (
            row.available is not None
            and row.on_hand is not None
            and row.available > row.on_hand
        ):
            warnings.append(
                Warning(
                    AVAILABLE_GT_ON_HAND_MSG.format(
                        available=row.available,
                        on_hand=row.on_hand,
                        item=item,
                    ),
                    item=item,
                    line_number=line,
                )
            )

        # Balance mismatch: OnHand - Allocated - Pending != Available.
        if (
            row.on_hand is not None
            and row.allocated is not None
            and row.pending is not None
            and row.available is not None
        ):
            computed = row.on_hand - row.allocated - row.pending
            if computed != row.available:
                warnings.append(
                    Warning(
                        BALANCE_MISMATCH_MSG.format(
                            computed=computed,
                            available=row.available,
                            item=item,
                        ),
                        item=item,
                        line_number=line,
                    )
                )

        # Parse-derived warnings (empty/unparseable description, unknown
        # variety, unparseable bottle/pack) only apply to Finished Goods.
        if row.is_finished_goods:
            _, parse_warnings = parse_description(row.description, item)
            for warning in parse_warnings:
                warning.line_number = line
                warnings.append(warning)

    return warnings


def _check_numeric(row: StockRow, warnings: List[Warning]) -> None:
    item = row.item
    line = row.line_number
    for field in _NUMERIC_FIELDS:
        raw = _raw_cell(row, field)
        cleaned = getattr(row, _FIELD_ATTR[field])
        if raw != "" and cleaned is None:
            warnings.append(
                Warning(
                    NON_NUMERIC_MSG.format(field=field, value=raw, item=item),
                    item=item,
                    line_number=line,
                )
            )
        elif cleaned is not None and cleaned < Decimal("0"):
            warnings.append(
                Warning(
                    NEGATIVE_VALUE_MSG.format(field=field, value=cleaned, item=item),
                    item=item,
                    line_number=line,
                )
            )


_FIELD_ATTR = {
    "OnHand": "on_hand",
    "Allocated": "allocated",
    "Pending": "pending",
    "Available": "available",
}


# Re-exported so callers/tests that already imported parser warning constants
# do not need to know which module produced a given warning.
__all__ = [
    "validate_rows",
    "UNKNOWN_TYPE_MSG",
    "UNKNOWN_UNITS_MSG",
    "NON_NUMERIC_MSG",
    "NEGATIVE_VALUE_MSG",
    "FINISHED_NOT_CASES_MSG",
    "DRY_GOODS_UNEXPECTED_UNITS_MSG",
    "AVAILABLE_GT_ON_HAND_MSG",
    "BALANCE_MISMATCH_MSG",
    "EMPTY_DESCRIPTION_MSG",
    "UNKNOWN_VARIETY_MSG",
    "UNPARSEABLE_BOTTLE_MSG",
    "UNPARSEABLE_PACK_MSG",
]
