# Run summary -- task-002

Base commit `65af635`, 2026-06-11T21:55:00Z -> 2026-06-11T22:25:00Z.

| Worker | Focus | Exit | Gate | Candidate | Result |
|---|---|---:|---|---|---|
| w1 | - | 0 | PASS | B |  |
| w2 | - | 0 | PASS | C | ADOPTED |
| w3 | - | 0 | PASS | D |  |
| w4 | - | 0 | PASS | A |  |
| w5 | - | 0 | PASS | E |  |

**Verdict:** adopt candidate C

**Reasoning:** Candidate C most contract-faithful: exact run.json (no extra keys), strict back-compat, correct anonymized autopsy path, complete verdict validation, clean extension of M1. See review.md.
