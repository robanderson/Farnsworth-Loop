"""Data models for the Wine Stock Report Generator.

These are presentation-neutral data contracts: dataclasses store plain values
(strings, Decimals, Nones). No presentation glyphs, emoji, or markup live in
any field here; the report layer owns all rendering. A ``None`` 9LE means
"no 9-litre-equivalent applies" (dry goods, or a row whose size could not be
parsed); the report renders that absence as the placeholder defined in
:mod:`wine_stock_reporter.report`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

# Row type constants (values of the CSV ``Type1`` column).
TYPE_FINISHED_GOODS = "Finished Goods"
TYPE_DRY_GOODS = "Dry Goods"

# Unit constants (values of the CSV ``Units`` column).
UNITS_CASES = "Cases"
UNITS_EACHES = "Eaches"

# Stock basis constants.
BASIS_ON_HAND = "OnHand"
BASIS_AVAILABLE = "Available"
VALID_BASES = (BASIS_ON_HAND, BASIS_AVAILABLE)

# Grouping constants.
GROUP_VARIETY = "variety"
GROUP_VINTAGE = "vintage"
GROUP_MARKET = "market"
GROUP_PACK_SIZE = "pack_size"
GROUP_LOT = "lot"
GROUP_NONE = "none"
VALID_GROUPINGS = (
    GROUP_VARIETY,
    GROUP_VINTAGE,
    GROUP_MARKET,
    GROUP_PACK_SIZE,
    GROUP_LOT,
    GROUP_NONE,
)

# Placeholder used in models/reports when a parsed field is absent.
UNKNOWN = "Unknown"


@dataclass
class StockRow:
    """A single normalised CSV row.

    Numeric fields are :class:`~decimal.Decimal` (``None`` if the source cell
    was blank). ``raw`` preserves the original cell strings for diagnostics.
    """

    type1: str
    item: str
    description: str
    client_stock_code: str
    client_stock_description: str
    lot: str
    on_hand: Optional[Decimal]
    warehouse: str
    allocated: Optional[Decimal]
    pending: Optional[Decimal]
    available: Optional[Decimal]
    units: str
    line_number: int = 0
    raw: dict = field(default_factory=dict)

    @property
    def is_finished_goods(self) -> bool:
        return self.type1 == TYPE_FINISHED_GOODS

    @property
    def is_dry_goods(self) -> bool:
        return self.type1 == TYPE_DRY_GOODS


@dataclass
class ParsedWine:
    """Wine metadata parsed from a Finished Goods ``Description``.

    All fields default to the absent/unknown sentinels so a description that
    fails to parse still yields a usable object (the parser never raises).
    """

    prefix: Optional[str] = None
    vintage: Optional[str] = None  # four-digit string, or "NV", or None
    variety_code: Optional[str] = None
    variety: str = UNKNOWN
    brand_code: Optional[str] = None
    market: Optional[str] = None
    bottle_size_ml: Optional[int] = None
    pack_size: Optional[int] = None
    extra_description: Optional[str] = None


@dataclass
class WineItem:
    """A Finished Goods row joined with its parsed metadata and computed 9LE.

    ``nine_litre_equivalent`` is ``None`` when it could not be computed
    (bottle size or pack size unparseable). Such rows still appear in detail
    tables (9LE rendered as the placeholder) and still contribute their cases
    to case totals, but are excluded from 9LE totals.
    """

    row: StockRow
    parsed: ParsedWine
    nine_litre_equivalent: Optional[Decimal] = None

    @property
    def item(self) -> str:
        return self.row.item

    @property
    def description(self) -> str:
        return self.row.description

    def cases(self, basis: str) -> Optional[Decimal]:
        """Cases on the chosen basis (``OnHand``/``Available``)."""
        if basis == BASIS_ON_HAND:
            return self.row.on_hand
        return self.row.available


@dataclass
class Warning:
    """A non-fatal validation/parse warning.

    ``message`` is a complete, presentation-neutral sentence; the report layer
    renders it verbatim as a bullet.
    """

    message: str
    item: str = ""
    line_number: int = 0


@dataclass
class ReportOptions:
    """Effective report options after CLI parsing and interactive prompting."""

    basis: str = BASIS_AVAILABLE
    group_by: str = GROUP_VARIETY
    include_dry_goods: bool = True
    low_stock_warnings: bool = True
    low_stock_threshold: Decimal = Decimal("10")
    output_path: str = "stock-report.md"
