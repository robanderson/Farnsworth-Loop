# PRD: Wine Stock Report Generator

**Project type:** AI coding-agent benchmark project  
**Primary output:** Command-line/TUI tool that converts a warehouse stock CSV into a human-readable Markdown report  
**Fixture data:** Embedded real CSV included at the end of this document  
**Prepared for:** AI agent loop / coding benchmark  
**Date:** 2026-06-12

---

## 1. Purpose

Build a small but realistic software project that can be given to an AI coding agent.

The agent must create a program that imports a warehouse stock-on-hand CSV file for wine inventory, asks a few clarification questions, and generates a human-readable Markdown stock report.

The goal of this project is **not** to manually solve the stock report once. The goal is to test whether a custom AI agent loop can:

- read and understand a PRD,
- inspect real-world CSV data,
- ask useful clarification questions,
- implement code,
- write tests,
- run tests,
- debug failures,
- refine the implementation,
- and stop only when the project is working and all tests pass.

---

## 2. Product Summary

**Wine Stock Report Generator** converts a warehouse stock-on-hand CSV into a readable Markdown stock report.

The report should summarise finished wine stock, dry goods, available stock, allocated stock, pack sizes, vintage, variety, market, low-stock warnings, and data quality warnings.

The first version should be a CLI program. A richer TUI may be added later.

---

## 3. Benchmark Rationale

This is intended as a better-than-Hello-World agent benchmark.

It is small enough to complete in a few agent iterations, but realistic enough to expose weak coding-agent behaviour.

It tests:

- CSV parsing,
- messy real-world data,
- interactive clarification,
- domain-specific parsing,
- grouping and aggregation,
- decimal calculations,
- Markdown report generation,
- validation warnings,
- unit testing,
- golden-file style report testing,
- and iterative bug fixing.

Expected completion should take roughly **2–5 AI agent rounds**, depending on the capability of the coding agent.

---

## 4. Target User

The end user is a wine business operator who has received a warehouse stock-on-hand export and wants a clean business-readable report.

The developer user is an AI coding agent being benchmarked on a realistic small-business coding task.

---

## 5. Input Data

The program accepts a CSV file exported from a warehouse system.

The supplied fixture CSV contains these columns:

```csv
Type1,Item,Description,ClientStockCode,ClientStockDescription,Lot,OnHand,Warehouse,Allocated,Pending,Available,Units
```

Known values in the `Type1` column include:

- `Finished Goods`
- `Dry Goods`

Known values in the `Units` column include:

- `Cases`
- `Eaches`

The embedded fixture contains both saleable finished wine and dry goods such as labels or packaging materials.

---

## 6. Main User Flow

Example command:

```bash
wine-stock-report stock_sample.csv
```

The program loads the file and asks clarification questions:

```text
Loaded stock_sample.csv.

Detected:
- Finished Goods rows
- Dry Goods rows
- Warehouse: Marlborough
- Units: Cases, Eaches

Report options:

1. Use OnHand or Available stock for wine totals? [Available]
2. Include Dry Goods section? [yes]
3. Group primary wine summary by variety, vintage, market, pack_size, or lot? [variety]
4. Include low-stock warnings? [yes]
5. Low-stock threshold in 9LE? [10]
6. Output filename? [stock-report.md]
```

Then it writes a Markdown report.

```text
Report written to stock-report.md
```

---

## 7. Required Behaviour

The program must:

1. Accept a CSV file path.
2. Load the CSV.
3. Validate required columns.
4. Clean and normalise numeric fields.
5. Separate Finished Goods from Dry Goods.
6. Parse wine metadata from Finished Goods descriptions where possible.
7. Calculate 9-litre-equivalent stock, abbreviated as `9LE`.
8. Ask clarification questions unless running in non-interactive mode.
9. Generate a Markdown report.
10. Write the report to a file.
11. Include data warnings for suspicious or unparseable rows.
12. Include automated tests.

---

## 8. Required CSV Columns

The following columns are required:

```text
Type1
Item
Description
OnHand
Warehouse
Allocated
Pending
Available
Units
```

The following columns may exist and may be empty:

```text
ClientStockCode
ClientStockDescription
Lot
```

If a required column is missing, the program must fail with a clear error.

Example:

```text
Error: required column 'Available' was not found in CSV.
```

---

## 9. Data Cleaning Requirements

The agent must not assume all numeric fields are already clean Python numbers.

The program should parse numeric strings such as:

```text
13.67
156.00
4,270.00
0.00
```

It should handle:

- blank nullable fields,
- decimal places,
- thousands separators,
- leading/trailing whitespace,
- zero values,
- and negative values.

Negative values should not crash the program, but they should generate a validation warning.

---

## 10. Finished Goods Parsing

For rows where `Type1` is `Finished Goods`, parse the `Description` field.

Example:

```text
FV 22 CHR EP NZ 750ml/12p
```

Expected parsed fields:

```text
Prefix: FV
Vintage: 2022
Variety code: CHR
Brand/code: EP
Market: NZ
Bottle size: 750ml
Pack size: 12
```

Another example:

```text
FV 22 RDB EP UK 750ml/6p Legacy Red
```

Expected parsed fields:

```text
Prefix: FV
Vintage: 2022
Variety code: RDB
Brand/code: EP
Market: UK
Bottle size: 750ml
Pack size: 6
Extra description: Legacy Red
```

The parser must be tolerant.

If a row cannot be parsed fully, the program should:

- still include the row in the report,
- leave unknown parsed fields blank or marked as `Unknown`,
- and add a data warning.

The parser must not crash because of one unusual description.

---

## 11. Variety Code Mapping

The first implementation should support at least these mappings:

| Code | Variety |
|---|---|
| CHR | Chardonnay |
| SAB | Sauvignon Blanc |
| PIN | Pinot Noir |
| PIG | Pinot Gris |
| PRO | Rosé |
| RDB | Red Blend |
| MXD | Mixed / Consolidated |

Unknown variety codes should remain visible in the report and be listed in data warnings.

Example warning:

```text
Unknown variety code 'ABC' in item 123456.
```

---

## 12. Vintage Parsing

Two-digit vintages should be expanded to four digits.

Examples:

| Input | Output |
|---|---|
| 20 | 2020 |
| 21 | 2021 |
| 22 | 2022 |
| 23 | 2023 |
| 24 | 2024 |
| 25 | 2025 |

For version 1, assume two-digit vintage values refer to years from 2000 to 2099.

---

## 13. Market Parsing

The parser should extract market codes from descriptions where possible.

Examples from the fixture include:

| Code | Likely Meaning |
|---|---|
| NZ | New Zealand |
| CA | Canada |
| UK | United Kingdom |
| UC | United States / USA channel |
| AN | Australia/New Zealand or internal market code |

The program does not need to know the full meaning of every market code in version 1.

It should preserve the market code as found.

---

## 14. 9LE Calculation

The report must calculate stock in 9-litre-equivalent cases, abbreviated as `9LE`.

Formula:

```text
litres = quantity × pack_size × bottle_size_litres
9LE = litres / 9
```

For the common wine cases in this fixture:

| Bottle Size | Pack | 9LE per Case |
|---|---:|---:|
| 750ml | 12p | 1.0 |
| 750ml | 6p | 0.5 |

Examples:

```text
48.58 cases of 750ml/12p = 48.58 9LE
26.67 cases of 750ml/6p = 13.335 9LE
```

Report values may be rounded to two decimal places.

Internal calculations should avoid unnecessary floating point errors. Using Python `Decimal` is preferred.

---

## 15. Stock Quantity Basis

The user must be able to choose whether wine totals use:

- `OnHand`
- `Available`

Default:

```text
Available
```

The report should still include `OnHand`, `Allocated`, `Pending`, and `Available` columns in detailed tables where useful.

---

## 16. Dry Goods Handling

Rows where `Type1` is `Dry Goods` should not be included in wine 9LE totals.

Dry Goods should be included in a separate section if the user chooses to include them.

Dry Goods should be reported in their original units, usually `Eaches`.

Dry Goods do not require 9LE calculation.

Suggested Dry Goods section:

```markdown
## Dry Goods Summary

| Item | Description | Available | Units |
|---|---|---:|---|
| 558243 | FV LA 25 SAB GL UK Front 12.5% ML FG087442 | 4270.00 | Eaches |
```

---

## 17. Clarification Questions

The interactive program should ask a small number of questions.

Required questions:

1. Should wine totals use `OnHand` or `Available`?
2. Should Dry Goods be included?
3. How should the main wine summary be grouped?
4. Should low-stock warnings be shown?
5. What is the low-stock threshold in 9LE?
6. What output filename should be used?

Valid grouping options:

```text
variety
vintage
market
pack_size
lot
none
```

Defaults:

```text
Quantity basis: Available
Include Dry Goods: yes
Group by: variety
Low-stock warnings: yes
Low-stock threshold: 10 9LE
Output filename: stock-report.md
```

---

## 18. Non-Interactive Mode

The program should support non-interactive mode for automated testing and CI.

Example:

```bash
wine-stock-report stock_sample.csv \
  --basis Available \
  --group-by variety \
  --include-dry-goods \
  --low-stock-threshold 10 \
  --output stock-report.md \
  --no-interactive
```

In non-interactive mode, the program must not prompt for input.

If required options are missing, it should use defaults.

---

## 19. Report Format

The program must generate a Markdown report.

Suggested structure:

```markdown
# Wine Stock Report

Generated: 2026-06-12
Source file: stock_sample.csv
Warehouse: Marlborough
Stock basis: Available

## Executive Summary

- Finished Goods rows: X
- Dry Goods rows: Y
- Total wine stock: X 9LE
- Total available cases: X
- Total allocated cases: X
- Total pending cases: X
- Lowest stock item: XYZ
- Data warnings: X

## Stock by Variety

| Variety | Rows | Cases | 9LE |
|---|---:|---:|---:|
| Sauvignon Blanc | 12 | 1000.00 | 1000.00 |
| Chardonnay | 6 | 500.00 | 375.00 |

## Stock by Vintage

| Vintage | Rows | Cases | 9LE |
|---|---:|---:|---:|
| 2022 | 10 | 500.00 | 400.00 |
| 2023 | 8 | 300.00 | 250.00 |

## Detailed Finished Goods

| Item | Description | Lot | Available | Units | 9LE |
|---|---|---|---:|---|---:|

## Low Stock Warnings

- Item X has only Y 9LE available.

## Dry Goods Summary

| Item | Description | Available | Units |
|---|---|---:|---|

## Data Warnings

- Unknown variety code: ABC
- Could not parse pack size for item XYZ
```

---

## 20. Validation Rules

The program should detect and warn about:

- missing required columns,
- empty descriptions,
- non-numeric stock quantities,
- unknown `Type1` values,
- unknown `Units` values,
- Finished Goods rows not measured in `Cases`,
- Dry Goods rows measured in unexpected units,
- unparseable bottle size,
- unparseable pack size,
- unknown variety code,
- negative stock values,
- `Available` greater than `OnHand`,
- and material mismatch where `OnHand - Allocated - Pending` does not equal `Available`.

Validation warnings should appear in the Markdown report.

Only fatal errors should stop processing.

---

## 21. Suggested Project Structure

```text
wine_stock_reporter/
  pyproject.toml
  README.md
  src/
    wine_stock_reporter/
      __init__.py
      cli.py
      csv_loader.py
      models.py
      parser.py
      calculations.py
      validation.py
      report.py
  tests/
    test_csv_loader.py
    test_parser.py
    test_calculations.py
    test_validation.py
    test_report.py
  examples/
    stock_sample.csv
    expected_report.md
```

---

## 22. Suggested Component Responsibilities

### `cli.py`

- parse command-line arguments,
- handle interactive prompts,
- support non-interactive defaults,
- call loader, parser, calculator, validator, and reporter,
- write the Markdown output file.

### `csv_loader.py`

- load CSV files,
- validate required columns,
- normalise row data,
- parse numeric columns,
- return structured records.

### `models.py`

- define typed dataclasses or Pydantic models,
- represent raw stock rows,
- represent parsed wine rows,
- represent report options,
- represent validation warnings.

### `parser.py`

- parse `Description`,
- extract vintage, variety code, market, bottle size, and pack size,
- map variety codes,
- return parse warnings.

### `calculations.py`

- calculate litres,
- calculate 9LE,
- aggregate by selected grouping,
- calculate totals,
- identify low-stock items.

### `validation.py`

- validate row-level data,
- detect suspicious quantities,
- produce non-fatal warnings.

### `report.py`

- render Markdown,
- format tables,
- include executive summary,
- include grouping sections,
- include detailed rows,
- include warnings.

---

## 23. Minimum Automated Tests

The project must include tests.

The agent is not done until all tests pass.

### CSV Loading Tests

- loads a valid CSV,
- fails clearly when the file does not exist,
- fails clearly when required columns are missing,
- parses decimal numeric strings,
- parses numbers with thousands separators,
- handles blank nullable fields.

### Parser Tests

- parses `FV 22 CHR EP NZ 750ml/12p`,
- parses `FV 22 CHR EP AN 750ml/6p`,
- parses `FV 22 RDB EP UK 750ml/6p Legacy Red`,
- expands vintage `22` to `2022`,
- maps `CHR` to `Chardonnay`,
- maps `SAB` to `Sauvignon Blanc`,
- handles unknown variety codes,
- handles descriptions that do not match the expected pattern.

### Calculation Tests

- calculates 9LE for `750ml/12p`,
- calculates 9LE for `750ml/6p`,
- uses `Available` when selected,
- uses `OnHand` when selected,
- excludes Dry Goods from wine totals,
- does not calculate 9LE for Dry Goods,
- aggregates correctly by variety,
- aggregates correctly by vintage,
- aggregates correctly by market.

### Validation Tests

- warns when `Available` is greater than `OnHand`,
- warns when stock quantity is negative,
- warns when pack size cannot be parsed,
- warns when bottle size cannot be parsed,
- warns on unknown units,
- warns on unknown variety code,
- warns when Finished Goods are not in cases.

### Report Tests

- generates Markdown,
- includes executive summary,
- includes selected grouping table,
- includes detailed finished goods table,
- includes low-stock warnings when enabled,
- excludes low-stock warnings when disabled,
- includes dry goods section only when requested,
- includes data warnings.

---

## 24. Example Acceptance Tests

Given this CSV row:

```csv
Finished Goods,747691,FV 22 CHR EP NZ 750ml/12p,,Eva 22 CHR 12pk,W39189,48.58,Marlborough,0.00,0.00,48.58,Cases
```

The parser should produce:

```json
{
  "type": "Finished Goods",
  "item": "747691",
  "vintage": "2022",
  "variety_code": "CHR",
  "variety": "Chardonnay",
  "market": "NZ",
  "bottle_size_ml": 750,
  "pack_size": 12,
  "available": "48.58",
  "units": "Cases",
  "nine_litre_equivalent": "48.58"
}
```

Given this CSV row:

```csv
Finished Goods,747690,FV 22 CHR EP NZ 750ml/6p,,Eva 22 CHR 6pk,W39189,26.67,Marlborough,0.00,0.00,26.67,Cases
```

The calculated 9LE should be:

```text
13.335
```

Rounded report value:

```text
13.34
```

Given this CSV row:

```csv
Dry Goods,558243,FV LA 25 SAB GL UK Front 12.5% ML FG087442,GLSB25UK-FL,GLSB25UK-FL,,4270.00,Marlborough,0.00,0.00,4270.00,Eaches
```

The row should:

- be excluded from wine totals,
- be included in the Dry Goods section only when requested,
- and not receive a 9LE calculation.

---

## 25. Expected Agent Loop

This project is expected to require several coding-agent passes.

Suggested loop:

```text
Round 1: Create basic CLI, CSV loader, Markdown report, and simple tests.
Round 2: Add wine description parser and 9LE calculations.
Round 3: Add validation warnings and dry-goods handling.
Round 4: Add non-interactive mode and improve tests.
Round 5: Polish report formatting and README.
```

The agent should be expected to:

- inspect the supplied CSV,
- infer structure without overfitting,
- implement code,
- write tests,
- run tests,
- fix failures,
- preserve user-facing clarity,
- and avoid hardcoding the exact fixture row count or output.

---

## 26. Definition of Done

The project is complete when:

- the CLI accepts a CSV path,
- the embedded fixture CSV can be processed,
- a Markdown report is written,
- Finished Goods and Dry Goods are handled separately,
- 9LE calculations are correct for `750ml/12p` and `750ml/6p`,
- the user can choose `OnHand` or `Available`,
- the user can choose at least one grouping option,
- low-stock warnings work,
- data warnings are included,
- unit tests exist,
- all tests pass,
- the README explains how to run the program,
- non-interactive mode works,
- and the code does not hardcode the supplied filename, row count, or report totals.

---

## 27. Out of Scope for Version 1

Version 1 does not need:

- database storage,
- web UI,
- authentication,
- PDF output,
- Excel output,
- email sending,
- live warehouse integration,
- AI-generated prose summaries,
- sales velocity forecasting,
- inventory valuation,
- or multi-warehouse reconciliation.

---

## 28. Stretch Goals

Future improvements may include:

- export to HTML,
- export to PDF,
- export to Excel,
- compare two stock files and produce a movement report,
- add inventory valuation from a price list,
- add reorder thresholds by SKU,
- add market-specific reports,
- add dry-goods usage estimation,
- add config file for variety mappings,
- add CI workflow,
- add golden-file tests for report output,
- add a richer TUI interface.

---

## 29. README One-Liner

**Wine Stock Report Generator** converts a real warehouse stock-on-hand CSV into a readable Markdown stock report, including finished wine stock, 9LE totals, grouping summaries, low-stock warnings, dry goods, and data validation notes.

---

# Appendix A: Embedded Fixture CSV

Save the following content as:

```text
examples/stock_sample.csv
```

```csv
Type1,Item,Description,ClientStockCode,ClientStockDescription,Lot,OnHand,Warehouse,Allocated,Pending,Available,Units
Finished Goods,742261,FV 20 CHR EP CA 750ml/12p,,Eva 20 CHR 12pk CA,W33265,13.67,Marlborough,0.00,0.00,13.67,Cases
Finished Goods,748959,FV 21 SAB EP UC 750ml/12p,737897,FV 21 SAB EP USA 750ml/12p,W37948,156.00,Marlborough,0.00,0.00,156.00,Cases
Finished Goods,766163,FV 22 CHR EP AN 750ml/6p,,EPCH22NZ,W39189,320.83,Marlborough,0.00,0.00,320.83,Cases
Finished Goods,747691,FV 22 CHR EP NZ 750ml/12p,,Eva 22 CHR 12pk,W39189,48.58,Marlborough,0.00,0.00,48.58,Cases
Finished Goods,747690,FV 22 CHR EP NZ 750ml/6p,,Eva 22 CHR 6pk,W39189,26.67,Marlborough,0.00,0.00,26.67,Cases
Finished Goods,769496,FV 22 CHR EP UK 750ml/6p,,EP WL Chard 22 - UK,W39189,111.33,Marlborough,0.00,0.00,111.33,Cases
Finished Goods,747609,FV 22 PIN EP NZ 750ml/12p,,Eva 22 PN 12pk,W39190,10.17,Marlborough,0.00,0.00,10.17,Cases
Finished Goods,747611,FV 22 PIN EP NZ 750ml/6p,,Eva 22 PN 6pk,W39190,12.00,Marlborough,0.00,0.00,12.00,Cases
Finished Goods,768013,FV 22 PIN EP US 750ml/12p,EP PN US 12 22 TTB,Celeste PN 22 USA,W39190,10.00,Marlborough,0.00,0.00,10.00,Cases
Finished Goods,770024,FV 22 RDB EP UK 750ml/6p Legacy Red,EP WL LR 22 - UK,EP WL LR 22 - UK,L51676-R51676,143.67,Marlborough,0.00,0.00,143.67,Cases
Finished Goods,765909,FV 22 SAB EP NZ 750ml/12p,,2022 SB NZ,W39186,86.33,Marlborough,0.00,0.00,86.33,Cases
Finished Goods,753031,FV 22 SAB EP NZ 750ml/6p,,Eva 22 SB 6pk,22EPSB-W39188,24.00,Marlborough,0.00,0.00,24.00,Cases
Finished Goods,742822,FV 22 SAB EP US 750ml/12p,,Eva 22 SB 12pk,W39186,99.25,Marlborough,0.00,0.00,99.25,Cases
Finished Goods,768616,FV 22 SAB EP US 750ml/12p,US Reconfig,EP 22 SB USA 12 Pallet R,W39186,395.00,Marlborough,0.00,0.00,395.00,Cases
Finished Goods,747253,FV 22 SAB EP X+ 750ml/12p,,Eva 22 SB 12pk,22EPSB-W39188,68.67,Marlborough,0.00,0.00,68.67,Cases
Finished Goods,766286,FV 23 PIN EP NZ 750ml/6p,,EPRPN23NZ6,23EPPN-W43531,288.83,Marlborough,3.17,0.00,285.67,Cases
Finished Goods,756598,FV 23 PIN EP X+ 750ml/12p,,23 EP PN - Cleanskin,23EPPN-W43531,122.42,Marlborough,0.00,0.00,122.42,Cases
Finished Goods,770089,FV 24 PIG EP UK 750ml/6p,EPWLPG24 (UK),EPWLPG24-UK,24CDPG-W52446,159.67,Marlborough,0.00,0.00,159.67,Cases
Finished Goods,770018,FV 24 PIN EP UK 750ml/6p,EP WL PN 24 (UK),EP WL PN 24 (UK),24EPPN-W48871,86.00,Marlborough,0.00,0.00,86.00,Cases
Finished Goods,765707,FV 24 PIN EP X+ 750ml/12p,2024 Eva Pinot Noir,24 EP PN - Cleanskin,24EPPN-W48871,478.75,Marlborough,0.00,0.00,478.75,Cases
Finished Goods,769809,FV 24 PIN GL UK 750ml/6p,Gatelands PN 24 (UK),Gatelands PN '24 (UK),24TPPN-W54111,809.83,Marlborough,0.00,0.00,809.83,Cases
Finished Goods,759292,FV 24 PRO EP NZ 750ml/12p,,Eva 24 Rosé,24EPRO-W48866,53.50,Marlborough,0.00,0.00,53.50,Cases
Finished Goods,759293,FV 24 PRO EP NZ 750ml/12p *back label only,,Eva 24 Rosé,24EPRO-W48866,9.50,Marlborough,0.00,0.00,9.50,Cases
Finished Goods,760706,FV 24 PRO EP NZ 750ml/6p,,Eva 24 Rosé,24EPRO-W48866,1.00,Marlborough,1.00,0.00,0.00,Cases
Finished Goods,764615,FV 24 PRO EP X+ 750ml/12p,,Eva 24 Rosé,24EPRO-W49991,82.75,Marlborough,0.00,0.00,82.75,Cases
Finished Goods,764951,FV 24 PRO EP X+ 750ml/12p,,Eva 24 Rosé,24EPRO-W49991,403.83,Marlborough,0.00,0.00,403.83,Cases
Finished Goods,766167,FV 24 SAB EP AN 750ml/6p,,EPSB24NZ,24SB COMM-W50300,436.50,Marlborough,1.00,0.00,435.50,Cases
Finished Goods,771637,FV 24 SAB EP CA 750ml/12p LCBO Updated,EPWLSB24LCBO New,EPWLSB24LCBO,24SB COMM-W50300,2.00,Marlborough,0.00,0.00,2.00,Cases
Finished Goods,763025,FV 24 SAB EP CC 750ml/12p,,2024 SB NZ - Reserve,24SBEP RES-W50299,523.58,Marlborough,0.00,0.00,523.58,Cases
Finished Goods,763026,FV 24 SAB EP CC 750ml/12p,,2024 SB NZ - Commercial,24SB COMM-W50300,644.75,Marlborough,0.00,0.00,644.75,Cases
Finished Goods,766287,FV 24 SAB EP NZ 750ml/6p,,EPRSBNZ6,24SBEP RES-W50299,408.17,Marlborough,0.17,0.00,408.00,Cases
Finished Goods,769494,FV 24 SAB EP UK 750ml/6p,,EPWLSB24-UK,24SB COMM-W50300,0.83,Marlborough,0.00,0.00,0.83,Cases
Finished Goods,769499,FV 24 SAB EP UK 750ml/6p,,EP Res SB 24 (UK),24SBEP RES-W50299,0.50,Marlborough,0.00,0.00,0.50,Cases
Finished Goods,774713,FV 25 PIN EP X+ 750ml/12p,2025 Eva Pinot Noir,25 EP PN - Cleanskin,25EPRESPN-W52457,553.25,Marlborough,0.00,0.00,553.25,Cases
Finished Goods,776561,FV 25 SAB EP CON 750ml/12p,,2025 EPWLSB,W52458,0.08,Marlborough,0.00,0.00,0.08,Cases
Finished Goods,770017,FV 25 SAB EP UK 375ml/12p,EP WL SB 25 - 375ml (UK),EP WL SB 25 - 375ml (UK),25STSB-W52448,146.50,Marlborough,0.00,0.00,146.50,Cases
Finished Goods,773329,FV 25 SAB EP X+ 750ml/12p,,2025 EPWLSB,25EPSB WL-W52455,546.75,Marlborough,0.00,0.00,546.75,Cases
Finished Goods,773329,FV 25 SAB EP X+ 750ml/12p,,2025 EPWLSB,25EPSB WL-W52458,"2,216.50",Marlborough,0.00,0.00,"2,216.50",Cases
Finished Goods,774175,FV 25 SAB EP X+ 750ml/12p,2025 SB NZ - Reserve,2025 SB NZ - Reserve,25EPSB-RES-W52454,402.75,Marlborough,0.00,0.00,402.75,Cases
Finished Goods,770088,FV 25 SAB EP X+ 750ml/12p Cleanskin EP WL 25,EP WL SB 25 CS,EP WL SB 25 CS,25STSB-W52448,418.92,Marlborough,0.33,0.00,418.58,Cases
Finished Goods,769808,FV 25 SAB GL UK 750ml/6p,Gatelands SB 25 (UK),Gatelands SB '25 (UK),25FLSB-W52441,"1,105.33",Marlborough,0.00,0.00,"1,105.33",Cases
Finished Goods,769868,FV 25 SAB SSK X+ 750ml/12p,SSSBX+,Sunstruck SC Cleanskin,25FLSB-W53964,35.00,Marlborough,0.00,0.00,35.00,Cases
Dry Goods,535783,FV CP SCR PR BLK EP Non Knurl CV6413355A,,,,"2,637.00",Marlborough,0.00,0.00,"2,637.00",Eaches
Dry Goods,561242,FV CP SCR PR BLK GLD EP Non Knurl NZ.EVA.BG-NK,EP Branded Black - NEW,EP Branded Black - NEW,,"53,100.00",Marlborough,0.00,0.00,"53,100.00",Eaches
Dry Goods,554489,FV CT BRG PR EP 06-SU WHI EPWLLWBurg6 VP146538,EPWLLWBurg6,Eva Pemper WL 6x750 LW Burg,,"1,037.00",Marlborough,0.00,0.00,"1,037.00",Eaches
Dry Goods,555936,FV CT BRG PR EP 12-SU WHI 12x750ml Eva Pemper 390g LW Burg 2 Col - LCBO,EPWLLWBurg12,Eva Pemper WL 12x750ml LW Burg (LCBO),,"1,375.00",Marlborough,0.00,0.00,"1,375.00",Eaches
Dry Goods,554491,FV CT PBG PR EP 06-SU BLK EPRESPremBurg6 VP146540,,EPRESPremBurg6,,"1,200.00",Marlborough,0.00,0.00,"1,200.00",Eaches
Dry Goods,554490,FV CT PBG PR EP 06-SU WHI EPWLPremB6 VP146541,EPWLPremB6,EP WL Prem Burg 6 x 750ml,,"1,245.00",Marlborough,0.00,0.00,"1,245.00",Eaches
Dry Goods,561241,FV CT PBG PR EP 12-SU BLK VP220063,EPR12x750PB,EPRES - 12 x 750 ml P.Burg,,"1,500.00",Marlborough,0.00,0.00,"1,500.00",Eaches
Dry Goods,554492,FV CT PBG PR EP 12-SU WHI VP148758,,EPWLPremBx12,,800.00,Marlborough,0.00,0.00,800.00,Eaches
Dry Goods,557968,FV LA 22 CHR EP GN Front ML,,EP WL Chard 22 (UK) - Front,,"1,972.00",Marlborough,0.00,0.00,"1,972.00",Eaches
Dry Goods,556416,FV LA 22 CHR EP US Back 13.0% ML 2022 CH USA_90x80_Eva back label TTB,22 CH USA_90x80_EP BL TTB,EP WL Chard 22 TTB Approved - Back,,245.00,Marlborough,0.00,0.00,245.00,Eaches
Dry Goods,539224,FV LA 22 PIN EP GN Front ML FG061837,,,,70.00,Marlborough,0.00,0.00,70.00,Eaches
Dry Goods,558087,FV LA 22 PIN EP UK Back 14.5% ML L3067,,EP WL PN 22 (UK) - Back,,12.00,Marlborough,0.00,0.00,12.00,Eaches
Dry Goods,556419,FV LA 22 PIN EP US Back 14.0% ML 2022 PN USA_90x80_Eva back label,22 PN USA 90x80 EP BL TTB,EP PNoir 22 BL - TTB approved,,91.00,Marlborough,0.00,0.00,91.00,Eaches
Dry Goods,554280,FV LA 23 PIN EP AN Back 14.5% ML FG081639,,EPRESPN23,,60.00,Marlborough,0.00,0.00,60.00,Eaches
Dry Goods,554279,FV LA 23 PIN EP GN Front ML FG081638,,EPRESPN23,,50.00,Marlborough,0.00,0.00,50.00,Eaches
Dry Goods,557971,FV LA 23 PIN EP UK Back 15.0% ML *L43531 Reserve,,EP Res PN 23 (UK) - Back,,10.00,Marlborough,0.00,0.00,10.00,Eaches
Dry Goods,558395,FV LA 24 PIG EP GN Front ML,EP WL PG 24 UK - FL,EP WL PG 24 UK - FL,,180.00,Marlborough,0.00,0.00,180.00,Eaches
Dry Goods,558455,FV LA 24 PIG EP UK Back 13.5% ML FG087694,EP WL PG 24 UK - BL,EP WL PG 24 UK - BL,,180.00,Marlborough,0.00,0.00,180.00,Eaches
Dry Goods,558403,FV LA 24 PIN EP GN Front ML,EP WL PN 24 UK FL,EP WL PN 24 UK FL,,578.00,Marlborough,0.00,0.00,578.00,Eaches
Dry Goods,558404,FV LA 24 PIN EP UK Back 14.5% ML,EP WL PN 24 UK BL,EP WL PN 24 UK BL,,578.00,Marlborough,0.00,0.00,578.00,Eaches
Dry Goods,558246,FV LA 24 PIN GL UK Back 13.0% ML FG087463,GLPN24(UK)-BL,GLPN24(UK)-BL,,130.00,Marlborough,0.00,0.00,130.00,Eaches
Dry Goods,558245,FV LA 24 PIN GL UK Front ML FG087462,GLPN24(UK)-FL,GLPN24(UK)-FL,,120.00,Marlborough,0.00,0.00,120.00,Eaches
Dry Goods,549470,FV LA 24 PRO EP GN Front 13.0% ML FG075820,,,,"5,790.00",Marlborough,0.00,0.00,"5,790.00",Eaches
Dry Goods,549469,FV LA 24 PRO EP NZ Back 13.0% ML 246116,,,,"5,180.00",Marlborough,0.00,0.00,"5,180.00",Eaches
Dry Goods,556418,FV LA 24 PRO EP US Back 13.0% ML 2024 PNR USA_90x80_Eva back label,24 EP PNR US 90x80_BL TTB,24 EP PNR BL USA TTB Approved,,211.00,Marlborough,0.00,0.00,211.00,Eaches
Dry Goods,555161,FV LA 24 SAB 15V CH Back 13.0% ML,15VSB24CHB,15th Valley SB China 24 - Back Lbl,,178.00,Marlborough,0.00,0.00,178.00,Eaches
Dry Goods,555163,FV LA 24 SAB 15V CH Back 13.0% ML *Special Release,15thSRSBCHB,15th Valley SR SB China 24 - Back Lbl,,148.00,Marlborough,0.00,0.00,148.00,Eaches
Dry Goods,555160,FV LA 24 SAB 15V CH Front 13.0% ML,15VSB24CHF,15th Valley SB China - Front Lbl,,158.00,Marlborough,0.00,0.00,158.00,Eaches
Dry Goods,555162,FV LA 24 SAB 15V CH Front ML *Special Release,15thSRSBCHF,15th Valley SR SB China 24 - Front Lbl,,178.00,Marlborough,0.00,0.00,178.00,Eaches
Dry Goods,554285,FV LA 24 SAB EP AN Back 13.0% ML FG081635,,EPWLSB24,,"13,690.00",Marlborough,0.00,0.00,"13,690.00",Eaches
Dry Goods,558398,FV LA 24 SAB EP CA Back 13.0% ML *L50300,EP WL SB 24 LCBO - BL,EP WL SB 24 LCBO - BL,,"9,100.00",Marlborough,0.00,0.00,"9,100.00",Eaches
Dry Goods,559745,FV LA 24 SAB EP CA Back 13.0% ML FG089572 Updated Artwork (Barcode),EPWLSB24LCBOBLUpdated,EPWLSB24LCBOBLUpdated,,510.00,Marlborough,0.00,0.00,510.00,Eaches
Dry Goods,554277,FV LA 24 SAB EP GN Front 13.0% ML FG081636,,EPRESSB24 - Front,,744.00,Marlborough,0.00,0.00,744.00,Eaches
Dry Goods,554281,FV LA 24 SAB EP GN Front ML FG081634,,EPWLSB24,,"13,910.00",Marlborough,0.00,0.00,"13,910.00",Eaches
Dry Goods,557974,FV LA 24 SAB EP UK Back 13.0% ML,,EP Res ASB 24 (UK) - Back,,424.00,Marlborough,0.00,0.00,424.00,Eaches
Dry Goods,557976,FV LA 24 SAB EP UK Back 13.0% ML *L50300,,EP WL SB 24 (UK) - Back,,29.00,Marlborough,0.00,0.00,29.00,Eaches
Dry Goods,561235,FV LA 25 SAB EP ANU Back 12.5% ML FG091461,,EPWLSAB25BNZ,,"7,470.00",Marlborough,0.00,0.00,"7,470.00",Eaches
Dry Goods,558397,FV LA 25 SAB EP GN Front ML 375ml,EP WL SB 25 375 UK - FL,EP WL SB 25 375 UK - FL,,268.00,Marlborough,0.00,0.00,268.00,Eaches
Dry Goods,561234,FV LA 25 SAB EP GN Front ML FG091460,,EPWLSB25FNZ,,"8,610.00",Marlborough,0.00,0.00,"8,610.00",Eaches
Dry Goods,558396,FV LA 25 SAB EP UK Back 12.5% ML 375ml *L5258,EP WL SB 25 375 UK - BL,EP WL SB 25 375 UK - BL,,268.00,Marlborough,0.00,0.00,268.00,Eaches
Dry Goods,562578,FV LA 25 SAB EP US Back 12.5% ML FG092573,,,,"1,010.00",Marlborough,0.00,0.00,"1,010.00",Eaches
Dry Goods,558244,FV LA 25 SAB GL UK Back 12.5% ML FG087443,GLSB25UK-BL,GLSB25UK-BL,,"4,430.00",Marlborough,0.00,0.00,"4,430.00",Eaches
Dry Goods,558243,FV LA 25 SAB GL UK Front 12.5% ML FG087442,GLSB25UK-FL,GLSB25UK-FL,,"4,270.00",Marlborough,0.00,0.00,"4,270.00",Eaches
Dry Goods,557779,FV LA 25 SAB SB CH Back 12.5% ML FG086724,SthBaySB25BK,South Bay SB 25 Back,,296.00,Marlborough,0.00,0.00,296.00,Eaches
Dry Goods,557780,FV LA 25 SAB SB GN Front ML,SthBaySB25FR,South Bay SB 25 Front,,278.00,Marlborough,0.00,0.00,278.00,Eaches
Dry Goods,557818,FV LA 25 SAB SSK CH Back 12.5% ML FG086722,Sunstruck SB 25 BL,Sunstruck SB 25 BL - China,,278.00,Marlborough,0.00,0.00,278.00,Eaches
Dry Goods,557411,FV LA 25 SAB SSK CH Front ML Sunstruck,SSSBCHFL6,Sunstruck SB China Front,,296.00,Marlborough,0.00,0.00,296.00,Eaches
Dry Goods,555101,FV LA GN EP SI Strip NZ *Trident Importer,,Strip Trident Sing 50x12mm,,"3,989.00",Marlborough,0.00,0.00,"3,989.00",Eaches
Dry Goods,554274,FV LA GN MXD EP ANU Strip 13.0% ML SLUSNZ22,,Strip Label - US to NZ - SB22,,"2,500.00",Marlborough,0.00,0.00,"2,500.00",Eaches
Dry Goods,552456,FV LA GN SAB Front NEOCOMO42,,Parliament Wine,,850.00,Marlborough,0.00,0.00,850.00,Eaches
Dry Goods,552457,FV LA GN SAB NZ Back 13.0% ML NEOCOM043,,Parliament Wine,,"1,176.00",Marlborough,0.00,0.00,"1,176.00",Eaches
Finished Goods,744929,FV NV MXD CON 750ml/12p Stock for consol,,,WWML869515-LIB,26.00,Marlborough,0.00,0.00,26.00,Cases


```
