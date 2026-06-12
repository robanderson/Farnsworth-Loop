# Blind Implementation Sketch — Task 001 Wine Stock Report Generator

Written BEFORE opening any candidate diff. This is my anchoring expectation
of what a correct, well-structured solution looks like.

## Package layout (flat, per brief — overrides PRD §21 src/)

```
wine_stock_reporter/__init__.py      # version, maybe re-exports
wine_stock_reporter/__main__.py      # `from .cli import main; raise SystemExit(main())`
wine_stock_reporter/cli.py           # argparse + interactive prompts + orchestration
wine_stock_reporter/csv_loader.py    # read CSV, validate columns, numeric cleaning
wine_stock_reporter/models.py        # dataclasses: RawRow, WineRow, ReportOptions, Warning
wine_stock_reporter/parser.py        # description parser, variety map, vintage expand
wine_stock_reporter/calculations.py  # 9LE, aggregation/grouping, totals, low-stock
wine_stock_reporter/validation.py    # row-level validation warnings
wine_stock_reporter/report.py        # Markdown rendering
tests/__init__.py + tests/test_*.py
README.md
```

## Key contracts I expect each candidate to get right

### CLI (exact, closed)
- `python3 -m wine_stock_reporter CSV_PATH [options]`
- argparse with: `--basis {OnHand,Available}` default Available;
  `--group-by {variety,vintage,market,pack_size,lot,none}` default variety;
  `--include-dry-goods/--no-dry-goods` (BooleanOptionalAction or paired
  store_true/store_false with a single dest default True);
  `--low-stock-warnings/--no-low-stock-warnings` default on;
  `--low-stock-threshold N` (Decimal, default 10);
  `--output PATH` default `stock-report.md`; `--no-interactive`.
- Exit codes: 0 ok; 2 argparse usage (DO NOT catch SystemExit — seed tip 4);
  1 for data/file errors with `Error: ...` one line on stderr, no traceback.
- Watch for the trap: wrapping parse_args in try/except SystemExit (seed #4).

### Interactive mode (default)
- Print "Detected: ..." summary (row types, warehouse(s), units).
- Six questions in PRD §17 order; default = effective CLI option value;
  show each default in brackets.
- Empty input → default. EOF → default for THIS and ALL remaining (catch
  EOFError, fall back to non-interactive for the rest), exit 0 no traceback.
- Invalid answer → re-prompt with brief explanation.
- I/O injectable: `input_fn=input`, `output_fn=print` (seed #6). All prompting
  in cli.py.

### Data handling
- Required columns (PRD §8): Type1, Item, Description, OnHand, Warehouse,
  Allocated, Pending, Available, Units. Missing → exit 1 naming the column.
- Numeric cleaning (§9): strip whitespace, remove thousands `,`, parse
  Decimal; blank → 0 or None; negatives warn not crash. `"2,216.50"` → 2216.50.
- Description parse (§10): tolerant. Pattern roughly
  `PREFIX VINTAGE VARIETY BRAND MARKET BOTTLEml/PACKp [extra...]`.
  Token-based, not a brittle single regex over whole string — there are rows
  with trailing junk ("*back label only", "Stock for consol", "LCBO Updated",
  "Cleanskin EP WL 25"). Must not crash on `FV NV MXD CON 750ml/12p` (vintage
  "NV" not 2-digit) or rows missing market.
- Variety map (§11): CHR/SAB/PIN/PIG/PRO/RDB/MXD. Unknown → keep code visible
  + warning.
- Vintage (§12): 2-digit → 20xx. "NV"/non-numeric stays Unknown + warning.
- Market (§13): preserve as found.
- 9LE (§14): `litres = qty * pack * bottle_ml/1000; 9LE = litres/9`, Decimal.
  750/12 → 9LE == cases; 750/6 → cases/2. Report rounded 2dp (26.67/6p →
  13.335 → 13.34). Floats only at formatting edge if at all.
- Unparseable bottle/pack: keep row in detail with 9LE shown `—`, warn,
  exclude from 9LE totals (cases still count in case totals).
- Basis switch (§15): OnHand vs Available drives wine totals; detail tables
  still show OnHand/Allocated/Pending/Available.
- Dry Goods (§16): never in wine 9LE totals, no 9LE, own section only when
  included, original units.

### Report (§19)
Header (Generated date, Source file, Warehouse(s), Stock basis) → Executive
Summary → SELECTED grouping table (none ⇒ omit grouping section) → Detailed
Finished Goods → Low Stock Warnings (when enabled; low = 9LE on chosen basis
< threshold) → Dry Goods Summary (when included) → Data Warnings.
Valid Markdown tables; correct totals are the contract, right-align is nicety.

### Tests (§23 minimums + §24 acceptance)
- Build rows in code; DO NOT assert fixture row counts/totals (§26).
- E2E smoke over fixture may assert structure/exit0/file-written, not totals.
- Coverage: csv_loader (valid, missing file, missing column, decimals,
  thousands, blanks), parser (the 3 example descriptions, vintage expand,
  variety map, unknown variety, non-matching desc), calculations (9LE 12p/6p,
  basis, dry-goods exclusion, aggregation by variety/vintage/market),
  validation (Available>OnHand, negative, unparseable pack/bottle, unknown
  units, unknown variety, FG not in cases), report (markdown, exec summary,
  grouping, detail, low-stock on/off, dry-goods on/off, data warnings).
- Tests import shared message constants, assert positive outcomes (seed #2, #7).

### README
What it does, both modes, every flag, one example command per §6/§18.

## Things I will specifically probe empirically
1. `--no-interactive --output r.md` exits 0, non-empty, has §19 sections.
2. `printf '' | ...` exits 0 (EOF → all defaults).
3. `--help` exit 0; unknown flag exit 2; missing file exit 1 `Error:` no TB.
4. Missing required column exit 1 naming column.
5. §24: 750/12 9LE==cases; 750/6 9LE==cases/2 (26.67→13.34); dry goods excluded.
6. `"2,216.50"` → 2216.50; negatives warn not crash.
7. `FV 22 RDB EP UK 750ml/6p Legacy Red` → extra desc "Legacy Red";
   unparseable desc → Unknown row + warning, no exception.
8. Switching basis/group-by/no-dry-goods/threshold visibly changes report.
9. Decimal used for 9LE (grep for float() in calc path = smell).
10. Anti-hardcoding: run on truncated CSV → different totals.
11. Stdlib only; no committed bytecode; base files untouched.

## Anticipated failure modes (from seed tips + task shape)
- try/except SystemExit swallowing usage errors (seed #4).
- EOF handling that crashes with EOFError traceback instead of defaulting.
- Float arithmetic in 9LE producing 13.33 instead of 13.34, or drift.
- Brittle regex parser that crashes on `FV NV MXD CON` or trailing-junk rows.
- Dry goods leaking into wine 9LE totals.
- Hardcoded fixture totals in tests.
- `--no-dry-goods` / `--group-by none` not actually changing output.
- Low-stock threshold compared against cases instead of 9LE.
- Thousands-separator rows crashing Decimal().
- Unparseable pack/bottle dropped entirely instead of kept-with-dash.
- Message strings re-typed in tests instead of imported (seed #7).
```
