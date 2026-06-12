"""Markdown report rendering.

This is the only layer that turns data into presentation. It owns every
user-facing heading and the placeholder for an absent 9LE. Decimals are
formatted to two places here (the sole float-free formatting edge); the
underlying calculations stay in :class:`~decimal.Decimal`.

Report structure (PRD section 19):

    # Wine Stock Report
    <header: generated date, source file, warehouse(s), stock basis>
    ## Executive Summary
    ## Stock by <Grouping>        (omitted entirely when group-by is "none")
    ## Detailed Finished Goods
    ## Low Stock Warnings         (only when enabled)
    ## Dry Goods Summary          (only when included)
    ## Data Warnings
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Sequence

from .calculations import (
    GroupAggregate,
    Totals,
    aggregate,
    compute_totals,
    low_stock_items,
)
from .models import (
    GROUP_LOT,
    GROUP_MARKET,
    GROUP_NONE,
    GROUP_PACK_SIZE,
    GROUP_VARIETY,
    GROUP_VINTAGE,
    ReportOptions,
    StockRow,
    Warning,
    WineItem,
)

# Placeholder rendered where a 9LE does not apply or could not be computed.
NO_VALUE = "—"

# Headings (single-sourced; imported by tests).
TITLE = "# Wine Stock Report"
H_EXEC_SUMMARY = "## Executive Summary"
H_DETAILED = "## Detailed Finished Goods"
H_LOW_STOCK = "## Low Stock Warnings"
H_DRY_GOODS = "## Dry Goods Summary"
H_DATA_WARNINGS = "## Data Warnings"

# Per-grouping section headings.
_GROUP_HEADINGS = {
    GROUP_VARIETY: "## Stock by Variety",
    GROUP_VINTAGE: "## Stock by Vintage",
    GROUP_MARKET: "## Stock by Market",
    GROUP_PACK_SIZE: "## Stock by Pack Size",
    GROUP_LOT: "## Stock by Lot",
}

# Friendly column label for the grouping table's first column.
_GROUP_COLUMN = {
    GROUP_VARIETY: "Variety",
    GROUP_VINTAGE: "Vintage",
    GROUP_MARKET: "Market",
    GROUP_PACK_SIZE: "Pack Size",
    GROUP_LOT: "Lot",
}

# Fixed lines / phrases (single-sourced).
NO_LOW_STOCK_LINE = "No items are below the low-stock threshold."
NO_DATA_WARNINGS_LINE = "No data warnings."
NO_FINISHED_GOODS_LINE = "_No finished goods rows._"
NO_DRY_GOODS_LINE = "_No dry goods rows._"
NO_GROUP_DATA_LINE = "_No finished goods to summarise._"


def group_heading(group_by: str) -> str:
    """Return the markdown heading for the chosen grouping section."""
    return _GROUP_HEADINGS[group_by]


def fmt_decimal(value: Optional[Decimal]) -> str:
    """Format a Decimal to exactly two places, or the placeholder if ``None``."""
    if value is None:
        return NO_VALUE
    quantised = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantised:,}"


def _table(header: Sequence[str], aligns: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    """Render a markdown table. ``aligns`` entries are 'l' or 'r'."""
    sep = []
    for align in aligns:
        sep.append("---:" if align == "r" else "---")
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(sep) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def render_report(
    rows: List[StockRow],
    options: ReportOptions,
    extra_warnings: Optional[List[Warning]] = None,
    *,
    today: Optional[date] = None,
    source_file: str = "",
) -> str:
    """Render the full Markdown report from normalised rows and options.

    ``extra_warnings`` are validation warnings produced upstream. ``today`` is
    injectable for deterministic tests. ``source_file`` is shown verbatim in
    the header.
    """
    from .calculations import build_wine_items

    items = build_wine_items(rows, options.basis)
    dry_rows = [r for r in rows if r.is_dry_goods]
    totals = compute_totals(items, dry_rows=len(dry_rows), basis=options.basis)
    warnings = list(extra_warnings or [])

    lines: List[str] = []
    lines += _render_header(rows, options, today=today, source_file=source_file)
    lines.append("")
    lines += _render_exec_summary(items, totals, options, warnings)

    if options.group_by != GROUP_NONE:
        lines.append("")
        lines += _render_grouping(items, options)

    lines.append("")
    lines += _render_detailed(items, options)

    if options.low_stock_warnings:
        lines.append("")
        lines += _render_low_stock(items, options)

    if options.include_dry_goods:
        lines.append("")
        lines += _render_dry_goods(dry_rows)

    lines.append("")
    lines += _render_data_warnings(warnings)

    return "\n".join(lines) + "\n"


def _warehouses(rows: List[StockRow]) -> List[str]:
    seen: List[str] = []
    for row in rows:
        wh = row.warehouse
        if wh and wh not in seen:
            seen.append(wh)
    return seen


def _render_header(
    rows: List[StockRow],
    options: ReportOptions,
    *,
    today: Optional[date],
    source_file: str,
) -> List[str]:
    generated = (today or date.today()).isoformat()
    warehouses = _warehouses(rows)
    warehouse_label = ", ".join(warehouses) if warehouses else "Unknown"
    return [
        TITLE,
        "",
        f"Generated: {generated}",
        f"Source file: {source_file}",
        f"Warehouse: {warehouse_label}",
        f"Stock basis: {options.basis}",
    ]


def _render_exec_summary(
    items: List[WineItem],
    totals: Totals,
    options: ReportOptions,
    warnings: List[Warning],
) -> List[str]:
    if totals.lowest_stock_item is not None:
        low = totals.lowest_stock_item
        lowest_label = (
            f"{low.item} ({low.description}) at "
            f"{fmt_decimal(low.nine_litre_equivalent)} 9LE"
        )
    else:
        lowest_label = NO_VALUE

    basis_cases = (
        totals.total_on_hand_cases
        if options.basis == "OnHand"
        else totals.total_available_cases
    )

    return [
        H_EXEC_SUMMARY,
        "",
        f"- Finished Goods rows: {totals.finished_rows}",
        f"- Dry Goods rows: {totals.dry_rows}",
        f"- Total wine stock: {fmt_decimal(totals.total_nine_le)} 9LE",
        f"- Total {options.basis.lower()} cases: {fmt_decimal(basis_cases)}",
        f"- Total OnHand cases: {fmt_decimal(totals.total_on_hand_cases)}",
        f"- Total Available cases: {fmt_decimal(totals.total_available_cases)}",
        f"- Total allocated cases: {fmt_decimal(totals.total_allocated_cases)}",
        f"- Total pending cases: {fmt_decimal(totals.total_pending_cases)}",
        f"- Lowest stock item: {lowest_label}",
        f"- Data warnings: {len(warnings)}",
    ]


def _render_grouping(items: List[WineItem], options: ReportOptions) -> List[str]:
    heading = group_heading(options.group_by)
    column = _GROUP_COLUMN[options.group_by]
    groups: List[GroupAggregate] = aggregate(items, options.group_by, options.basis)
    out = [heading, ""]
    if not groups:
        out.append(NO_GROUP_DATA_LINE)
        return out
    table_rows = [
        [
            g.key,
            str(g.rows),
            fmt_decimal(g.cases),
            fmt_decimal(g.nine_le),
        ]
        for g in groups
    ]
    out += _table(
        [column, "Rows", "Cases", "9LE"],
        ["l", "r", "r", "r"],
        table_rows,
    )
    return out


def _render_detailed(items: List[WineItem], options: ReportOptions) -> List[str]:
    out = [H_DETAILED, ""]
    if not items:
        out.append(NO_FINISHED_GOODS_LINE)
        return out
    table_rows = []
    for item in items:
        row = item.row
        table_rows.append(
            [
                row.item,
                row.description,
                row.lot or NO_VALUE,
                fmt_decimal(row.on_hand),
                fmt_decimal(row.available),
                row.units or NO_VALUE,
                fmt_decimal(item.nine_litre_equivalent),
            ]
        )
    out += _table(
        ["Item", "Description", "Lot", "OnHand", "Available", "Units", "9LE"],
        ["l", "l", "l", "r", "r", "l", "r"],
        table_rows,
    )
    return out


def _render_low_stock(items: List[WineItem], options: ReportOptions) -> List[str]:
    out = [H_LOW_STOCK, ""]
    low = low_stock_items(items, options.low_stock_threshold, options.basis)
    if not low:
        out.append(NO_LOW_STOCK_LINE)
        return out
    for item in low:
        out.append(
            f"- Item {item.item} ({item.description}) has only "
            f"{fmt_decimal(item.nine_litre_equivalent)} 9LE on the "
            f"{options.basis} basis."
        )
    return out


def _render_dry_goods(dry_rows: List[StockRow]) -> List[str]:
    out = [H_DRY_GOODS, ""]
    if not dry_rows:
        out.append(NO_DRY_GOODS_LINE)
        return out
    table_rows = [
        [
            row.item,
            row.description,
            fmt_decimal(row.available),
            row.units or NO_VALUE,
        ]
        for row in dry_rows
    ]
    out += _table(
        ["Item", "Description", "Available", "Units"],
        ["l", "l", "r", "l"],
        table_rows,
    )
    return out


def _render_data_warnings(warnings: List[Warning]) -> List[str]:
    out = [H_DATA_WARNINGS, ""]
    if not warnings:
        out.append(NO_DATA_WARNINGS_LINE)
        return out
    for warning in warnings:
        out.append(f"- {warning.message}")
    return out
