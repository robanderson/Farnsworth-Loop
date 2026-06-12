# Goal Attestation — Wine Stock Report Generator

Reviewer attestation against GOAL.md "Done — semantic half" and PRD section 26.
All criteria verified EMPIRICALLY against the merged state (repo of record at
`/home/user/wsr-run/wine-stock-report-generator-1`). No project source was
modified during review.

## Mechanical baseline (re-confirmed)

- `python3 -m unittest discover -s tests` → 73 tests, OK.
- `python3 -m compileall -q wine_stock_reporter` → rc 0.
- `--help` → rc 0; unknown flag → rc 2; missing CSV → rc 1 with one-line
  `Error: input file '...' was not found.` and no traceback; empty-stdin
  interactive run → rc 0.

## PRD Section 24 acceptance examples (empirical)

Probed via the live parser/calculator (`parse_description`, `nine_litre_equivalent`):

- `FV 22 CHR EP NZ 750ml/12p` → vintage `2022`, variety `Chardonnay`
  (code `CHR`), market `NZ`, bottle `750`, pack `12`. 9LE for 48.58 cases =
  `48.5800`, which equals its cases (`== Decimal('48.58')` → True). No warnings.
- `FV 22 CHR EP NZ 750ml/6p` → 9LE for 26.67 cases = `13.3350` (exactly half
  the cases), rendered rounded as `13.34`. Confirms the 6-pack 9LE-half rule.
- `FV 22 RDB EP UK 750ml/6p Legacy Red` → variety `Red Blend`, market `UK`,
  pack `6`, extra description `Legacy Red`.
- Dry Goods row `558243` (`FV LA 25 SAB GL UK Front 12.5% ML FG087442`,
  `4,270.00` Eaches): in the full fixture report it appears exactly once — only
  in the Dry Goods Summary table (line 137: `| 558243 | ... | 4,270.00 |
  Eaches |`), is excluded from the variety grouping and Detailed Finished Goods
  tables, and receives no 9LE.

## PRD Section 19 report structure (empirical)

Full-fixture report headings, in order: `# Wine Stock Report`,
`## Executive Summary`, `## Stock by Variety` (selected grouping),
`## Detailed Finished Goods`, `## Low Stock Warnings`, `## Dry Goods Summary`,
`## Data Warnings`. Executive summary includes finished/dry row counts, total
wine 9LE, basis cases, allocated/pending, lowest-stock item, and data-warning
count.

## PRD Section 20 validation rules (constructed bad data, not the fixture)

Ran the tool on a hand-built `/tmp/bad.csv`. Data Warnings rendered:
negative OnHand and Available (item 900001); unknown variety code `ABC`;
`Available (20.00) exceeds OnHand (10.00)` (item 900002); balance mismatch;
unparseable bottle/pack size (gibberish description 900003); unknown variety
`GIBBERISH`; Finished Goods measured in Eaches not Cases (900004); Dry Goods
measured in Cases not Eaches (900005); unknown Type1 `Mystery Goods`; unknown
units `Widgets` (900006). All required section-20 categories produced visible
warnings. The fixture itself also surfaced two genuine balance-mismatch
warnings (items 766286, 770088).

## Switches visibly change the report (empirical)

- Basis: `--basis OnHand` vs `--basis Available` → total wine stock
  `9,448.83` vs `9,445.83` 9LE; lowest-stock item changes (776561 vs 760706);
  basis-cases line label/value change.
- Grouping: `--group-by vintage` → `## Stock by Vintage`; `--group-by market`
  → `## Stock by Market`; `--group-by none` → grouping section omitted.
- Dry-goods: `--no-dry-goods` removes the `## Dry Goods Summary` section
  (count 0); default includes it (count 1).
- Threshold: `--low-stock-threshold 10` → 7 low-stock bullets;
  `--low-stock-threshold 50` → 16. `--no-low-stock-warnings` omits the section.
- Interactive mode: answering `OnHand` then `vintage` produced a report with
  `Stock basis: OnHand` and `## Stock by Vintage`, confirming prompts are
  applied (not just non-interactive flags).

## Decimal + thousands separators (empirical)

- 9LE objects are `Decimal` (verified `type(nle).__name__ == 'Decimal'`); the
  whole 9LE path (`csv_loader.clean_numeric`, `calculations.nine_litre_equivalent`,
  totals/aggregates) uses `Decimal`; floats appear only at the report
  formatting edge.
- `clean_numeric` parses `4,270.00 → 4270.00`, `2,216.50 → 2216.50`,
  `53,100.00 → 53100.00`, trims whitespace, and returns `None` for blanks.
  Thousands-separated totals render correctly in the report (`9,445.83`).

## Anti-hardcoding (empirical, PRD section 26)

- Truncated copy (header + 5 finished rows): report shows 5 Finished Goods
  rows, 0 Dry Goods, total `392.00` 9LE — independently recomputed by hand to
  `392.000`. Completely different from the full fixture.
- Modified copy (one 156.00-case 750ml/12p row doubled to 312.00): total wine
  stock rose from `9,445.83` to `9,601.83` 9LE — exactly +156, the expected
  delta. Totals track the data, nothing is pinned to the fixture.

## README (empirical)

`README.md` documents both Interactive (default) and Non-interactive
(`--no-interactive`) modes with `python3 -m wine_stock_reporter ...` commands
and a flag reference table.

## Residual gaps

None blocking. Minor observations (non-blocking): the brief's illustrative
26.67→13.34 phrasing matches; the report adds extra OnHand/Available total
lines beyond the PRD's suggested skeleton, which is additive and consistent
with section 15's "still include ... columns where useful."

## Conclusion

Every GOAL.md semantic criterion and PRD section 26 item is satisfied under
empirical probing. Goal met.
