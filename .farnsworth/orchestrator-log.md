# Orchestrator Log

The running record of dogfooded Farnsworth Loop iterations: each entry is
written by the orchestrator after MERGE, summarizing what the loop did and
what we learned about the loop itself. Per-task forensics (briefs, candidate
diffs, anonymized reviews, verdicts, run logs, attribution) live in
`.farnsworth/task-NNN/`; durable engineering lessons live in `.code-tips.md`.
This file is for findings about the PROCESS.

---

## task-001 — M1 Skeleton (2026-06-11)

**Setup.** First iteration, run manually: the orchestrator and reviewer were
Claude agents driving git/worktrees by hand, since the tool being built did
not exist yet. Fleet per PRD section 3: 2x Haiku 4.5, 2x Sonnet 4.6,
1x Opus 4.8, blind, parallel, one isolated worktree each. `.code-tips.md`
was empty (seed headers only).

**Gate.** 5/5 first-pass (tests + compileall).

**Verdict.** ADOPT A -> unsealed to the Opus worker. Both Haiku candidates
were disqualified in review despite passing the mechanical gate: they
committed `__pycache__/*.pyc` and the seed `.code-tips.md`, and deviated
from the briefing-composition contract. Sonnets were adequate runners-up
(CWD-anchored worktrees instead of git toplevel; deprecated `utcnow()`).

**Findings.**
1. The mechanical gate is necessary but nowhere near sufficient: all five
   passed it, yet only one candidate was contract-faithful. The semantic
   review phase did the real filtering.
2. On an empty tips file, capability tier won: Opus produced the cleanest
   candidate (and also the cheapest of the round at ~43k tokens — fewer
   wasted motions).
3. Operational gotcha: agent worktrees forked from the session base commit,
   not branch HEAD, so the orchestrator had to inject the brief/tips into
   worktrees and (from task-002 on) give workers an explicit
   `git merge <sha>` sync step.
4. Attribution hygiene works: the label->worker mapping was kept outside the
   repo until post-verdict so the reviewer could not deanonymize candidates.

**Cost.** Workers ~244k tokens total; reviewer ~124k. Reviewer overhead
~= 51% of worker spend.

**Distilled.** 14 lessons into `.code-tips.md` (briefing/run.json contracts,
toplevel anchoring, timestamp + bytecode hygiene, test rigor).

---

## task-002 — M2 Tournament (2026-06-11)

**Setup.** Same 5-worker fleet, same blind protocol — but now every briefing
carried the 14 task-001 lessons. Task: extend the adopted M1 code to full
tournament mode (parallel dispatch, anonymization, configurable reviewer,
three-outcome verdict, exit-code trichotomy).

**Gate.** 5/5 first-pass again — with ZERO hygiene violations (task-001 had
two pyc/tips-committing candidates). The tips measurably raised the floor.

**Verdict.** ADOPT C -> unsealed to a HAIKU worker. With lessons in the
briefing, the cheapest model beat two Sonnets and an Opus on contract
faithfulness. Review also caught, in gate-passing candidates: a real logic
defect (B derived gate-failure autopsies from the passing set, so autopsies
never reached the reviewer — masked by a negative-only test) and a contract
violation (E added an unrequested `label_mapping` key to run.json).

**Findings.**
1. First direct evidence for the PRD's economic thesis: cheap workers + a
   strong reviewer + an accumulating tips file matched (here: beat) expensive
   workers. Round 1 winner: Opus. Round 2 winner: Haiku-with-tips.
2. The knowledge compounds in the context layer, exactly as designed — the
   improvement arrived with no model change, only a better briefing.
3. Weak tests are the loop's blind spot: B's bug survived its own suite
   because the test asserted only the negative (`assertNotIn`). Distilled as
   a tips rule: anonymity/autopsy tests must assert the POSITIVE.
4. Reviewer cost is the dominant scaling concern: ~212k tokens (~54% of the
   ~390k worker spend). Review depth is where the value is, but consolidation
   (PRD section 6) and triage (single-worker dispatch for routine tasks) will
   matter economically.

**Cost.** Workers ~390k tokens total; reviewer ~212k.

**Distilled.** 8 new/amended entries in `.code-tips.md` (anonymization
mechanics, autopsy delivery, verdict validation/exit codes, worktree-add
serialization, positive-assertion testing).

---

## Cumulative metrics (after 2 merged tasks)

| Metric                        | task-001        | task-002        |
|-------------------------------|-----------------|-----------------|
| First-pass gate rate          | 5/5             | 5/5             |
| Hygiene violations in field   | 2               | 0               |
| Verdict                       | adopt           | adopt           |
| Winning model                 | Opus 4.8        | Haiku 4.5       |
| Worker tokens (total)         | ~244k           | ~390k           |
| Reviewer tokens               | ~124k           | ~212k           |
| Round 2 triggered             | no              | no              |

Verdict distribution so far: adopt 2 / synthesize 0 / escalate 0.
Win rate by model: Opus 1, Haiku 1, Sonnet 0.

The chart that matters (gate success over merged tasks) needs more points;
the leading indicator we can already see is field quality: violations per
round went 2 -> 0 once tips entered the briefing.

---

## Word Garden example — first external project (2026-06-11)

The loop's first run against a project that is not itself:
`examples/word-garden-1/`, a terminal word-guessing game built in two
iterations (5-worker tournament for the core engine, triaged 3-worker
tournament for the UI; both verdicts ADOPT). Full forensics and the
process report live with the example: `examples/README.md` and
`examples/word-garden-1/.farnsworth/orchestrator-log.md`.

Headline: the thesis generalized. No-tips round won by Opus; tips-in-
briefing round won by Sonnet over Opus, with field defects falling from
one gate-passing logic bug to zero. New process lessons folded into the
PRD (Section 12, risk table, Section 7 measurement notes): distill tips
in contract language, not advisory language; triage lowers absolute cost
but raises the reviewer's share of spend; per-task gate extensions are
worth first-class support; manual agent dispatch is the working fallback
where nested `claude -p` cannot authenticate; seed repos with
`commit.gpgsign=false` under signing-enforced hosts.

---

## Housekeeping incident — zombie reviewer (2026-06-11)

During the Word Garden run, the background-task panel showed an
"Anonymized review task-001" agent still running 35+ minutes after the
round had closed: an infrastructure retry had DUPLICATED the reviewer
dispatch, the duplicate stalled mid-candidate-reading (~23k tokens, six
reads, then silence), and the completed twin had long since delivered the
verdict. The orchestrator had no record of the duplicate because it never
received a launch acknowledgement for it; it was found by diffing the
host's task ledger against the orchestrator's own dispatch list.

Cleanup: programmatic stop failed (the host's task registry had been
reset, so the id was unknown to TaskStop); the host UI's stop control is
the remaining kill switch. State audit confirmed zero damage: both repos
clean, no stray worktrees/branches, all phase artifacts complete — the
duplicate had read but never written.

What this hardened, now in the tool and PRD (Section 4.3):
1. Per-command `timeout_seconds` for workers (kill -> exit_code -1 ->
   gate what was committed) and reviewer (timeout = infra error; the
   verdict cannot be partial).
2. The idempotency rule that made this incident harmless, promoted to
   protocol: a phase is complete when its ARTIFACT exists and validates,
   never when an agent claims completion or goes quiet. Duplicates then
   cost tokens, not correctness.
3. `farnsworth clean <task-id>`: sweep leftover worktrees/branches so a
   task id can be re-dispatched (collision pre-checks otherwise refuse);
   dirty worktrees skipped without --force.
4. Manual-mode ledger discipline: record every dispatch id at launch,
   set a per-phase deadline, check transcript liveness at deadline,
   stop-verify-redispatch only what's missing.

---

## Word Garden 2 — first replication run (2026-06-12)

The loop's first controlled replication: `examples/word-garden-2/`, the
same spec, byte-identical task-001 brief, fleet, and gate as word-garden-1,
re-seeded with an empty tips file. Both verdicts ADOPT; full process report
in `examples/word-garden-2/.farnsworth/orchestrator-log.md`.

Headline: the parts of the thesis that are mechanism replicated (review
catches real bugs the gate passes; tips cut the field's defect rate 2 -> 1;
duplicate dispatches absorbed by the artifact-boundary rule — it happened
again, in both rounds). The part that was narrative did not: Opus won BOTH
rounds, breaking the three-round cheaper-model-wins streak. PRD updated
(Section 13, Section 7 third measurement note, new risk row): the loop's
early learning signal is defects-per-round in gate-passing candidates, not
winner identity. Two refinements queued: a cross-project tips seed for new
projects (run 2 re-committed a defect run 1 had already distilled in the
other project's tips), and a distillation rule upgrade — contract language
AND explicit scope, after an imperative tip was ignored outside the scope
it failed to state.

---

## Loop upgrade — summary tables and focus-diversified dispatch (2026-06-12)

Two protocol upgrades, implemented directly in the tool (maintainer mode,
not a tournament — the changes are to the loop itself, requested by the
human after the Word Garden 2 replication):

1. **Per-run summary table.** Every run now ends with a short
   what-happened table (worker / focus / exit / gate / candidate /
   ADOPTED, then verdict + reasoning), written to
   `.farnsworth/<task-id>/summary.md`, printed by `farnsworth run`, and
   reprintable with the new `farnsworth report <task-id>`. Generated
   retroactively for all six recorded runs (loop tasks 001–002, both Word
   Garden examples). Motivation: run.json is the contract, but nobody can
   read a tournament's outcome from it in thirty seconds.

2. **Focus directives.** Each worker in `farnsworth.json` may carry a
   one-line focus ("Focus on runtime speed", "Focus on security", "Focus
   on minimal dependencies", ...) appended to its briefing with an
   explicit the-brief-wins precedence sentence. Motivation: every round
   run so far produced IDENTICAL file footprints across the field — blind
   same-family workers converge, which starves the review of variety and
   the two-round trigger of signal. Foci force the field apart in
   round/task 1; the reviewer receives the round's directives as a
   sorted UNATTRIBUTED set (per-candidate focus would deanonymize);
   `run.json` and the summary table record each worker's focus so
   per-focus win rates can accumulate. Round 2 narrows: drop or re-aim
   foci after distillation.

PRD updated: new Section 2.1, Section 4.4 audit paragraph, MVP scope,
risk row (focus read as contract amendment), milestone notes on M4/M5,
two new acceptance criteria. Tests: 46 passing (focus isolation per
worker, unattributed reviewer disclosure, table rendering, summary.md ==
rendered run.json). First live exercise: the next tournament dispatched
from this repo.

---

## Bridge note — Word Garden 3, 4, and 5 (2026-06-12)

Three more recorded runs landed between the entry above and the next one;
their process reports live with the examples rather than here:
`examples/word-garden-3/.farnsworth/orchestrator-log.md` (cross-project
seed tips + focus-diversified dispatch, first live),
`examples/word-garden-4/.farnsworth/orchestrator-log.md` (the fully
CLI-dispatched run; commits-as-artifact hole found and fixed), and
`examples/word-garden-5/.farnsworth/orchestrator-log.md` (first
goal-driven run; constructed review environment, first live). The PRD
carries the distilled findings as Sections 14–16. This note exists so the
journal's own pointer ("written after each merge") has no silent gap.

---

## Loop hardening pass — review findings folded into the tool (2026-06-12)

Maintainer mode, requested by the human after a full review of the repo:
the review found four implementation bugs that undercut the protocol's
own guarantees, three PRD promises the CLI didn't keep, and four queued
items whose evidence base was already sufficient. All folded in, in one
pass; 129 tests passing (was 81).

Bugs fixed:

1. **Silent default-config fallback.** `Config.load` fell back to the
   built-in default on ANY missing path — so a typo'd `--config` would
   dispatch the default fleet, whose old form carried the `--bare` flag
   word-garden-4 proved 100% fatal. Explicit-but-missing is now an error
   in every subcommand, relative `--config` paths anchor at the repo
   root uniformly, and the default worker command is the proven
   `--setting-sources ""` + scoped `--allowedTools` form.
2. **Subprocess workers had no rules of engagement.** The worker
   preamble (commit contract, tips hygiene, blindness) existed only in
   delegate dispatch; it is now shared by both modes — and the hygiene
   rules are additionally enforced mechanically at the gate (a candidate
   touching `.code-tips.md`, `farnsworth.json`, or the brief fails with
   an autopsy).
3. **Re-gating could serve stale labels.** `farnsworth gate` re-runs
   (the documented recovery move) reshuffled labels but never swept
   previous diffs from `candidates/` nor refreshed an existing review
   env. Both fixed; the briefing and the served diffs can no longer
   disagree.
4. **Gate autopsies missed stdout.** pytest-style failures (stdout-only)
   produced bare "tests: exit 1" autopsies; the tail now falls back to
   stdout.

PRD promises now kept by the CLI:

5. **Cost capture** (Section 5 had promised it since v1.0): per-worker
   `total_cost_usd` parsed from JSON output into run.json; reviewer cost
   too; delegate mode gets an orchestrator-writable ledger field; the
   summary table grows a Cost column when costs exist.
6. **Goal artifacts** (Section 4.4's no-hidden-state rule): every
   `farnsworth done` probe writes `.farnsworth/done-checks.json`, and a
   mechanical pass writes the attestation briefing — the semantic half's
   protocol now travels in a file, like the review protocol, not in an
   orchestrator prompt.
7. **Generalize-while-distilling** (M3's rule): the review briefing now
   instructs the reviewer to write general forms to `seed-tips.next.md`
   for seed-pile routing.

Queued items shipped:

8. **`farnsworth preflight`** (queued by word-garden-4): config parse,
   clean tree, green-gate-at-base, and a per-worker scratch-worktree
   canary proving edit + commit — the two observed fatality classes.
9. **Content-based divergence** (M4's confirmed requirement): mean
   pairwise token-Jaccard distance across candidate diffs, recorded in
   every run.json. Recording-only until accumulated rounds calibrate a
   trigger threshold.
10. **`farnsworth metrics`** (M5): the cross-run table from every
    run.json on disk — verdict distribution, gate-rate chart data,
    per-model wins, divergence, dollar costs.
11. **`farnsworth adopt`**: the post-verdict manual stretch (merge
    winner, install code-tips.next.md, sweep) mechanized, with an
    adopted-task counter that finally gives the Section 6 consolidation
    cadence something to count.
