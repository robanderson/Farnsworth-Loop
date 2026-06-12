"""Shared test helpers.

Rows are constructed directly with pinned values (never loaded from the fixture
and then overwritten), so each test owns exactly the data it asserts on.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from wine_stock_reporter.models import (
    TYPE_FINISHED_GOODS,
    UNITS_CASES,
    StockRow,
)


def make_row(
    *,
    type1: str = TYPE_FINISHED_GOODS,
    item: str = "100001",
    description: str = "FV 22 CHR EP NZ 750ml/12p",
    client_stock_code: str = "",
    client_stock_description: str = "",
    lot: str = "W00000",
    on_hand: Optional[Decimal] = Decimal("10.00"),
    warehouse: str = "Marlborough",
    allocated: Optional[Decimal] = Decimal("0.00"),
    pending: Optional[Decimal] = Decimal("0.00"),
    available: Optional[Decimal] = Decimal("10.00"),
    units: str = UNITS_CASES,
    line_number: int = 2,
    raw: Optional[dict] = None,
) -> StockRow:
    """Build a :class:`StockRow` with pinned defaults.

    ``raw`` defaults to a dict mirroring the numeric/string cells so that
    validation (which reads raw cells to distinguish blank from non-numeric)
    behaves as if the row came from a clean CSV.
    """
    if raw is None:
        raw = {
            "Type1": type1,
            "Item": item,
            "Description": description,
            "ClientStockCode": client_stock_code,
            "ClientStockDescription": client_stock_description,
            "Lot": lot,
            "OnHand": "" if on_hand is None else str(on_hand),
            "Warehouse": warehouse,
            "Allocated": "" if allocated is None else str(allocated),
            "Pending": "" if pending is None else str(pending),
            "Available": "" if available is None else str(available),
            "Units": units,
        }
    return StockRow(
        type1=type1,
        item=item,
        description=description,
        client_stock_code=client_stock_code,
        client_stock_description=client_stock_description,
        lot=lot,
        on_hand=on_hand,
        warehouse=warehouse,
        allocated=allocated,
        pending=pending,
        available=available,
        units=units,
        line_number=line_number,
        raw=raw,
    )
