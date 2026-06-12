# Task 001 — Wine Stock Report Generator, complete program in one shot

## Goal

Implement the ENTIRE program described in `PRD.md` (read it first — it is
in this repository, with the fixture CSV at `examples/stock_sample.csv`) —
CSV loader, description parser, calculations, validation, Markdown report,
interactive + non-interactive CLI, tests, and README — in this one task.
This is not a milestone slice: when this task is done,
`python3 -m wine_stock_reporter examples/stock_sample.csv --no-interactive`
produces the finished report and the test suite proves the behavior.

The PRD is the specification of record. Where this brief pins a contract
the PRD leaves open (layout, flags, exit codes), this brief wins; for
everything else, PRD sections 7–20 define required behavior and PRD
section 26 defines done.

## Hard requirements

1. **Stdlib only, Python 3.11+.** Flat package layout (this brief
   overrides the PRD section 21 `src/` + `pyproject.toml` suggestion so
   the tool runs from the repo root with no install step):
   ```
   wine_stock_reporter/__init__.py
   wine_stock_reporter/__main__.py
   wine_stock_reporter/cli.py
   wine_stock_reporter/csv_loader.py
   wine_stock_reporter/models.py
   wine_stock_reporter/parser.py
   wine_stock_reporter/calculations.py
   wine_stock_reporter/validation.py
   wine_stock_reporter/report.py
   tests/__init__.py
   tests/...
   README.md
   ```
   Component responsibilities per PRD section 22. Tests may be one file or
   several, but live in `tests/` as a package.

2. **CLI contract — exact and CLOSED** (do not add, rename, or remove
   flags; propose changes via escalation, never silently in the diff):
   - Invocation: `python3 -m wine_stock_reporter CSV_PATH [options]`
   - `--basis {OnHand,Available}` (default `Available`)
   - `--group-by {variety,vintage,market,pack_size,lot,none}` (default
     `variety`)
   - `--include-dry-goods` / `--no-dry-goods` (default: include)
   - `--low-stock-warnings` / `--no-low-stock-warnings` (default: on)
   - `--low-stock-threshold N` (decimal 9LE threshold, default `10`)
   - `--output PATH` (default `stock-report.md`)
   - `--no-interactive` (skip all prompts, use effective option values)
   - Exit codes: 0 success; 2 usage error (argparse-native — never swallow
     `SystemExit`); 1 for data/file errors (missing file, missing required
     column, unreadable CSV) with a clear one-line `Error: ...` message on
     stderr and NO traceback.

3. **Interactive mode** (the default): after loading the CSV, print a
   short "Detected: ..." summary (row types, warehouse(s), units), then ask
   the six PRD section 17 questions in that order, showing each default.
   The default for each question is the effective CLI option value.
   - Empty input (just Enter) accepts the default.
   - EOF (`printf '' | ...`) accepts the default for that question AND all
     remaining questions — exit 0, never a traceback.
   - An invalid answer re-prompts with a brief explanation.
   - `--no-interactive` asks nothing.
   - All prompting lives in `cli.py` behind injectable I/O
     (`input_fn=input`, `output_fn=print`) so tests run hermetically.

4. **Data handling per the PRD:**
   - Required-column validation per section 8 (error message names the
     missing column).
   - Numeric cleaning per section 9: blanks, decimals, thousands
     separators (`"2,216.50"`), whitespace, zero, negatives (warn, don't
     crash).
   - Tolerant description parsing per section 10 (never crash on one odd
     description; unknown fields stay blank/`Unknown` + data warning),
     variety mapping per section 11, vintage expansion per section 12,
     market codes preserved per section 13.
   - 9LE per section 14, computed with `decimal.Decimal` (MUST — floats
     only at the formatting edge, if at all). Report values rounded to two
     decimal places.
   - Rows whose bottle size or pack size cannot be parsed: keep them in
     detail tables with 9LE shown as `—` and a data warning; exclude them
     from 9LE totals (their cases still count in case totals).
   - Basis switching per section 15; Dry Goods per section 16 (never in
     wine 9LE totals, no 9LE, own section only when included, original
     units).
   - Validation warnings per section 20, rendered in the report's Data
     Warnings section.

5. **Report** per section 19's structure: header (generated date, source
   file, warehouse(s), stock basis), executive summary, the SELECTED
   grouping table (`none` means no grouping section), detailed finished
   goods, low-stock warnings (when enabled; an item is low-stock when its
   9LE on the chosen basis is below the threshold), dry goods summary
   (when included), data warnings. Valid Markdown tables; right-aligned
   numeric columns are a nicety, correct totals are the contract.

6. **Tests** per PRD section 23, minimum coverage as listed there (CSV
   loading, parser, calculations, validation, report), plus the PRD
   section 24 acceptance examples as concrete test cases.
   `python3 -m unittest discover -s tests` must pass from the repo root.
   Build test rows directly in test code; do NOT assert the fixture CSV's
   row counts or totals (PRD section 26 forbids hardcoding them) — an
   end-to-end smoke test over `examples/stock_sample.csv` may assert
   structure (sections present, exit 0, file written), not totals.

7. **README.md**: what the tool does, how to run both modes, every flag,
   one example command per PRD section 6/18.

8. **Hygiene:** commit all work to the current branch with clear messages.
   Never commit `__pycache__`/`*.pyc` (a `.gitignore` exists). Never write
   or commit `.code-tips.md`. Do not modify `PRD.md`, `GOAL.md`,
   `farnsworth.json`, `tasks/`, or `examples/stock_sample.csv`.

## Acceptance criteria

- [ ] `python3 -m unittest discover -s tests` green from repo root.
- [ ] `python3 -m compileall -q wine_stock_reporter` green.
- [ ] `python3 -m wine_stock_reporter examples/stock_sample.csv
      --no-interactive --output r.md` exits 0 and writes a non-empty
      Markdown report with the section 19 structure.
- [ ] `printf '' | python3 -m wine_stock_reporter examples/stock_sample.csv`
      exits 0 (all defaults accepted) and writes the report.
- [ ] `--help` exits 0; an unknown flag exits 2; a missing CSV file exits 1
      with `Error: ...` on stderr and no traceback.
- [ ] A missing required column exits 1 with an error naming the column.
- [ ] PRD section 24 examples hold: 750ml/12p ⇒ 9LE == cases;
      750ml/6p ⇒ 9LE == cases/2 (26.67 ⇒ 13.34 in the report); the Dry
      Goods example row is excluded from wine totals and has no 9LE.
- [ ] `"2,216.50"` parses as 2216.50; negative values warn, not crash.
- [ ] `FV 22 RDB EP UK 750ml/6p Legacy Red` parses with extra description
      `Legacy Red`; an unparseable description yields a row marked
      `Unknown` plus a data warning, never an exception.
- [ ] Switching `--basis`, `--group-by`, `--no-dry-goods`,
      `--low-stock-threshold` visibly changes the report.
- [ ] Stdlib only; no committed bytecode; base files untouched.
