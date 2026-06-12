"""CSV loading tests (PRD section 23)."""

from __future__ import annotations

import os
import tempfile
import unittest
from decimal import Decimal

from wine_stock_reporter.csv_loader import (
    MISSING_COLUMN_MSG,
    MISSING_FILE_MSG,
    DataError,
    clean_numeric,
    load_csv,
)

HEADER = (
    "Type1,Item,Description,ClientStockCode,ClientStockDescription,Lot,"
    "OnHand,Warehouse,Allocated,Pending,Available,Units"
)


def _write_csv(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class CleanNumericTests(unittest.TestCase):
    def test_parses_decimal(self):
        self.assertEqual(clean_numeric("13.67"), Decimal("13.67"))

    def test_parses_thousands_separator(self):
        self.assertEqual(clean_numeric("2,216.50"), Decimal("2216.50"))

    def test_strips_whitespace(self):
        self.assertEqual(clean_numeric("  156.00 "), Decimal("156.00"))

    def test_blank_is_none(self):
        self.assertIsNone(clean_numeric(""))
        self.assertIsNone(clean_numeric("   "))
        self.assertIsNone(clean_numeric(None))

    def test_zero(self):
        self.assertEqual(clean_numeric("0.00"), Decimal("0.00"))

    def test_negative(self):
        self.assertEqual(clean_numeric("-5.00"), Decimal("-5.00"))

    def test_non_numeric_is_none(self):
        self.assertIsNone(clean_numeric("abc"))


class LoadCsvTests(unittest.TestCase):
    def setUp(self):
        self._paths = []

    def tearDown(self):
        for path in self._paths:
            try:
                os.remove(path)
            except OSError:
                pass

    def _csv(self, text: str) -> str:
        path = _write_csv(text)
        self._paths.append(path)
        return path

    def test_loads_valid_csv(self):
        path = self._csv(
            HEADER
            + "\nFinished Goods,1,FV 22 CHR EP NZ 750ml/12p,,,W1,"
            "10.00,Marlborough,0.00,0.00,10.00,Cases\n"
        )
        rows = load_csv(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].item, "1")
        self.assertEqual(rows[0].available, Decimal("10.00"))
        self.assertEqual(rows[0].warehouse, "Marlborough")

    def test_missing_file_raises_with_message(self):
        missing = os.path.join(tempfile.gettempdir(), "definitely-not-here-xyz.csv")
        with self.assertRaises(DataError) as ctx:
            load_csv(missing)
        self.assertEqual(str(ctx.exception), MISSING_FILE_MSG.format(path=missing))

    def test_missing_required_column_names_it(self):
        # Drop the Available column.
        header = HEADER.replace(",Available", "")
        path = self._csv(
            header
            + "\nFinished Goods,1,FV 22 CHR EP NZ 750ml/12p,,,W1,"
            "10.00,Marlborough,0.00,0.00,Cases\n"
        )
        with self.assertRaises(DataError) as ctx:
            load_csv(path)
        self.assertEqual(
            str(ctx.exception), MISSING_COLUMN_MSG.format(column="Available")
        )

    def test_parses_decimal_strings(self):
        path = self._csv(
            HEADER
            + "\nFinished Goods,1,FV 22 CHR EP NZ 750ml/12p,,,W1,"
            "13.67,Marlborough,0.00,0.00,13.67,Cases\n"
        )
        rows = load_csv(path)
        self.assertEqual(rows[0].on_hand, Decimal("13.67"))

    def test_parses_thousands_separators(self):
        path = self._csv(
            HEADER
            + '\nFinished Goods,1,FV 22 CHR EP NZ 750ml/12p,,,W1,'
            '"2,216.50",Marlborough,0.00,0.00,"2,216.50",Cases\n'
        )
        rows = load_csv(path)
        self.assertEqual(rows[0].available, Decimal("2216.50"))

    def test_blank_nullable_numeric(self):
        path = self._csv(
            HEADER
            + "\nFinished Goods,1,FV 22 CHR EP NZ 750ml/12p,,,W1,"
            "10.00,Marlborough,,,10.00,Cases\n"
        )
        rows = load_csv(path)
        self.assertIsNone(rows[0].allocated)
        self.assertIsNone(rows[0].pending)


if __name__ == "__main__":
    unittest.main()
