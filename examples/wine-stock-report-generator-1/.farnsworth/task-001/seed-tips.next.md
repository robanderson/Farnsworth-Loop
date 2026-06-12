# Seed-tip candidates (domain-general) — distilled in task-001

These are the GENERAL forms of project lessons that would pay rent in ANY
project, routed by the orchestrator into the cross-project seed pile. The
project-specific instantiations stay in code-tips.next.md.

A. A structured-output generator (report, document, serialized payload)
   MUST render its UNCONDITIONAL sections regardless of whether their
   content is empty — an empty section renders with an explicit
   empty-state marker ("No data warnings.", "(none)"), it is NOT omitted.
   Omitting a section when its collection is empty makes the output's shape
   depend on the input, which breaks any consumer (or golden test) that
   relies on a stable structure. Only TRULY conditional sections (gated by
   an explicit option/flag) may be absent. Applies to source; output tests
   MUST assert the unconditional sections appear on an input that yields
   zero items for them. [2026-06-12, seed; generalized from wine-stock
   task-001: a candidate dropped the Data Warnings section on the canonical
   fixture because it had zero warnings.]

B. A TOLERANT parser over messy real-world records MUST keep a partially
   unparseable record in the output, mark the unknown fields
   (blank/`Unknown`/`—`), and emit a warning naming the record — never drop
   it and never crash on one odd record. The symmetric obligation is to not
   OVER-reject: a record with a parseable core plus a trailing free-text
   tail is parseable; extract the core and keep the tail as an extra field
   rather than declaring the whole record unparseable. Records excluded from
   a derived AGGREGATE because one field is unknown MUST still be excluded
   ONLY from the aggregate that depends on that field, and still counted in
   aggregates that do not. Prefer token-based parsing over a brittle
   whole-string regex. Applies to source; parser tests MUST cover both the
   genuinely-unparseable record AND the parseable-core-with-tail record.
   [2026-06-12, seed; generalized from wine-stock task-001: one candidate
   wrongly marked `... 750ml/12p Stock for consol` as having an unparseable
   size, excluding it from 9LE though the size was present.]

C. When a function is injected purely so it can be tested hermetically
   (an `input_fn`/`output_fn`/clock/rng seam), the test suite MUST actually
   DRIVE it through that seam and assert the behavior — importing the
   function and never calling it leaves the most contract-heavy surface
   unproven while looking covered. For an interactive/prompt seam this means
   scripting inputs (including an end-of-stream that raises `EOFError`) and
   asserting default-acceptance, end-of-stream-accepts-all-remaining, and
   re-prompt-on-invalid. This sharpens seed tip 6: providing the injection
   point is not the same as exercising it. Applies to tests. [2026-06-12,
   seed; generalized from wine-stock task-001: an otherwise-faithful
   candidate imported its prompt function but never invoked it in tests.]
