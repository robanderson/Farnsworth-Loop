"""9LE calculation, aggregation, totals, and low-stock identification.

All arithmetic uses :class:`~decimal.Decimal`; floats appear only at the
formatting edge in the report layer. 9LE for a row is::

    litres = cases * pack_size * (bottle_size_ml / 1000)
    9LE = litres / 9

A row whose pack or bottle size is unknown gets ``None`` for 9LE — it is
excluded from 9LE totals but still counts toward case totals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from .models import (
    BASIS_AVAILABLE,
    GROUP_LOT,
    GROUP_MARKET,
    GROUP_NONE,
    GROUP_PACK_SIZE,
    GROUP_VARIETY,
    GROUP_VINTAGE,
    UNKNOWN,
    ParsedWine,
    StockRow,
    WineItem,
)
from .parser import parse_description

_LITRES_PER_ML = Decimal("1000")
_NINE = Decimal("9")

# Sentinel group-key label for items missing the grouping attribute.
GROUP_UNKNOWN = UNKNOWN


def nine_litre_equivalent(
    cases: Optional[Decimal],
    bottle_size_ml: Optional[int],
    pack_size: Optional[int],
) -> Optional[Decimal]:
    """Return the 9LE for ``cases`` of a given bottle/pack, or ``None``.

    ``None`` is returned when cases, bottle size, or pack size is missing —
    signalling "no 9LE applies", which the report renders as a placeholder.
    """
    if cases is None or bottle_size_ml is None or pack_size is None:
        return None
    litres = cases * Decimal(pack_size) * (Decimal(bottle_size_ml) / _LITRES_PER_ML)
    return litres / _NINE


def build_wine_items(rows: List[StockRow], basis: str = BASIS_AVAILABLE) -> List[WineItem]:
    """Parse Finished Goods rows and compute their 9LE on the chosen basis.

    Only rows whose ``Type1`` is Finished Goods are returned. The 9LE is
    computed against the cases on ``basis``; rows that lack a parseable size
    receive ``None``.
    """
    items: List[WineItem] = []
    for row in rows:
        if not row.is_finished_goods:
            continue
        parsed, _ = parse_description(row.description, row.item)
        item = WineItem(row=row, parsed=parsed)
        cases = item.cases(basis)
        item.nine_litre_equivalent = nine_litre_equivalent(
            cases, parsed.bottle_size_ml, parsed.pack_size
        )
        items.append(item)
    return items


@dataclass
class GroupAggregate:
    """Aggregated stock for one grouping key."""

    key: str
    rows: int = 0
    cases: Decimal = field(default_factory=lambda: Decimal("0"))
    nine_le: Decimal = field(default_factory=lambda: Decimal("0"))


def _group_key(parsed: ParsedWine, group_by: str) -> str:
    if group_by == GROUP_VARIETY:
        return parsed.variety or UNKNOWN
    if group_by == GROUP_VINTAGE:
        return parsed.vintage or UNKNOWN
    if group_by == GROUP_MARKET:
        return parsed.market or UNKNOWN
    if group_by == GROUP_PACK_SIZE:
        return f"{parsed.pack_size}p" if parsed.pack_size is not None else UNKNOWN
    raise ValueError(f"unsupported group_by for parsed key: {group_by!r}")


def aggregate(items: List[WineItem], group_by: str, basis: str) -> List[GroupAggregate]:
    """Aggregate wine items by the chosen grouping.

    Returns an empty list for ``none``. For ``lot`` the row's Lot field is the
    key. Raises :class:`ValueError` for an unknown grouping rather than
    silently falling back to an ungrouped view.
    """
    if group_by == GROUP_NONE:
        return []
    if group_by not in (
        GROUP_VARIETY,
        GROUP_VINTAGE,
        GROUP_MARKET,
        GROUP_PACK_SIZE,
        GROUP_LOT,
    ):
        raise ValueError(f"unknown grouping: {group_by!r}")

    buckets: dict[str, GroupAggregate] = {}
    for item in items:
        if group_by == GROUP_LOT:
            key = item.row.lot or UNKNOWN
        else:
            key = _group_key(item.parsed, group_by)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = GroupAggregate(key=key)
            buckets[key] = bucket
        bucket.rows += 1
        cases = item.cases(basis)
        if cases is not None:
            bucket.cases += cases
        if item.nine_litre_equivalent is not None:
            bucket.nine_le += item.nine_litre_equivalent

    # Stable, business-readable order: 9LE descending, then key.
    return sorted(buckets.values(), key=lambda g: (-g.nine_le, g.key))


@dataclass
class Totals:
    """Whole-of-report wine totals on the chosen basis."""

    finished_rows: int = 0
    dry_rows: int = 0
    total_nine_le: Decimal = field(default_factory=lambda: Decimal("0"))
    total_available_cases: Decimal = field(default_factory=lambda: Decimal("0"))
    total_allocated_cases: Decimal = field(default_factory=lambda: Decimal("0"))
    total_pending_cases: Decimal = field(default_factory=lambda: Decimal("0"))
    total_on_hand_cases: Decimal = field(default_factory=lambda: Decimal("0"))
    lowest_stock_item: Optional[WineItem] = None


def compute_totals(items: List[WineItem], dry_rows: int, basis: str) -> Totals:
    """Compute whole-report totals and the lowest-stock wine item.

    The lowest-stock item is the one with the smallest computable 9LE on the
    chosen basis (rows without a 9LE are not eligible to be "lowest").
    """
    totals = Totals(finished_rows=len(items), dry_rows=dry_rows)
    lowest: Optional[WineItem] = None
    lowest_value: Optional[Decimal] = None
    for item in items:
        if item.nine_litre_equivalent is not None:
            totals.total_nine_le += item.nine_litre_equivalent
            if lowest_value is None or item.nine_litre_equivalent < lowest_value:
                lowest_value = item.nine_litre_equivalent
                lowest = item
        if item.row.available is not None:
            totals.total_available_cases += item.row.available
        if item.row.allocated is not None:
            totals.total_allocated_cases += item.row.allocated
        if item.row.pending is not None:
            totals.total_pending_cases += item.row.pending
        if item.row.on_hand is not None:
            totals.total_on_hand_cases += item.row.on_hand
    totals.lowest_stock_item = lowest
    return totals


def low_stock_items(
    items: List[WineItem], threshold: Decimal, basis: str
) -> List[WineItem]:
    """Return wine items whose 9LE on the chosen basis is below ``threshold``.

    Items without a computable 9LE are not low-stock candidates (their stock
    level is unknown, not low). Sorted ascending by 9LE so the scarcest items
    lead.
    """
    low = [
        item
        for item in items
        if item.nine_litre_equivalent is not None
        and item.nine_litre_equivalent < threshold
    ]
    return sorted(low, key=lambda i: i.nine_litre_equivalent)
