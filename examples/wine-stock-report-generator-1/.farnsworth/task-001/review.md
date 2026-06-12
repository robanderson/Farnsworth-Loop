# Review — Task 001: Wine Stock Report Generator (one-shot full program)

Reviewer working dir: `/home/user/wsr-run/task-001-review`. Every candidate
was applied with `git apply`, exercised empirically, then reverted with
`git reset --hard && git clean -fd -e .farnsworth` (plus manual removal of
gitignored `__pycache__` and report artifacts) before the next. The tree was
verified clean of candidate files between each. My blind sketch
(`blind-sketch.md`) was written before any diff was opened.

## Empirical harness

A shared probe (`.farnsworth/task-001/probe.sh`) ran, per candidate:
unittest discover; `compileall`; non-interactive run over the fixture
(`--output r.md`); piped-EOF interactive run (`printf '' | ...`); `--help`;
unknown flag; missing file; missing required column; `--basis OnHand`;
`--group-by none`; `--no-dry-goods`; `--low-stock-threshold 100`; and
`--group-by {vintage,market,pack_size,lot}`. The §24 numerics (750/12 ⇒
9LE==cases; 750/6 26.67 ⇒ 13.34; `Legacy Red` extra description; the
`FV NV MXD CON 750ml/12p Stock for consol` odd row; the `"2,216.50"`
thousands row; the Dry Goods example) were checked in each candidate's
report output and, where present, in its tests.

## Baseline result: ALL FIVE candidates are functionally complete

Every candidate (A–E) ships the full flat package layout, a README, exits
0/1/2 on the right paths, names the missing column on the §8 error, accepts
EOF as all-defaults without a traceback, renders the §19 section structure,
and makes `--basis`, `--group-by`, `--no-dry-goods`, and
`--low-stock-threshold` visibly change the report. All compute 9LE with
`Decimal` (no `float(` in any `calculations.py`), get 750/6 26.67 ⇒ 13.34
exactly, preserve the `Legacy Red` extra description, and parse `"2,216.50"`
to 2216.50. None hardcodes fixture totals in a smoke test. This is a strong
field — the decision turns on test rigor and report fidelity, not on
basic correctness.

## Per-candidate findings

### Candidate A — faithful report, untested interactive path
- **Good:** Richest detail table (Item, Description, Variety, Vintage,
  Market, Bottle/Pack, On Hand, Allocated, Pending, Available, Units, 9LE) —
  the fullest honoring of §15/§19. Data Warnings section ALWAYS present.
  Correctly shows `—` for the odd `MXD CON` row's 9LE and emits three data
  warnings for it (it treats the trailing `Stock for consol` as making the
  size unparseable; defensible). 26 tests, all green; clean compile.
  Anti-hardcoding smoke test asserts structure, not totals.
- **Bad:** The interactive prompt logic (`prompt_for_options`, the EOF
  branch at `cli.py:230`, the re-prompt loop) is **never unit-tested** — the
  test file imports `prompt_for_options` but never calls it and never
  injects an `input_fn`. The brief and seed tip #6 specifically call for
  hermetic interactive testing; A leaves the most contract-heavy surface
  unproven (it works at runtime, but on faith). Minor: one error path
  calls `output_fn("...", file=sys.stderr)`, passing a `file=` kwarg into
  the injected output function — fine for default `print`, brittle for a
  list-capturing test double. Single test file (`test_all.py`) rather than
  the per-module split §23 suggests.

### Candidate B — heaviest test count, one §19 fidelity gap
- **Good:** 100 tests, all green — the largest suite, split per §23 module.
  Explicit source comment refusing to wrap `parse_args` in `try/except
  SystemExit` (seed #4 internalized). All exit codes and switches correct.
  Crafted-bad-row probe confirmed: bogus description ⇒ 9LE `—` + warning;
  negatives, `Available>OnHand`, balance mismatch, unknown variety, unknown
  units all warn; the Data Warnings section renders when warnings exist.
- **Bad:** **Omits the Data Warnings section entirely when the count is 0**
  — on the fixture (which B finds zero warnings for) the report ends at Dry
  Goods Summary, so the §19 structure is incomplete for the canonical input.
  A, C, and D all keep the section present (rendering "No data warnings.").
  This is the one place B is less faithful than the leaders.

### Candidate C — faithful report, leaky test handles
- **Good:** 97 tests green, per-module split, full §19 structure with a
  Data Warnings section that renders "No data warnings." when empty (good
  fidelity). §24 numerics correct. Switches all work.
- **Bad:** Its OWN test suite leaks file handles — many tests do
  `open(path).read()` without a context manager, producing a wall of
  `ResourceWarning: unclosed file` during the run. Tests pass, but this is a
  hygiene/quality smell in exactly the code that is supposed to model good
  practice, and it makes the suite output noisy. Detail table mid-tier.

### Candidate D — strongest test rigor and report clarity (SELECTED)
- **Good:** 73 tests across all six §23 categories (csv_loader, parser,
  calculations, validation, report, AND a dedicated `test_cli.py`), clean
  run with **no ResourceWarnings**. The interactive contract is genuinely
  tested hermetically: a `_scripted_input` helper yields answers then raises
  `EOFError`, with explicit tests for EOF⇒defaults, invalid-then-valid
  re-prompt, and `prompt_options` driven by injected `input_fn`/`output_fn`
  (seed #6 fully honored). §24 examples are explicit, named test cases
  (13.335⇒13.34, 48.58, `Legacy Red` extra description, `"2,216.50"`⇒
  2216.50). Validation tests import named message constants
  (`AVAILABLE_GT_ON_HAND_MSG`, `NEGATIVE_VALUE_MSG`, `UNKNOWN_VARIETY_MSG`,
  …) and assert against them rather than re-typed literals (seed #7 fully
  honored); section headers are single-sourced constants (`H_DETAILED`).
  Richest executive summary (dual OnHand + Available totals, lowest-stock
  item). Data Warnings section always present. No `try/except SystemExit`.
  No hardcoded fixture totals.
- **Bad (minor):** Detail table is leaner — it shows On Hand + the
  chosen-basis quantity rather than all four of OnHand/Allocated/Pending/
  Available (defensible under §15's "where useful", but A/C are fuller).
  Surfaces two tiny balance-mismatch warnings on the fixture (766286:
  285.66 vs 285.67; 770088: 418.59 vs 418.58) — genuine §20 "material
  mismatch" detections on real fixture rounding, arguably correct but
  noisier than A/B/C which suppress sub-cent diffs. Renders large numbers
  with thousands separators (`2,216.50`) in the report — a presentation
  choice, value is correct.

### Candidate E — clean program, thin tests
- **Good:** The program is on par with the field — 23 tests green, all
  exit codes correct, full §19 structure, the nicest EOF transcript (echoes
  all six prompts with defaults). §24 core numerics (13.34, 71.84) correct.
- **Bad:** **Only three test files — no `test_validation.py`, no
  `test_report.py`** — directly under-covering two of the five §23-required
  categories (~23 tests total vs 73–100 elsewhere). Parser brittleness: it
  alone treats the `FV NV MXD CON 750ml/12p Stock for consol` row as having
  an UNPARSEABLE bottle/pack size and excludes it from 9LE, even though
  `750ml/12p` is literally present (A–D all extract 750/12 correctly from
  it). Minor: the odd row's quantity prints as `26` rather than `26.00`.

## Decision

This is a tight field where every candidate clears the acceptance bar, so
the verdict is driven by which one best proves its behavior and stays most
faithful to §19/§23. **Candidate D** wins on the dimensions the brief
weights most: it is the only candidate that hermetically tests the full
interactive contract (EOF + re-prompt via injected I/O), the only one that
turns the §24 acceptance examples into named tests, and it single-sources
its user-facing strings and asserts against the constants — honoring seed
tips #4, #6, and #7 most completely. Its report is also the clearest. Its
two demerits (leaner detail table, sub-cent balance warnings) are
presentation/policy choices, not correctness defects. A is the closest
runner-up (most faithful report) but leaves its interactive path untested;
B drops the Data Warnings section on the canonical input; C leaks file
handles in its own suite; E under-tests two required categories.

Outcome: **adopt D**.
