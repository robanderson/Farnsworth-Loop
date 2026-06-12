"""Report rendering tests (PRD section 23 + section 24 acceptance examples)."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from wine_stock_reporter.models import (
    GROUP_NONE,
    GROUP_VINTAGE,
    TYPE_DRY_GOODS,
    ReportOptions,
    Warning,
)
from wine_stock_reporter.report import (
    H_DATA_WARNINGS,
    H_DETAILED,
    H_DRY_GOODS,
    H_EXEC_SUMMARY,
    H_LOW_STOCK,
    NO_VALUE,
    TITLE,
    fmt_decimal,
    group_heading,
    render_report,
)
from tests.helpers import make_row


def _render(rows, options, warnings=None):
    return render_report(
        rows,
        options,
        extra_warnings=warnings,
        today=date(2026, 6, 12),
        source_file="stock_sample.csv",
    )


class FmtDecimalTests(unittest.TestCase):
    def test_two_places(self):
        self.assertEqual(fmt_decimal(Decimal("48.58")), "48.58")

    def test_rounds_half_up(self):
        # 13.335 -> 13.34 (PRD section 24 rounded report value).
        self.assertEqual(fmt_decimal(Decimal("13.335")), "13.34")

    def test_thousands_separator(self):
        self.assertEqual(fmt_decimal(Decimal("2216.50")), "2,216.50")

    def test_none_is_placeholder(self):
        self.assertEqual(fmt_decimal(None), NO_VALUE)


class ReportStructureTests(unittest.TestCase):
    def _rows(self):
        return [
            make_row(item="1", description="FV 22 CHR EP NZ 750ml/12p",
                     available=Decimal("48.58"), on_hand=Decimal("48.58")),
            make_row(item="2", description="FV 22 CHR EP NZ 750ml/6p",
                     available=Decimal("26.67"), on_hand=Decimal("26.67")),
            make_row(item="3", type1=TYPE_DRY_GOODS, units="Eaches",
                     description="FV LA 25 SAB GL UK Front 12.5% ML",
                     available=Decimal("4270.00"), on_hand=Decimal("4270.00")),
        ]

    def test_generates_markdown_with_title(self):
        text = _render(self._rows(), ReportOptions())
        self.assertTrue(text.startswith(TITLE))
        self.assertIn("Source file: stock_sample.csv", text)
        self.assertIn("Generated: 2026-06-12", text)

    def test_includes_executive_summary(self):
        text = _render(self._rows(), ReportOptions())
        self.assertIn(H_EXEC_SUMMARY, text)
        self.assertIn("- Finished Goods rows: 2", text)
        self.assertIn("- Dry Goods rows: 1", text)

    def test_includes_selected_grouping_table(self):
        text = _render(self._rows(), ReportOptions(group_by=GROUP_VINTAGE))
        self.assertIn(group_heading(GROUP_VINTAGE), text)
        self.assertIn("| Vintage | Rows | Cases | 9LE |", text)

    def test_group_none_omits_grouping_section(self):
        text = _render(self._rows(), ReportOptions(group_by=GROUP_NONE))
        self.assertNotIn("## Stock by", text)

    def test_includes_detailed_finished_goods(self):
        text = _render(self._rows(), ReportOptions())
        self.assertIn(H_DETAILED, text)
        # 13.335 9LE row renders rounded to 13.34.
        self.assertIn("13.34", text)

    def test_750_12p_9le_equals_cases(self):
        text = _render(
            [make_row(item="1", description="FV 22 CHR EP NZ 750ml/12p",
                      available=Decimal("48.58"))],
            ReportOptions(group_by=GROUP_NONE, include_dry_goods=False,
                          low_stock_warnings=False),
        )
        # Detailed row: ...| 48.58 | Cases | 48.58 |
        self.assertIn("| 48.58 | Cases | 48.58 |", text)

    def test_low_stock_included_when_enabled(self):
        rows = [make_row(item="low", description="FV 22 CHR EP NZ 750ml/12p",
                         available=Decimal("3"))]
        text = _render(rows, ReportOptions(low_stock_warnings=True,
                                           low_stock_threshold=Decimal("10")))
        self.assertIn(H_LOW_STOCK, text)
        self.assertIn("Item low", text)

    def test_low_stock_excluded_when_disabled(self):
        rows = [make_row(item="low", available=Decimal("3"))]
        text = _render(rows, ReportOptions(low_stock_warnings=False))
        self.assertNotIn(H_LOW_STOCK, text)

    def test_dry_goods_included_only_when_requested(self):
        rows = self._rows()
        with_dry = _render(rows, ReportOptions(include_dry_goods=True))
        without_dry = _render(rows, ReportOptions(include_dry_goods=False))
        self.assertIn(H_DRY_GOODS, with_dry)
        self.assertNotIn(H_DRY_GOODS, without_dry)

    def test_dry_goods_row_excluded_from_wine_totals_and_no_9le(self):
        rows = self._rows()
        text = _render(rows, ReportOptions(include_dry_goods=True))
        # Wine totals: 48.58 + 13.335 = 61.92 (rounded). Dry 4270 not included.
        self.assertIn("- Total wine stock: 61.92 9LE", text)
        # The dry-goods row is in its own section with no 9LE column.
        dry_section = text.split(H_DRY_GOODS, 1)[1]
        self.assertIn("4,270.00", dry_section)
        self.assertNotIn("9LE", dry_section.split(H_DATA_WARNINGS)[0])

    def test_includes_data_warnings(self):
        rows = self._rows()
        warning = Warning(message="Test warning for item 1", item="1")
        text = _render(rows, ReportOptions(), warnings=[warning])
        self.assertIn(H_DATA_WARNINGS, text)
        self.assertIn("- Test warning for item 1", text)
        self.assertIn("- Data warnings: 1", text)

    def test_basis_changes_summary_label(self):
        rows = self._rows()
        available = _render(rows, ReportOptions(basis="Available"))
        on_hand = _render(rows, ReportOptions(basis="OnHand"))
        self.assertIn("Stock basis: Available", available)
        self.assertIn("Stock basis: OnHand", on_hand)


if __name__ == "__main__":
    unittest.main()
