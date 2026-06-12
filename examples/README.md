# Examples

Projects built BY the Farnsworth Loop, kept as complete forensic records:
source, task briefs, anonymized candidate diffs, reviews, verdicts, run
logs, the distilled `.code-tips.md`, and an orchestrator process log. Every
decision in each example is reconstructible from the files alone.

Each task also carries a thirty-second `summary.md` table
(`.farnsworth/task-NNN/summary.md`, the output of
`farnsworth report <task-id>`): one row per worker with its focus, gate
result, and candidate label, then the verdict. These were generated for
runs 1–2 retroactively when the summary-table feature landed (2026-06-12;
their Focus column reads `-` because focus-diversified dispatch, PRD
Section 2.1, did not exist yet). Word Garden 4 is the first run where both
features ran live.

| Example | What it is | Tasks | Verdicts |
|---|---|---|---|
| [`word-garden-1/`](word-garden-1/) | A friendly terminal word-guessing game (Hangman with plants) — the loop's first external project | 2 | adopt, adopt |
| [`word-garden-2/`](word-garden-2/) | The same game, rebuilt from the same spec as a controlled REPLICATION of run 1 (fresh seed, empty tips file) | 2 | adopt, adopt |
| [`word-garden-4/`](word-garden-4/) | The same game again — the first run driven by the LIVE `farnsworth` CLI, with focus-diversified dispatch and a cross-project tips seed | 2 | adopt, adopt |

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

## Word Garden 4 — the first live CLI run (2026-06-12)

Same spec, byte-identical task-001 brief, same fleet mix and gate — but
this time the tournament was driven by the actual tool
(`python3 -m farnsworth run`), because this host's subscription OAuth lets
nested headless `claude -p` authenticate. Two more loop features had their
first live outing: focus-diversified dispatch (each worker carried a
distinct one-line focus) and a cross-project tips seed (13 domain-general
lessons curated from word-garden-1/-2 into round-1 `.code-tips.md`).
Full process report:
[`word-garden-4/.farnsworth/orchestrator-log.md`](word-garden-4/.farnsworth/orchestrator-log.md).

| | task-001 (5 workers, seed tips) | task-002 (3 workers, seed + t1 tips) |
|---|---|---|
| Gate | 5/5 | 3/3 (one vacuous — see below) |
| Bugs in gate-passing field | 2 | 1 (+1 non-submission) |
| Winner | **Sonnet 4.6** (readability focus) | **Opus 4.8** (spec-faithfulness focus) |
| Worker / reviewer cost | $3.03 / $3.61 (119%) | $3.60 / $3.40 (94%) |
| Wall clock | 13.5 min | 17 min |

What the run added:

1. **The recorded fleet config was never runnable.** Pre-flight canaries
   found two 100%-fatal bugs before dispatch: `--bare` never reads
   OAuth/keychain (every worker would have died "Not logged in" — replaced
   with `--setting-sources ""`), and headless `acceptEdits` denies ALL
   Bash (workers could not test or commit — fixed with scoped
   `--allowedTools`). A dispatch config is a runtime contract; it needs a
   mechanical pre-flight before a tournament burns real money.
2. **The cross-project seed prevented the mechanical defect class but not
   the semantic one.** Run 2's argparse `SystemExit` bug did NOT recur
   (seed bans it verbatim); the terminal-message defect DID recur, twice,
   same tier as run 2 — the general "assert the full outcome" tip can't
   substitute for the project-specific status-message contract. Seeds
   transfer API-shaped rules, not state-contract rules; both directions of
   run 2's "memory is project-scoped" finding now have evidence.
3. **Tier dominates focus.** Foci visibly shaped style, and the two
   adopted candidates came from differently-focused workers — but the
   TEST-RIGOR-focused Haiku still shipped the flag-only-assertion defect,
   and a Haiku reproduced a vacuous-test pattern the seed forbids
   verbatim. A focus is a lens, not a capability upgrade.
4. **The loop's first self-caught implementation bug.** A Sonnet did all
   of task-002 but never committed; the gate (which runs in the worktree)
   passed it while its candidate diff (`base..HEAD`) was empty — the
   briefing then vouched to the reviewer for a 0-line candidate. The
   reviewer's empirical probe caught it ("non-submission") and the field
   was judged on merits, but the mechanical layer had violated PRD 4.3's
   artifact rule. Fixed in the CLI with tests (no-commit workers fail the
   gate with autopsy "no commits on branch"; their uncommitted work is
   archived; empty diffs can't take a label), alongside a second live bug
   (`farnsworth clean` run from inside a worktree targeted the wrong
   repo).
5. **Reviewer cost crossed 100% of worker spend** in the 5-way round.
   Dollar-true accounting (the JSON output's `total_cost_usd`) makes the
   economics unambiguous: empirical review is now the dominant line item;
   depth should scale with field disagreement, not field size. Whole
   project: ~$13.6, ~45 minutes.

Play it: identical commands to word-garden-1, from `examples/word-garden-4`.

## Reproducing with the CLI

Word Garden 4 IS the CLI reproduction — start from
`word-garden-4/farnsworth.json`, which is the first fleet config proven to
run live. (The configs recorded with runs 1–2 carry `--bare`, which never
reads OAuth/keychain and so cannot authenticate on subscription hosts, and
they lack the `--allowedTools` grants headless workers need to test and
commit. Word Garden 4's pre-flight found both.) On a machine with an
authenticated `claude` binary:

```bash
git init my-word-garden && cd my-word-garden
git config commit.gpgsign false   # if your host forces signing
# copy in SPEC.md, .gitignore, tasks/ from this example, and
# farnsworth.json + farnsworth-002.json from word-garden-4/
git add -A && git commit -m "seed"
# pre-flight: one cheap canary proving auth + edit + test + commit
claude -p "create canary.txt, run python3 -c 'print(1)', git commit it; report what was denied" \
  --setting-sources "" --model claude-haiku-4-5 --permission-mode acceptEdits \
  --allowedTools "Bash(python3:*)" "Bash(git:*)"
PYTHONPATH=/path/to/Farnsworth-Loop python3 -m farnsworth run tasks/task-001.md
```

Then review the verdict, merge the winning branch (the reviewer has
already distilled `.code-tips.md` as part of its protocol), sweep with
`farnsworth clean task-001`, and dispatch task-002 the same way with
`--config farnsworth-002.json`.
