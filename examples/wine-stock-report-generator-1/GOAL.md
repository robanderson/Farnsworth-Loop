# Wine Stock Report Generator — Goal Brief

This file is the loop's termination contract (Farnsworth PRD Section 2.4).
The loop cycles — one task per iteration, each derived from the gap between
the merged state and this goal — until BOTH halves of done pass. Nothing in
this file pre-plans the task list; iteration count is emergent.

## Objective

A complete, working Wine Stock Report Generator: the command-line tool
specified in `PRD.md`, launchable as `python3 -m wine_stock_reporter`,
that converts a warehouse stock-on-hand CSV into a human-readable Markdown
stock report and meets every item in PRD section 26 (Definition of Done).

## Done — mechanical half

The `goal.done` checks in `farnsworth.json`, run by `farnsworth done`
against the merged state from the repo root:

1. `acceptance` — `python3 -m unittest discover -s tests` exits 0.
2. `compiles` — `python3 -m compileall -q wine_stock_reporter` exits 0.
3. `report-noninteractive` — the tool processes `examples/stock_sample.csv`
   with `--no-interactive`, exits 0, and writes a non-empty report file.
4. `report-interactive-eof` — `printf '' | python3 -m wine_stock_reporter
   examples/stock_sample.csv --output ...` exits 0 (EOF at a prompt accepts
   the default for that and all remaining questions, never a traceback).
5. `help` — `python3 -m wine_stock_reporter --help` exits 0.
6. `usage-error` — an unknown flag exits 2.
7. `missing-file` — a nonexistent CSV path exits 1 (clear one-line error,
   no traceback).

## Done — semantic half

The reviewer attests, in its final review, that the merged state meets
PRD section 26 in full, and specifically that:

- The PRD section 24 acceptance examples hold, verified empirically:
  the `FV 22 CHR EP NZ 750ml/12p` row parses to vintage 2022 / Chardonnay /
  NZ / 750ml / 12p with 9LE equal to its cases; the `750ml/6p` row's 9LE is
  half its cases (26.67 → 13.34 rounded); the Dry Goods row is excluded
  from wine totals, gets no 9LE, and appears only in the Dry Goods section.
- The report contains the PRD section 19 structure: executive summary,
  the selected grouping table, detailed finished goods, low-stock warnings
  (when enabled), dry goods summary (when included), and data warnings.
- PRD section 20 validation rules produce visible warnings (at minimum:
  negative quantities, Available > OnHand, unparseable descriptions,
  unknown variety codes — exercised against constructed data, not only the
  fixture).
- The user can switch basis (`OnHand`/`Available`), grouping, dry-goods
  inclusion, and low-stock threshold, and the report visibly changes
  accordingly.
- 9LE arithmetic uses `Decimal`, and `4,270.00`-style thousands separators
  parse correctly.
- Nothing is hardcoded to the fixture: running the tool on a modified or
  truncated copy of the CSV produces correspondingly different totals
  (PRD section 26's anti-hardcoding clause, probed empirically).
- A README explains how to run the program, both modes.

## Exits

DONE when both halves pass. ESCALATED if a change request blocks all
remaining work. STOPPED at the orchestrator's budget (4 iterations for
this run). STALLED after 3 consecutive iterations without measurable
progress on the done checks.
