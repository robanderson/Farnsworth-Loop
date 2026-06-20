# FL-38 attempt notes

Surface a run-purpose summary in the live /workflows heading via the only runtime lever available — an early `log()` narrator line (the static `meta` is a PURE LITERAL per the Workflow spec and cannot be made dynamic).

- Added `deriveSummary()` in `workflows/tournament.mjs`: `args.title` (alias `args.purpose`) wins verbatim; otherwise it sanitizes `args.task` — strips `@@FL`-style sigils (`/@@FL(:\d+){0,3}/`), flattens newlines, collapses whitespace, and truncates to ~80 chars with a `…` ellipsis.
- Emitted ONCE as the very first `log()` (`▶ <summary>`), right after `phase('Round 1')` and before `buildContext()`.
- Shortened the static `meta.description` so it no longer truncates mid-sentence in the live display.
- No change to mapping/ranking/return value or control flow; `deriveSummary` is pure and only adds one early log line.

Tradeoffs / limitations: sigil regex is anchored to the documented `@@FL[:N][:M[:Z]]` form (won't catch hypothetical future sigil variants); truncation uses a unicode `…` (single char, fine in markdown render but not ASCII); a missing task with no title yields the literal `(untitled run)`.
