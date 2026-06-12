# Examples

Projects built BY the Farnsworth Loop, kept as complete forensic records:
source, task briefs, anonymized candidate diffs, reviews, verdicts, run
logs, the distilled `.code-tips.md`, and an orchestrator process log. Every
decision in each example is reconstructible from the files alone.

| Example | What it is | Tasks | Verdicts |
|---|---|---|---|
| [`word-garden/`](word-garden/) | A friendly terminal word-guessing game (Hangman with plants) — the loop's first external project | 2 | adopt, adopt |

## Word Garden — how this example was produced

The game was developed end-to-end by two Farnsworth iterations on
2026-06-11, from the spec in [`word-garden/SPEC.md`](word-garden/SPEC.md):

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
cd examples/word-garden
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

## Reproducing with the CLI

`word-garden/farnsworth.json` records the exact fleet this run emulated.
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
