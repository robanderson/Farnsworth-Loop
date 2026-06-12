"""Tolerant parser for Finished Goods descriptions.

A typical description looks like::

    FV 22 CHR EP NZ 750ml/12p
    FV 22 RDB EP UK 750ml/6p Legacy Red

Layout (token positions): ``<prefix> <vintage> <variety> <brand> <market>
<bottle>ml/<pack>p [extra...]``. The parser is deliberately forgiving: any
piece it cannot read is left absent (``None``) or marked ``Unknown`` and a
warning is emitted by :mod:`wine_stock_reporter.validation`; it never raises
because of one odd description.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .models import UNKNOWN, ParsedWine, Warning

# Variety code -> human-readable variety name (PRD section 11).
VARIETY_MAP = {
    "CHR": "Chardonnay",
    "SAB": "Sauvignon Blanc",
    "PIN": "Pinot Noir",
    "PIG": "Pinot Gris",
    "PRO": "Rosé",
    "RDB": "Red Blend",
    "MXD": "Mixed / Consolidated",
}

# Marker for a non-vintage product.
NON_VINTAGE = "NV"

# Warning message templates (single-sourced; imported by tests).
UNKNOWN_VARIETY_MSG = "Unknown variety code '{code}' in item {item}."
UNPARSEABLE_PACK_MSG = "Could not parse pack size for item {item}."
UNPARSEABLE_BOTTLE_MSG = "Could not parse bottle size for item {item}."
UNPARSEABLE_DESCRIPTION_MSG = (
    "Could not parse description '{description}' for item {item}; "
    "marked Unknown."
)
EMPTY_DESCRIPTION_MSG = "Empty description for item {item}."

# bottle/pack token, e.g. "750ml/12p" (case-insensitive, tolerant spacing).
_SIZE_RE = re.compile(r"(?P<bottle>\d+)\s*ml\s*/\s*(?P<pack>\d+)\s*p", re.IGNORECASE)
# Two-digit vintage.
_VINTAGE_RE = re.compile(r"^\d{2}$")
# A short alphabetic-ish token (used to recognise market / variety / brand).
_CODE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+]*$")


def expand_vintage(token: str) -> str:
    """Expand a two-digit vintage to four digits (``"22" -> "2022"``).

    ``NV`` (any case) passes through as ``"NV"``. A token that is neither a
    two-digit year nor ``NV`` is returned unchanged so the caller can decide.
    """
    upper = token.upper()
    if upper == NON_VINTAGE:
        return NON_VINTAGE
    if _VINTAGE_RE.match(token):
        return "20" + token
    return token


def map_variety(code: str) -> str:
    """Map a variety code to its name, or :data:`UNKNOWN` if not recognised."""
    return VARIETY_MAP.get(code.upper(), UNKNOWN)


def parse_description(description: str, item: str = "") -> Tuple[ParsedWine, List[Warning]]:
    """Parse a Finished Goods description into a :class:`ParsedWine`.

    Returns the parsed object plus a list of non-fatal :class:`Warning`
    objects. Always returns a usable object — never raises.
    """
    warnings: List[Warning] = []
    parsed = ParsedWine()

    text = (description or "").strip()
    if text == "":
        warnings.append(Warning(EMPTY_DESCRIPTION_MSG.format(item=item), item=item))
        return parsed, warnings

    # Extract the size token (bottle/pack) and split it out of the stream.
    size_match = _SIZE_RE.search(text)
    if size_match:
        parsed.bottle_size_ml = int(size_match.group("bottle"))
        parsed.pack_size = int(size_match.group("pack"))
        before = text[: size_match.start()].strip()
        after = text[size_match.end():].strip()
    else:
        before = text
        after = ""
        warnings.append(Warning(UNPARSEABLE_BOTTLE_MSG.format(item=item), item=item))
        warnings.append(Warning(UNPARSEABLE_PACK_MSG.format(item=item), item=item))

    tokens = before.split()

    # Prefix (e.g. "FV"), if a leading alpha token exists.
    idx = 0
    if idx < len(tokens) and _CODE_RE.match(tokens[idx]):
        parsed.prefix = tokens[idx]
        idx += 1

    # Vintage: two-digit year or NV.
    if idx < len(tokens):
        tok = tokens[idx]
        if _VINTAGE_RE.match(tok) or tok.upper() == NON_VINTAGE:
            parsed.vintage = expand_vintage(tok)
            idx += 1

    # Variety code.
    if idx < len(tokens) and _CODE_RE.match(tokens[idx]):
        parsed.variety_code = tokens[idx].upper()
        parsed.variety = map_variety(parsed.variety_code)
        idx += 1
        if parsed.variety == UNKNOWN:
            warnings.append(
                Warning(
                    UNKNOWN_VARIETY_MSG.format(code=parsed.variety_code, item=item),
                    item=item,
                )
            )

    # Brand/code (e.g. "EP", "GL", "SSK").
    if idx < len(tokens) and _CODE_RE.match(tokens[idx]):
        parsed.brand_code = tokens[idx]
        idx += 1

    # Market code (e.g. "NZ", "UK", "CA", "X+").
    if idx < len(tokens):
        parsed.market = tokens[idx]
        idx += 1

    # Anything left before the size token, plus anything after it, is extra.
    leftover_before = " ".join(tokens[idx:]).strip()
    extra_parts = [p for p in (leftover_before, after) if p]
    if extra_parts:
        parsed.extra_description = " ".join(extra_parts)

    # If we recognised essentially nothing meaningful, flag the description.
    if (
        parsed.variety_code is None
        and parsed.vintage is None
        and parsed.bottle_size_ml is None
    ):
        warnings.append(
            Warning(
                UNPARSEABLE_DESCRIPTION_MSG.format(description=text, item=item),
                item=item,
            )
        )

    return parsed, warnings
