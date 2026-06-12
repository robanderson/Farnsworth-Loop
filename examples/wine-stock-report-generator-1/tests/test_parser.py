"""Parser tests (PRD section 23 + section 24 acceptance examples)."""

from __future__ import annotations

import unittest

from wine_stock_reporter.models import UNKNOWN
from wine_stock_reporter.parser import (
    UNKNOWN_VARIETY_MSG,
    expand_vintage,
    map_variety,
    parse_description,
)


class ExpandVintageTests(unittest.TestCase):
    def test_two_digit_years(self):
        self.assertEqual(expand_vintage("20"), "2020")
        self.assertEqual(expand_vintage("22"), "2022")
        self.assertEqual(expand_vintage("25"), "2025")

    def test_nv_passthrough(self):
        self.assertEqual(expand_vintage("NV"), "NV")
        self.assertEqual(expand_vintage("nv"), "NV")


class MapVarietyTests(unittest.TestCase):
    def test_known_codes(self):
        self.assertEqual(map_variety("CHR"), "Chardonnay")
        self.assertEqual(map_variety("SAB"), "Sauvignon Blanc")
        self.assertEqual(map_variety("PIN"), "Pinot Noir")
        self.assertEqual(map_variety("RDB"), "Red Blend")

    def test_unknown_code(self):
        self.assertEqual(map_variety("ABC"), UNKNOWN)


class ParseDescriptionTests(unittest.TestCase):
    def test_standard_750_12p(self):
        parsed, warnings = parse_description("FV 22 CHR EP NZ 750ml/12p", "747691")
        self.assertEqual(parsed.prefix, "FV")
        self.assertEqual(parsed.vintage, "2022")
        self.assertEqual(parsed.variety_code, "CHR")
        self.assertEqual(parsed.variety, "Chardonnay")
        self.assertEqual(parsed.market, "NZ")
        self.assertEqual(parsed.bottle_size_ml, 750)
        self.assertEqual(parsed.pack_size, 12)
        self.assertEqual(warnings, [])

    def test_standard_750_6p_an_market(self):
        parsed, warnings = parse_description("FV 22 CHR EP AN 750ml/6p", "766163")
        self.assertEqual(parsed.vintage, "2022")
        self.assertEqual(parsed.variety, "Chardonnay")
        self.assertEqual(parsed.market, "AN")
        self.assertEqual(parsed.bottle_size_ml, 750)
        self.assertEqual(parsed.pack_size, 6)
        self.assertEqual(warnings, [])

    def test_extra_description_preserved(self):
        parsed, warnings = parse_description(
            "FV 22 RDB EP UK 750ml/6p Legacy Red", "770024"
        )
        self.assertEqual(parsed.variety_code, "RDB")
        self.assertEqual(parsed.variety, "Red Blend")
        self.assertEqual(parsed.market, "UK")
        self.assertEqual(parsed.pack_size, 6)
        self.assertEqual(parsed.extra_description, "Legacy Red")
        self.assertEqual(warnings, [])

    def test_unknown_variety_warns_and_stays_visible(self):
        parsed, warnings = parse_description("FV 22 ZZZ EP NZ 750ml/12p", "999999")
        self.assertEqual(parsed.variety_code, "ZZZ")
        self.assertEqual(parsed.variety, UNKNOWN)
        messages = [w.message for w in warnings]
        self.assertIn(
            UNKNOWN_VARIETY_MSG.format(code="ZZZ", item="999999"), messages
        )

    def test_non_matching_description_does_not_crash(self):
        parsed, warnings = parse_description("totally unstructured label text", "555")
        # Returns a usable object; no exception.
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.variety, UNKNOWN)
        self.assertIsNone(parsed.bottle_size_ml)
        self.assertTrue(warnings)

    def test_empty_description(self):
        parsed, warnings = parse_description("", "555")
        self.assertEqual(parsed.variety, UNKNOWN)
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
