"""Calculation tests (PRD section 23 + section 24 acceptance examples)."""

from __future__ import annotations

import unittest
from decimal import Decimal

from wine_stock_reporter.calculations import (
    aggregate,
    build_wine_items,
    compute_totals,
    low_stock_items,
    nine_litre_equivalent,
)
from wine_stock_reporter.models import (
    BASIS_AVAILABLE,
    BASIS_ON_HAND,
    GROUP_MARKET,
    GROUP_VARIETY,
    GROUP_VINTAGE,
    TYPE_DRY_GOODS,
)
from tests.helpers import make_row


class NineLitreEquivalentTests(unittest.TestCase):
    def test_750_12p_is_one_to_one(self):
        # 48.58 cases of 750ml/12p == 48.58 9LE.
        self.assertEqual(
            nine_litre_equivalent(Decimal("48.58"), 750, 12), Decimal("48.58")
        )

    def test_750_6p_is_half(self):
        # 26.67 cases of 750ml/6p == 13.335 9LE.
        self.assertEqual(
            nine_litre_equivalent(Decimal("26.67"), 750, 6), Decimal("13.335")
        )

    def test_none_when_size_missing(self):
        self.assertIsNone(nine_litre_equivalent(Decimal("10"), None, 12))
        self.assertIsNone(nine_litre_equivalent(Decimal("10"), 750, None))
        self.assertIsNone(nine_litre_equivalent(None, 750, 12))


class BuildWineItemsTests(unittest.TestCase):
    def test_uses_available_basis(self):
        row = make_row(on_hand=Decimal("100"), available=Decimal("40"))
        items = build_wine_items([row], BASIS_AVAILABLE)
        self.assertEqual(len(items), 1)
        # 40 cases of 750ml/12p -> 40 9LE.
        self.assertEqual(items[0].nine_litre_equivalent, Decimal("40"))

    def test_uses_on_hand_basis(self):
        row = make_row(on_hand=Decimal("100"), available=Decimal("40"))
        items = build_wine_items([row], BASIS_ON_HAND)
        self.assertEqual(items[0].nine_litre_equivalent, Decimal("100"))

    def test_excludes_dry_goods(self):
        wine = make_row(item="1")
        dry = make_row(
            item="2",
            type1=TYPE_DRY_GOODS,
            description="FV LA 25 SAB GL UK Front 12.5% ML",
            units="Eaches",
            available=Decimal("4270.00"),
        )
        items = build_wine_items([wine, dry], BASIS_AVAILABLE)
        self.assertEqual([i.item for i in items], ["1"])

    def test_dry_goods_get_no_9le(self):
        # A dry-goods row never produces a wine item, so it cannot receive 9LE.
        dry = make_row(type1=TYPE_DRY_GOODS, units="Eaches")
        self.assertEqual(build_wine_items([dry], BASIS_AVAILABLE), [])


class AggregateTests(unittest.TestCase):
    def _items(self):
        rows = [
            make_row(
                item="1",
                description="FV 22 CHR EP NZ 750ml/12p",
                available=Decimal("10"),
            ),
            make_row(
                item="2",
                description="FV 22 CHR EP NZ 750ml/12p",
                available=Decimal("20"),
            ),
            make_row(
                item="3",
                description="FV 23 SAB EP UK 750ml/12p",
                available=Decimal("5"),
            ),
        ]
        return build_wine_items(rows, BASIS_AVAILABLE)

    def test_aggregate_by_variety(self):
        groups = {g.key: g for g in aggregate(self._items(), GROUP_VARIETY, BASIS_AVAILABLE)}
        self.assertEqual(groups["Chardonnay"].rows, 2)
        self.assertEqual(groups["Chardonnay"].cases, Decimal("30"))
        self.assertEqual(groups["Chardonnay"].nine_le, Decimal("30"))
        self.assertEqual(groups["Sauvignon Blanc"].rows, 1)
        self.assertEqual(groups["Sauvignon Blanc"].cases, Decimal("5"))

    def test_aggregate_by_vintage(self):
        groups = {g.key: g for g in aggregate(self._items(), GROUP_VINTAGE, BASIS_AVAILABLE)}
        self.assertEqual(groups["2022"].rows, 2)
        self.assertEqual(groups["2022"].cases, Decimal("30"))
        self.assertEqual(groups["2023"].rows, 1)

    def test_aggregate_by_market(self):
        groups = {g.key: g for g in aggregate(self._items(), GROUP_MARKET, BASIS_AVAILABLE)}
        self.assertEqual(groups["NZ"].rows, 2)
        self.assertEqual(groups["UK"].rows, 1)

    def test_unknown_grouping_raises(self):
        with self.assertRaises(ValueError):
            aggregate(self._items(), "color", BASIS_AVAILABLE)


class TotalsAndLowStockTests(unittest.TestCase):
    def test_totals_sum_9le_and_pick_lowest(self):
        rows = [
            make_row(item="1", available=Decimal("48.58")),  # 48.58 9LE
            make_row(
                item="2",
                description="FV 22 CHR EP NZ 750ml/6p",
                available=Decimal("26.67"),
            ),  # 13.335 9LE
        ]
        items = build_wine_items(rows, BASIS_AVAILABLE)
        totals = compute_totals(items, dry_rows=3, basis=BASIS_AVAILABLE)
        self.assertEqual(totals.finished_rows, 2)
        self.assertEqual(totals.dry_rows, 3)
        self.assertEqual(totals.total_nine_le, Decimal("61.915"))
        self.assertEqual(totals.lowest_stock_item.item, "2")

    def test_low_stock_below_threshold_only(self):
        rows = [
            make_row(item="low", available=Decimal("5")),   # 5 9LE
            make_row(item="high", available=Decimal("50")),  # 50 9LE
        ]
        items = build_wine_items(rows, BASIS_AVAILABLE)
        low = low_stock_items(items, Decimal("10"), BASIS_AVAILABLE)
        self.assertEqual([i.item for i in low], ["low"])


if __name__ == "__main__":
    unittest.main()
