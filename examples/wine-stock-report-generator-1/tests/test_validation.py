"""Validation tests (PRD section 23)."""

from __future__ import annotations

import unittest
from decimal import Decimal

from wine_stock_reporter.models import TYPE_DRY_GOODS
from wine_stock_reporter.validation import (
    AVAILABLE_GT_ON_HAND_MSG,
    DRY_GOODS_UNEXPECTED_UNITS_MSG,
    FINISHED_NOT_CASES_MSG,
    NEGATIVE_VALUE_MSG,
    UNKNOWN_UNITS_MSG,
    UNKNOWN_VARIETY_MSG,
    UNPARSEABLE_BOTTLE_MSG,
    UNPARSEABLE_PACK_MSG,
    validate_rows,
)
from tests.helpers import make_row


def _messages(rows):
    return [w.message for w in validate_rows(rows)]


class ValidationTests(unittest.TestCase):
    def test_available_greater_than_on_hand(self):
        row = make_row(item="A", on_hand=Decimal("5"), available=Decimal("9"))
        self.assertIn(
            AVAILABLE_GT_ON_HAND_MSG.format(
                available=Decimal("9"), on_hand=Decimal("5"), item="A"
            ),
            _messages([row]),
        )

    def test_negative_stock_warns(self):
        row = make_row(
            item="A",
            on_hand=Decimal("-3"),
            available=Decimal("-3"),
            raw={
                "Type1": "Finished Goods",
                "Item": "A",
                "Description": "FV 22 CHR EP NZ 750ml/12p",
                "ClientStockCode": "",
                "ClientStockDescription": "",
                "Lot": "W1",
                "OnHand": "-3",
                "Warehouse": "Marlborough",
                "Allocated": "0",
                "Pending": "0",
                "Available": "-3",
                "Units": "Cases",
            },
        )
        msgs = _messages([row])
        self.assertIn(
            NEGATIVE_VALUE_MSG.format(field="OnHand", value=Decimal("-3"), item="A"),
            msgs,
        )

    def test_unparseable_pack_and_bottle(self):
        row = make_row(item="A", description="FV 22 CHR EP NZ no-size-here")
        msgs = _messages([row])
        self.assertIn(UNPARSEABLE_PACK_MSG.format(item="A"), msgs)
        self.assertIn(UNPARSEABLE_BOTTLE_MSG.format(item="A"), msgs)

    def test_unknown_units_warns(self):
        row = make_row(item="A", units="Pallets")
        self.assertIn(
            UNKNOWN_UNITS_MSG.format(units="Pallets", item="A"), _messages([row])
        )

    def test_unknown_variety_code_warns(self):
        row = make_row(item="A", description="FV 22 ZZZ EP NZ 750ml/12p")
        self.assertIn(
            UNKNOWN_VARIETY_MSG.format(code="ZZZ", item="A"), _messages([row])
        )

    def test_finished_goods_not_in_cases(self):
        row = make_row(item="A", units="Eaches")
        self.assertIn(
            FINISHED_NOT_CASES_MSG.format(item="A", units="Eaches"), _messages([row])
        )

    def test_dry_goods_unexpected_units(self):
        row = make_row(
            item="A",
            type1=TYPE_DRY_GOODS,
            description="FV LA 25 SAB GL UK Front",
            units="Cases",
        )
        self.assertIn(
            DRY_GOODS_UNEXPECTED_UNITS_MSG.format(item="A", units="Cases"),
            _messages([row]),
        )

    def test_clean_row_has_no_warnings(self):
        row = make_row(item="A")
        self.assertEqual(validate_rows([row]), [])


if __name__ == "__main__":
    unittest.main()
