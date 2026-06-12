# Wine Stock Report Generator

Converts a real warehouse stock-on-hand CSV into a readable Markdown stock
report, including finished wine stock, 9-litre-equivalent (`9LE`) totals,
grouping summaries, low-stock warnings, dry goods, and data validation notes.

The tool is pure Python 3.11+ standard library — no install step, no
dependencies. Run it straight from the repository root.

## What it does

1. Loads a warehouse stock CSV and validates that the required columns exist.
2. Cleans messy numeric fields (thousands separators like `"2,216.50"`, blanks,
   whitespace, zeros, negatives).
3. Separates **Finished Goods** (wine) from **Dry Goods** (labels, packaging).
4. Parses each Finished Goods `Description` for vintage, variety, market,
   bottle size and pack size — tolerantly, never crashing on an odd row.
5. Computes 9LE per case (`litres = cases × pack × bottle_size; 9LE = litres / 9`)
   using `decimal.Decimal` so the totals are exact.
6. Asks six clarification questions (interactive mode) or uses defaults
   (`--no-interactive`).
7. Writes a Markdown report and lists data-quality warnings.

## Running

### Interactive (default)

```bash
python3 -m wine_stock_reporter examples/stock_sample.csv
```

After loading the file the program prints a short `Detected:` summary and asks
six questions, each showing its default in brackets. Press **Enter** to accept a
default; type a value to override it. Reaching end-of-input (e.g. piping from an
empty stream) accepts the default for that question and every remaining one.

### Non-interactive (CI / automation)

```bash
python3 -m wine_stock_reporter examples/stock_sample.csv \
  --basis Available \
  --group-by variety \
  --include-dry-goods \
  --low-stock-threshold 10 \
  --output stock-report.md \
  --no-interactive
```

## Command-line options

| Flag | Values | Default | Meaning |
|---|---|---|---|
| `CSV_PATH` | path | — (required) | Stock CSV to read. |
| `--basis` | `OnHand`, `Available` | `Available` | Stock basis used for wine 9LE totals. |
| `--group-by` | `variety`, `vintage`, `market`, `pack_size`, `lot`, `none` | `variety` | Grouping for the primary wine summary (`none` omits the grouping section). |
| `--include-dry-goods` / `--no-dry-goods` | flag | include | Include or omit the Dry Goods section. |
| `--low-stock-warnings` / `--no-low-stock-warnings` | flag | on | Show or hide low-stock warnings. |
| `--low-stock-threshold N` | number (9LE) | `10` | An item is low-stock when its 9LE on the chosen basis is below `N`. |
| `--output PATH` | path | `stock-report.md` | Where to write the Markdown report. |
| `--no-interactive` | flag | off | Skip all prompts and use the effective option values. |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — report written. |
| `1` | Data/file error (missing file, missing required column, unreadable CSV). A one-line `Error: ...` is printed to stderr with no traceback. |
| `2` | Usage error (unknown flag, bad choice). `--help` exits `0`. |

## Report structure

The generated Markdown contains, in order:

- a header (generated date, source file, warehouse(s), stock basis),
- `## Executive Summary` (row counts, total 9LE, case totals, lowest-stock
  item, data-warning count),
- the selected grouping table, e.g. `## Stock by Variety` (omitted when
  `--group-by none`),
- `## Detailed Finished Goods`,
- `## Low Stock Warnings` (when enabled),
- `## Dry Goods Summary` (when included),
- `## Data Warnings`.

Dry Goods never contribute to wine 9LE totals and never receive a 9LE value;
they appear in their own section in their original units (usually `Eaches`).
A Finished Goods row whose bottle/pack size cannot be parsed still appears in
the detail table with its 9LE shown as `—`, is excluded from 9LE totals, but
still counts toward case totals — and earns a data warning.

## Running the tests

```bash
python3 -m unittest discover -s tests
```

## Variety codes

`CHR` Chardonnay · `SAB` Sauvignon Blanc · `PIN` Pinot Noir · `PIG` Pinot Gris
· `PRO` Rosé · `RDB` Red Blend · `MXD` Mixed / Consolidated. Unknown codes stay
visible in the report and are listed under Data Warnings.
