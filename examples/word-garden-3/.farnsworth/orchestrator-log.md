# Orchestrator Log — Word Garden 3

Third Word Garden run (2026-06-12) and the first LIVE trial of two queued
loop extensions at once:

1. **Cross-project seed tips** (proposed after word-garden-2): 9 curated
   domain-general entries from prior projects' reviewer distillations,
   injected into `.code-tips.md` BEFORE round 1 of this fresh project.
   Hypothesis under test: the empty-tips defect classes observed twice
   before (terminal-message-not-overwritten, silent pool fallback,
   flag-only tests) do not reappear in the round-1 field.
2. **Focus-diversified dispatch** (PRD §2.1, shipped 2026-06-12, never
   live-run): each worker carries a one-line focus directive recorded in
   `farnsworth.json`, appended to its briefing with the precedence
   sentence; disclosed to the reviewer only as a sorted, unattributed set;
   unsealed post-verdict.

Confound, acknowledged up front: vs the word-garden-2 baseline this run
changes TWO variables (seed tips + foci). Mitigation: defect attribution
is done at the defect-CLASS level (each defect found or absent is checked
against whether a specific seed tip addressed it), and focus efficacy is
judged by field divergence, not by defect count.

Dispatch mode: MANUAL AGENT DISPATCH (orchestrator and reviewer as agents,
workers as parallel sub-agents pinned to git worktrees), same as all prior
runs, same reason — nested headless `claude -p` cannot authenticate in
this managed sandbox. `farnsworth.json` records the emulated fleet.

---

## task-001 — Core engine (2026-06-12)

**Setup.** Full 5-worker fleet: 2x Haiku 4.5, 2x Sonnet 4.6, 1x Opus 4.8,
blind, parallel, one worktree each, base commit `6cfef01`. Brief
byte-identical to runs 1–2. Tips: the 9-entry cross-project seed. Foci:
test-rigor (w1/haiku), simplicity (w2/haiku), readability (w3/sonnet),
defensive-robustness (w4/sonnet), API-ergonomics (w5/opus).

**Dispatch observations.**
- The duplicate-dispatch signature reproduced for the third run in a row,
  and at higher rate: four of five workers ran as background agents, and
  w3, w4, w5 each reported finding the implementation "already present as
  untracked scaffolding" in their worktree — an infrastructure retry
  re-entering the same worktree before the recorded agent's pass. Two of
  them (w3, w4) consequently described their own contribution as "writing
  the missing tests". The artifact-boundary rule absorbed all of it:
  committed branches face the gate; agent narratives are ignored.
- Blindness verified mechanically post-hoc: all ten pairwise tree diffs
  between worker branches are large (1.4k–2k lines); no two candidates
  share files. The "already present" files were each worker's own
  duplicate, not cross-contamination.

**Gate.** 5/5 first-pass (third run in a row at saturation — on tasks this
size the gate is a hygiene check, not a discriminator). Hygiene: zero
violations — no bytecode, no forbidden-file edits, no `.code-tips.md`
writes, all work committed. Test counts: 84 (w1), 47 (w2), 58 (w3),
80 (w4), 36 (w5).

**Divergence measurement note (for M4).** File footprints were IDENTICAL
across all five candidates — the same weak signal as both prior runs —
while pairwise content divergence was high. When the brief pins the
package layout (as good briefs do), footprint comparison measures the
brief, not the field. M4's divergence metric needs content-level signals
(API surface, test-case sets, control-flow shape), not file lists. The
foci demonstrably forced content apart (test counts alone range 36–84),
which is what they were designed to do; footprint just can't see it.

**Anonymization.** Labels shuffled (A=w2, B=w5, C=w1, D=w4, E=w3 — sealed
until post-verdict), diffs archived under
`.farnsworth/task-001/candidates/`, reviewer given a stripped clone (no
worker-named refs — a NEW leak class found and plugged this run: a naive
`git clone` of the project hands the reviewer `task-001-w*` branch names,
which de-anonymize candidates by id; the reviewer environment must carry
the base tree and the labeled diffs ONLY).

**Review.** Dispatched to Opus 4.8 with blind-sketch-first protocol and an
explicit seed-tip audit requirement (per-entry: did the field honor it).
The duplicate-dispatch signature hit the REVIEWER too (as in run 1): the
recorded reviewer found a blind sketch and probe harness "already present"
from its own duplicated dispatch, verified them against its independent
reasoning, and proceeded. Artifact boundary absorbed it again.

**Verdict.** ADOPT D -> unsealed to w4 (SONNET 4.6, defensive-robustness
focus). The reviewer's 31-assertion empirical probe found ONE real defect
in the gate-passing field: candidate A (w2, Haiku, simplicity focus) ships
`is_lost` without the `not is_won` guard — won-at-zero-water reports won
AND lost simultaneously. Masked in `apply_guess` (win checked first) and
by a suite that never calls `is_lost` on a won state. This is the EXACT
defect class word-garden-1's round 1 produced and distilled — a lesson
that lived in that project's PROJECT-SCOPED tips and was deliberately NOT
in the domain-general seed.

**Seed-tip audit (the experiment's key data).** 0 of 9 seed entries
violated; 7 universally honored; 1 partially (every candidate raises on
the empty pool in source, but no suite forces the branch); 1 N/A until
task-002 (argparse). Both prior empty-tips runs shipped terminal-message
defects and flag-only suites; with the seed in the briefing, those classes
were absent from all five candidates.

**Interpretation.** Cleanest evidence yet that memory scope is the binding
constraint, in BOTH directions: (a) seeding domain-general lessons
suppressed the domain-general defect classes (defects-per-round: 2, 2, 1
across the three runs' engine rounds — and this round's single defect is
the only one NOT covered by a seed entry); (b) the defect that DID appear
is precisely the one whose lesson existed but was scoped to another
project. The proposed M3 cross-project seed works; its curation rule
("domain-general only") correctly predicted both what it would and
wouldn't prevent. Note the wrinkle for the seed's curation policy: the
is_lost lesson LOOKS project-specific but is actually an instance of a
general class ("a standalone predicate must not depend on a caller's
check ordering") — generalizing lessons at distillation time is the
skill to push on.

**Focus observations (first live trial of PRD 2.1).** Foci demonstrably
shaped the field: the test-rigor Haiku shipped 84 tests, the simplicity
Haiku 47 (and the round's only defect — economy bought at the predicate's
expense), the defensive-robustness Sonnet won with the suite that
explicitly tested the precedence case the defective candidate missed, the
API-ergonomics Opus produced the leanest, best-factored candidate (rich
__init__ re-exports, a words_for helper) with the fewest tests (36). The
winning focus was the one aligned with the task's dominant risk (contract
violations). No focus was misread as a contract amendment; no candidate
deviated from the brief. Anonymization held: foci disclosed to the
reviewer only as a sorted unattributed set.

**Cost.** Workers ~262k agent tokens (w1 75k/54 calls, w2 38k/28, w3
46k/31, w4 49k/33, w5 53k/29); reviewer ~149k (~57% of worker spend).
Reviewer share consistent with run 2's ~54-55% under a heavy-worker
5-field; the probe-harness depth (31 assertions, applied 5x) is where
review spend goes.

**Distilled.** 14 project-scoped entries added to the seed (engine API as
a frozen contract for task-002, is_lost win-precedence, terminal-message
rule re-confirmed project-locally, immutable-vs-mutating apply_guess tests
must match the implementation, force-the-empty-pool-branch testing,
full-string message assertions against imported constants).

---

## task-002 — UI, main loop, packaging (2026-06-12)

**Setup.** TRIAGED fleet (routine, well-specified UI task on a frozen
engine contract): 1x Haiku, 1x Sonnet, 1x Opus, base `d848286`. Every
briefing carries the 9 seed + 14 project entries. Foci: test-rigor
(w1/haiku), accessibility-and-display-faithfulness (w2/sonnet),
readability (w3/opus). Gate: unittest + compileall + run-1's two per-task
extensions (piped-EOF exits 0; engine files byte-identical to base).

**Gate.** 3/3 first-pass, extensions included. Duplicate-dispatch
signature again in all three background workers ("already present"
scaffolding); pairwise tree diffs large; blindness held.

**Verdict.** ADOPT A -> unsealed to w3 (OPUS 4.8, readability focus). The
reviewer exercised all three candidates empirically (full win/loss runs,
whole-game ASCII, argparse exit codes, growth stages) and found ZERO
behavioral bugs — both prior runs' UI rounds shipped one. Two defects
found are CONTRACT-level: B (sonnet, accessibility focus) extended the
brief's required `main()` signature with a `new_game_fn` parameter its own
tests depend on (disqualifying: an injection path without a signature
change existed); C (haiku, test-rigor focus) violated the
message-constants rule in source and tests — the exact rot pattern two
prior rounds distilled against, still recurring at the cheapest tier
despite imperative, scoped phrasing.

**Seed result, part 2.** The argparse seed entry — N/A in round 1 — became
applicable and was honored by all three candidates. The
`try/except SystemExit` defect shipped in BOTH prior projects' UI rounds;
with the seed in the briefing it did not occur. This is the
cross-project-seed hypothesis confirming on its second, independent
defect class.

**Focus observations.** The focus-aligned candidate did NOT win this time:
the accessibility-focused Sonnet had genuinely the strongest accessibility
assertions but lost on a self-inflicted contract deviation; readability
Opus won on overall faithfulness. Two rounds in: foci reliably shape
WHERE candidates invest (test counts, assertion styles, helper structure),
and the reviewer's verdict stays anchored to the acceptance criteria —
the precedence sentence is doing its job in both directions.

**Cost.** Workers ~226k agent tokens (haiku 93k/73 calls — again the most
motion in the field, sonnet 66k/56, opus 67k/34); reviewer ~125k (~55% of
worker spend — matches run 2's heavy-worker pattern, not run 1's 68%
triage spike).

**Distilled.** UI/CLI entries added; two existing entries SHARPENED:
required signatures are CLOSED contracts (extending them is a deviation,
not a discretionary extension), and the constants rule now names its own
enforcement test (assert imported constants by full-string equality).

---

## Cumulative metrics (after 2 merged tasks)

| Metric                      | task-001 (9 seed tips) | task-002 (seed + 14) |
|-----------------------------|------------------------|----------------------|
| Fleet                       | 5 (2H/2S/1O)           | 3 (1H/1S/1O) triaged |
| First-pass gate rate        | 5/5                    | 3/3                  |
| Behavioral bugs in field    | 1 (gate-passing)       | 0                    |
| Contract-level defects      | 0                      | 2                    |
| Verdict                     | adopt                  | adopt                |
| Winning model               | Sonnet 4.6             | Opus 4.8             |
| Winning focus               | defensive robustness   | readability          |
| Worker agent tokens         | ~262k                  | ~226k                |
| Reviewer agent tokens       | ~149k (57%)            | ~125k (55%)          |
| Round 2 triggered           | no                     | no                   |

Verdict distribution: adopt 2 / synthesize 0 / escalate 0.
Win rate by model this run: Sonnet 1, Opus 1, Haiku 0.

## What this run changes about the loop

1. **Cross-project seed tips: validated; promote to a first-class M3
   deliverable.** Across the three runs' engine rounds, behavioral
   defects-per-round went 1, 2, 1 — but defect ATTRIBUTION is the real
   result: in this run, every defect class covered by a seed entry was
   absent (terminal-message, flag-only suites in round 1; argparse in
   round 2, where both prior projects had shipped it), and the one
   behavioral defect that DID appear (`is_lost` guard) was exactly the
   lesson sitting in another project's project-scoped tips, excluded from
   the seed by the domain-general curation rule. Memory works precisely
   where it exists, and its scope boundary is visible in the defect data
   from both sides.
2. **Distillation should GENERALIZE while it distills.** The `is_lost`
   miss shows the curation rule needs one more step: when a project lesson
   is an instance of a general class ("a standalone predicate must not
   rely on a caller's check ordering"), the reviewer should write the
   general form into the seed candidate pile, not just the project form
   into project tips. Queued for M3 alongside the seed itself.
3. **Focus-diversified dispatch: works as designed, with the predicted
   trade-off.** Foci forced measurable field divergence (test counts
   36–145 across rounds; clearly differentiated investment per candidate)
   without a single contract amendment misread. But the round-1 defect
   sat in the simplicity-focused candidate — diversity searches more of
   the space INCLUDING its failure modes; the tournament's whole premise
   is that the review absorbs that.
4. **Footprint divergence measurement is officially inadequate.** Three
   runs, every footprint identical, even under deliberate diversification
   — because good briefs pin the layout. M4's divergence metric must read
   content (API surface, assertion styles, test-case sets), or the
   round-2 trigger will never fire on well-briefed tasks.
5. **Anonymization has an environment-shaped leak class.** A naive clone
   for the reviewer carries worker-named branches (`task-001-w1`...). The
   reviewer environment must be constructed: base tree + labeled diffs +
   gate notes, nothing else. Plugged this run; belongs in the CLI's
   review-dispatch code and the PRD risk table.
6. **Required signatures need closed-contract language in briefs.** B's
   `new_game_fn` was a good-faith engineering improvement that still
   forfeited the round. Briefs (and tips) should say explicitly: required
   signatures are exact and closed; extensions belong in an escalation or
   a follow-up task proposal, not in the diff.
7. **Haiku's economy-of-motion pattern is now 3-for-3.** In every round
   with a Haiku in the field, a Haiku spent the most tokens/tool-calls
   for a non-winning candidate. Worth a standing line in the routing
   guidance: cheap per token is not cheap per attempt.
