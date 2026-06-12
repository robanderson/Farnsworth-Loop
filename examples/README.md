# Examples

Projects built BY the Farnsworth Loop, kept as complete forensic records:
source, task briefs, anonymized candidate diffs, reviews, verdicts, run
logs, the distilled `.code-tips.md`, and an orchestrator process log. Every
decision in each example is reconstructible from the files alone.

The TUI word game is a demonstration subject only — the loop itself is
task- and domain-agnostic (PRD Section 2.3): a task is any brief with
acceptance criteria and a mechanical gate, whether that's one-shotting a
whole program, a milestone slice, or a bug fix on an existing codebase
(a Gitea/Forgejo fork, a new MCP server) whose own build/test commands
become the gate. The three recorded runs all used MILESTONE-SLICE grains
(task-001 = engine, task-002 = UI on top — sequential floors of one
build), and all three were also run as FIXED two-task pipelines — the
task list was authored before the first dispatch, which PRD Section 2.4
now forbids. The queued next design, word-garden-4, corrects both at
once: it is GOAL-DRIVEN (the goal brief is SPEC section 20's acceptance
criteria; `farnsworth done` decides after every merge whether to keep
cycling — 2 iterations or 200, emergent, never a pre-planned list) and
uses the RE-SHOT grain where useful: one-shot the entire game, distill
the field's mistakes, one-shot it again with only the lessons carried
forward — attempt 2 replaces attempt 1, and the progression note reports
the attempt-to-attempt delta, the loop's learning measurement on an
identical problem.

Each task also carries a thirty-second `summary.md` table
(`.farnsworth/task-NNN/summary.md`, the output of
`farnsworth report <task-id>`): one row per worker with its focus, gate
result, and candidate label, then the verdict. These were generated for
all recorded runs when the summary-table feature landed (2026-06-12);
the Focus column reads `-` for runs 1–2 because focus-diversified
dispatch (PRD Section 2.1) did not exist yet. Run 3 was the first live
tournament for both features.

Since 2026-06-12 each merging verdict's summary also ends with a
**progression note** (PRD Section 4.4): the reviewer's explanation of how
the adopted code advances the previously adopted baseline — what it built
on, what is new, what got better, and which distilled lessons it visibly
absorbed. The verdict reasoning says why the winner beat the round's
field; the progression note says how the project moved between tasks
(e.g. how word-garden-3's accepted task-002 build improves on its
task-001 engine). Present for word-garden-3's two tasks (recorded
retroactively in their `run.json`); earlier runs predate the feature.

| Example | What it is | Tasks | Verdicts |
|---|---|---|---|
| [`word-garden-1/`](word-garden-1/) | A friendly terminal word-guessing game (Hangman with plants) — the loop's first external project | 2 | adopt, adopt |
| [`word-garden-2/`](word-garden-2/) | The same game, rebuilt from the same spec as a controlled REPLICATION of run 1 (fresh seed, empty tips file) | 2 | adopt, adopt |
| [`word-garden-3/`](word-garden-3/) | The same game a third time — first live run of CROSS-PROJECT SEED TIPS and FOCUS-DIVERSIFIED DISPATCH | 2 | adopt, adopt |

## Word Garden — how this example was produced

The game was developed end-to-end by two Farnsworth iterations on
2026-06-11, from the spec in [`word-garden-1/SPEC.md`](word-garden-1/SPEC.md):

- **task-001 (core engine):** full 5-worker blind tournament
  (2x Haiku 4.5, 2x Sonnet 4.6, 1x Opus 4.8). Gate 5/5. Verdict: ADOPT —
  the Opus candidate. The reviewer found a real logic bug in a
  gate-passing candidate (`is_lost` missing the not-won guard) and
  distilled 21 lessons into `.code-tips.md`.
- **task-002 (UI + main loop):** triaged 3-worker tournament
  (1x Haiku, 1x Sonnet, 1x Opus), every briefing carrying the 21 lessons.
  Gate 3/3, zero correctness bugs in the field. Verdict: ADOPT — the
  SONNET candidate, beating Opus on test rigor and spec faithfulness.

Play it:

```bash
cd examples/word-garden-1
python3 -m word_garden            # emoji mode
python3 -m word_garden --ascii    # ASCII fallback
python3 -m word_garden --difficulty hard
python3 -m unittest discover -s tests   # 80 tests
```

Read the run, in order: `tasks/task-001.md` → `.farnsworth/task-001/`
(candidates, review.md, verdict.json, run.json, attribution) →
`.code-tips.md` → `tasks/task-002.md` → `.farnsworth/task-002/` →
`.farnsworth/orchestrator-log.md` (process findings) →
`.farnsworth/git-log.txt` (the project's full commit graph).

## What we observed (and fed back into the loop)

The headline: **the thesis reproduced on the first external project.**
Round 1, with no tips file, was won by the strongest model (Opus). Round 2,
with 21 distilled lessons in every briefing, was won by a cheaper model
(Sonnet) over Opus — and the field's defect rate fell from one real
gate-passing logic bug to zero. The models never got smarter; the project
did. This is the third consecutive round across two projects (loop
dogfooding tasks 001–002, Word Garden tasks 001–002) where the win moved
down the cost ladder exactly when tips entered the briefing.

Process findings, distilled from `.farnsworth/orchestrator-log.md`:

1. **Gate filters mechanics; review filters meaning — again.** All eight
   candidates across both rounds passed the mechanical gate; the semantic
   review still found a real correctness bug in one of them. The bug
   (won-at-zero-water misreported as a loss) was confirmed empirically by
   the reviewer applying the diff and probing the edge case, not by
   reading the diff.
2. **Advisory tips get ignored; contract tips get followed.** Round-1 tips
   written in contract language ("MUST", exact signatures) were universally
   absorbed in round 2. The one tip written as a preference ("prefer
   message constants...") was followed in spirit but its point (reuse the
   engine's `MSG_*` constants in the UI) was missed by all three workers.
   Refinement: the reviewer now distills lessons in imperative contract
   language.
3. **Triage cuts absolute cost but worsens reviewer dominance.** The
   3-worker round cost ~45% less in worker tokens, but review depth is
   fixed, so the reviewer's share rose from ~50% to ~68% of worker spend.
   The PRD's consolidation pass and review-depth scaling matter more under
   triage, not less.
4. **Per-task gates beat one static gate.** task-002's orchestrator added
   two cheap mechanical checks beyond `farnsworth.json` (piped-EOF exits 0;
   engine files byte-identical to base). Task-type-specific gate entries
   are a worthwhile loop extension.
5. **Capability tier shows up as economy of motion, not just quality.** In
   the 5-way round, Opus produced the winning candidate with the FEWEST
   agent tokens (~31k, 12 tool calls); a Haiku needed ~76k and 64 calls to
   reach a weaker result. "Cheap model" and "cheap attempt" are not the
   same thing — per-attempt cost data belongs in the run log.
6. **Dispatches hang, die, and duplicate — plan for it.** An infrastructure
   retry duplicated the task-001 reviewer dispatch; the duplicate stalled
   mid-review and sat as a zombie for 35+ minutes after its twin had
   already delivered the verdict. It was harmless only because the loop
   treats the *artifact* (a validating verdict.json) as the phase boundary,
   not an agent's completion claim. Refinements: per-command
   `timeout_seconds` in `farnsworth.json`, a `farnsworth clean <task-id>`
   command to sweep leftovers before re-dispatch, and a dispatch-ledger +
   liveness-check protocol for manual mode (PRD Section 4.3).
7. **Managed-sandbox findings (environment):** a nested headless
   `claude -p` cannot authenticate where credentials are host-managed file
   descriptors, so this run used manual agent dispatch (orchestrator and
   reviewer as agents, workers as parallel sub-agents pinned to worktrees)
   — the same mode that dogfooded the loop itself. And hosts that force
   `commit.gpgsign=true` globally break worker commits in scratch repos;
   seed repos and test fixtures must set `commit.gpgsign=false` locally
   (the loop's own test suite was fixed accordingly).

## Word Garden 2 — the replication run (2026-06-12)

Same spec, byte-identical task-001 brief, same fleet mix, same gate — re-run
from a fresh seed with an EMPTY tips file, to see which run-1 findings
reproduce. Full process report: [`word-garden-2/.farnsworth/orchestrator-log.md`](word-garden-2/.farnsworth/orchestrator-log.md).

| | run 1 task-001 | run 2 task-001 | run 1 task-002 (tips) | run 2 task-002 (tips) |
|---|---|---|---|---|
| Gate | 5/5 | 5/5 | 3/3 | 3/3 |
| Bugs in gate-passing field | 1 | 2 | 0 | 1 |
| Winner | Opus | **Opus** ✓ | Sonnet | **Opus** ✗ |

What replicated, and what didn't:

1. **Replicated:** empty-tips round won by the strongest model; gate
   filters mechanics while review catches real bugs in gate-passing code
   (a "flags right, message wrong" terminal-guess defect in two
   candidates); tips cut the field's defect rate (2 → 1); duplicated
   dispatches absorbed harmlessly by the artifact-boundary rule; Haiku
   spending the most motion for the weakest candidates.
2. **Did NOT replicate:** the win moving down the cost ladder once tips
   entered the briefing. Opus won both rounds. Conclusion folded into the
   PRD: the durable, twice-reproduced effect of tips is the field's defect
   FLOOR, not the winner's identity — track defects-per-round as the
   primary learning signal, and treat per-model win rates as noise until
   there are many more rounds.
3. **New finding — memory is project-scoped, mistakes are not.** Run 2's
   Haiku committed exactly the argparse defect (`try/except SystemExit`
   swallowing usage exit codes) that run 1 had already distilled into
   word-garden-1's tips — but this fresh project's memory was empty, and
   its engine round produced no CLI tips. Proposed loop extension:
   a small curated CROSS-PROJECT tips seed for round 1 of new projects.
4. **Tip-phrasing finding, level 2:** run 1 learned advisory tips get
   ignored; run 2 learned imperative tips ALSO get ignored outside their
   stated scope (the MSG_*-reuse tip didn't say "applies to tests too";
   2 of 3 workers string-matched literals in tests). Distillation rule now:
   contract language AND explicit scope.

Play it: identical commands to word-garden-1, from `examples/word-garden-2`.

## Word Garden 3 — the extensions run (2026-06-12)

Same spec and byte-identical task briefs again, but this run flipped ON
the two loop extensions the first two runs queued up, both live for the
first time:

1. **Cross-project seed tips.** The fresh project's `.code-tips.md`
   started not empty but with 9 curated DOMAIN-GENERAL entries from the
   prior runs' reviewer distillations (terminal-message contract,
   assert-the-positive, forced-scenario e2e, argparse exit codes, no
   silent fallbacks, injectable I/O/rng, message constants, direct
   fixtures, hygiene) — each keeping its original provenance.
2. **Focus-diversified dispatch (PRD §2.1).** Every worker carried a
   one-line focus directive (recorded in `farnsworth.json` and the run
   logs, disclosed to the reviewer only as a sorted unattributed set,
   unsealed post-verdict).

Full process report: [`word-garden-3/.farnsworth/orchestrator-log.md`](word-garden-3/.farnsworth/orchestrator-log.md).

| | run 2 t-001 (empty tips) | run 3 t-001 (9 seed tips) | run 2 t-002 (proj. tips) | run 3 t-002 (seed+proj.) |
|---|---|---|---|---|
| Gate | 5/5 | 5/5 | 3/3 | 3/3 |
| Behavioral bugs in field | 2 | 1 | 1 | **0** |
| Winner | Opus | **Sonnet** | Opus | Opus |

What the run showed:

1. **The seed worked, attributably, on both of its target classes.** The
   defect classes the seed covered did not occur: no terminal-message
   bugs, no flag-only suites (round 1), and no argparse `SystemExit`
   swallow (round 2) — the latter having shipped in BOTH prior projects'
   UI rounds. The reviewer's per-entry audit: 0 of 9 seed entries
   violated in round 1.
2. **The one behavioral bug that DID ship maps exactly to the seed's
   scope boundary.** A round-1 candidate reproduced word-garden-1's
   `is_lost` missing-win-guard defect — the lesson that existed only in
   that OTHER project's project-scoped tips and was excluded from the
   seed by the domain-general curation rule. Memory prevents precisely
   the defects it covers; nothing more. Refinement queued: the reviewer
   should GENERALIZE while distilling (the general form — "a standalone
   predicate must not rely on a caller's check ordering" — belongs in
   the seed pile, the specific form in project tips).
3. **Foci force divergence without corrupting verdicts.** Test counts
   ranged 36–84 (round 1) and 105–145 (round 2); candidates invested
   visibly along their lenses. No focus was misread as a contract
   amendment — and focus alignment did not buy wins: round 2's
   accessibility-focused candidate had the best accessibility work and
   still lost on a self-inflicted signature deviation.
4. **A new anonymization leak class, found and plugged.** A naive `git
   clone` for the reviewer environment carries worker-named branches
   (`task-001-w1`...), de-anonymizing the field by id. The reviewer
   environment must be CONSTRUCTED: base tree + labeled diffs + gate
   notes, nothing else.
5. **Required signatures need closed-contract language.** A good-faith
   extra parameter (`new_game_fn`) on the brief's required `main()`
   signature forfeited round 2 for an otherwise excellent candidate.
   Briefs and tips now state: required signatures are exact and CLOSED;
   improvements go to escalation, not the diff.
6. **Repeat signatures, third confirmation each:** duplicate dispatches
   in every background phase (absorbed by the artifact-boundary rule,
   including a duplicated reviewer); identical file footprints across all
   candidates (the M4 divergence metric must read content, not file
   lists); a Haiku spending the most motion in the field for a
   non-winning candidate (3 runs for 3).

Play it: identical commands to word-garden-1, from `examples/word-garden-3`.

## Reproducing with the CLI

`word-garden-1/farnsworth.json` records the exact fleet this run emulated.
On a machine with an authenticated `claude` binary:

```bash
git init my-word-garden && cd my-word-garden
git config commit.gpgsign false   # if your host forces signing
# copy in SPEC.md, farnsworth.json, .gitignore, tasks/ from this example
git add -A && git commit -m "seed"
PYTHONPATH=/path/to/Farnsworth-Loop python3 -m farnsworth run tasks/task-001.md
```

Then review the verdict, merge the winning branch, let the reviewer
distill `.code-tips.md`, and dispatch task-002 the same way.
