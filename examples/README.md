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
become the gate. The first three recorded runs all used MILESTONE-SLICE
grains (task-001 = engine, task-002 = UI on top — sequential floors of
one build), and all three were also run as FIXED two-task pipelines —
the task list was authored before the first dispatch, which PRD Section
2.4 now forbids (a run-4 orchestrator session repeated exactly that
mistake and is preserved only as the PRD's cautionary example).
word-garden-5 is the corrected design, executed: GOAL-DRIVEN (the goal
brief plus `farnsworth done` checks decide after every merge whether to
keep cycling — iteration count emergent, never a pre-planned list) with
the WHOLE-PROGRAM grain (one-shot the entire game; had the goal not
been met, the next gap-derived task could have been the RE-SHOT —
attempt 2 replacing attempt 1 with only distilled lessons carried
forward). The goal was met in one iteration, which is itself the
honest pricing of the re-shot: it only triggers when attempt 1 leaves
a gap.

Each task also carries a thirty-second `summary.md` table
(`.farnsworth/task-NNN/summary.md`, the output of
`farnsworth report <task-id>`): one row per worker with its focus, gate
result, and candidate label, then the verdict. These were generated for
all recorded runs when the summary-table feature landed (2026-06-12);
the Focus column reads `-` for runs 1–2 because focus-diversified
dispatch (PRD Section 2.1) did not exist yet. Run 3 was the first live
tournament for both features; run 4 replicated them the same day from a
parallel session.

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
| [`word-garden-4/`](word-garden-4/) | The same game again — the only run dispatched end-to-end by the LIVE `farnsworth` CLI (real `claude -p` workers + reviewer), replicating the seed + foci extensions | 2 | adopt, adopt |
| [`word-garden-5/`](word-garden-5/) | The same game, GOAL-DRIVEN: whole-program grain, seed v2 (generalized lessons), constructed review env — goal met in 1 iteration | 1 | adopt |

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

## Word Garden 4 — the CLI-dispatched run (2026-06-12)

Same spec, byte-identical task-001 brief, same fleet mix and gate — and
the only run so far dispatched end to end by the actual tool: every worker
and the reviewer ran as real `claude -p` subprocesses under
`python3 -m farnsworth run`, on subscription OAuth that held for the whole
run (run 5 later saw it turn intermittent). Run 4 came out of a session
parallel to run 3's and independently exercised the same two extensions —
focus-diversified dispatch and a cross-project tips seed (its own
13-entry curation from word-garden-1/-2) — so its findings double as a
same-day replication of run 3's. Full process report:
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

## Word Garden 5 — the goal-driven run (2026-06-12)

Same SPEC, but a different shape of run: the first project under the
PRD Section 2.4 termination contract. `GOAL.md` + six `goal.done`
checks were seeded alongside the spec; the orchestrator derived ONE
task from the goal gap (the entire game, whole-program grain), and
after the merge `farnsworth done` plus a reviewer goal-attestation
decided the exit. Exit: DONE at 1 iteration. Three other firsts: the
cross-project seed shipped as v2 (10 entries, including the GENERALIZED
predicate lesson queued by run 3 — the "generalize while distilling"
rule's first product); the reviewer ran in the CLI's new CONSTRUCTED
review environment (base tree + labeled diffs + gate notes, nothing
else); and the per-task gate extensions from runs 1–3 (piped-EOF,
help/usage exit codes) ran as first-class gate config. Full process
report: [`word-garden-5/.farnsworth/orchestrator-log.md`](word-garden-5/.farnsworth/orchestrator-log.md).

| | run 3 t-001 (9 seed tips) | run 5 t-001 (10 seed tips, whole game) |
|---|---|---|
| Gate | 5/5 | 5/5 (six checks) |
| Engine-behavior bugs in field | 1 | **0** |
| Spec-deviation defects in field | 0 | 3 (ASCII stage collapse) |
| Winner | Sonnet | **Sonnet** (readability) |
| Iterations (emergent) | n/a (fixed pipeline) | **1** (goal-driven) |

What the run showed:

1. **Seed v2 closed the predicate hole.** The generalized tip-10 entry
   was honored by all five candidates — every `is_lost` carries its own
   not-won guard, directly tested. The defect class that shipped in
   both prior empty-or-narrower-seed engine rounds did not appear.
   Generalizing at distillation time widens memory's scope for free.
2. **The gate's blind spot, new exemplar.** Three of five candidates
   passed the `plays-ascii` gate (exit 0, pure ASCII) while collapsing
   SPEC 10's five growth stages to 1–4 distinct glyphs. Mechanical
   checks verify exit codes and character sets; DISTINCTNESS — meaning
   — needed the reviewer. Distilled as tips 11–15.
3. **Goal-driven cycling stops honestly.** One iteration, because the
   attestation found no residual gap. No pre-planned second task, no
   forced re-shot — the run-4 failure mode is structurally absent.
4. **Constructed review env worked on first live use** — and live use
   immediately caught a briefing-path bug the fake-reviewer smoke test
   couldn't (the briefed diff path didn't match where the env serves
   the diffs). Lesson for the loop's own tests: a fake reviewer that
   globs instead of following the briefing text validates plumbing,
   not the contract.
5. **Reviewer economics, two new data points.** Tournament review fell
   to ~39% of worker spend (lowest recorded — pre-labeled diffs in a
   ready-made env reduce review overhead), but the goal contract adds
   a per-goal attestation dispatch (~68k tokens here) that the
   economics must now name.
6. **Repeat signatures.** Identical file footprints even at
   whole-program grain (4th run; M4's metric must read content);
   Haiku-most-motion (4th run); focus-alignment ≠ advantage (the
   accessibility-focused candidate had the worst ASCII display);
   duplicate dispatches absorbed by the artifact boundary — this time
   in the attestation phase, a NEW artifact type, which is the rule
   working generically.

Play it: identical commands to word-garden-1, from `examples/word-garden-5`.
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
cp /path/to/Farnsworth-Loop/seed-tips.md .code-tips.md   # cross-project seed (M3)
git add -A && git commit -m "seed"
# pre-flight: one cheap canary proving auth + edit + test + commit
claude -p "create canary.txt, run python3 -c 'print(1)', git commit it; report what was denied" \
  --setting-sources "" --model claude-haiku-4-5 --permission-mode acceptEdits \
  --allowedTools "Bash(python3:*)" "Bash(git:*)"
PYTHONPATH=/path/to/Farnsworth-Loop python3 -m farnsworth run tasks/task-001.md
```

For a goal-driven run (the word-garden-5 shape), also copy in `GOAL.md`
and a `goal` block in `farnsworth.json`, then after every merge let
`PYTHONPATH=... python3 -m farnsworth done` decide whether to derive the
next task or stop.

Then review the verdict, merge the winning branch, install the reviewer's
`code-tips.next.md` as `.code-tips.md`, sweep with
`farnsworth clean task-001`, and dispatch task-002 the same way
(word-garden-4 used a per-task `--config farnsworth-002.json` for its
triaged round).

Since 2026-06-12 there is a cheaper path for Anthropic-model fleets:
**delegate dispatch** (PRD Section 4.1b) — worker entries carry `model`
instead of `command`, `farnsworth run` prepares worktrees and briefing
files and exits 3, the orchestrating Claude Code session spawns one
subagent per briefing (billed to the subscription, not API credit), then
`farnsworth gate <task-id>` and `farnsworth finalize <task-id>` complete
the round. The recorded word-garden configs predate this and keep the
subprocess form.
