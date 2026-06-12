# Orchestrator Log — Word Garden 4 (first live CLI run)

Process findings from the Farnsworth Loop's first run driven by the actual
CLI (`python3 -m farnsworth run`), 2026-06-12. Runs 1–2 ran the same
protocol via manual agent dispatch because nested headless `claude -p`
could not authenticate in that sandbox; this host's subscription OAuth
works, so the tool finally ran the loop it implements. Per-task forensics:
`.farnsworth/task-001/`, `.farnsworth/task-002/`. Durable engineering
lessons: `.code-tips.md`. This file is about the PROCESS.

Three deliberate experiment variables vs run 2 (which was a strict
replication of run 1):

1. **CLI dispatch** (first live run of the tool itself).
2. **Focus-diversified dispatch (PRD 2.1), first live use** — five distinct
   one-line foci recorded in `farnsworth.json`.
3. **Cross-project tips seed (run 2's proposed M3 extension), first use** —
   13 domain-general entries curated from word-garden-1/-2 tips into
   round-1 `.code-tips.md` (game-specific lessons deliberately excluded).

SPEC.md and tasks/task-001.md byte-identical to runs 1 and 2 (verified).

---

## Pre-flight — the recorded fleet config was never runnable (2 blockers)

The `farnsworth.json` carried by runs 1–2 was written but never executed.
Canary-testing it before dispatch found two 100%-fatal config bugs:

1. **`--bare` cannot authenticate on subscription hosts.** By design it
   never reads OAuth/keychain (auth strictly `ANTHROPIC_API_KEY` /
   `apiKeyHelper`). Every dispatch would have died "Not logged in".
   Replacement: `--setting-sources ""` — keeps settings/plugin isolation,
   OAuth works. (Residual inheritance vs `--bare` — user CLAUDE.md,
   auto-memory — not fully audited; flagged in the PRD risk table.)
2. **`--permission-mode acceptEdits` starves headless workers of Bash.**
   A canary worker could Write files but was DENIED `python3` and
   `git commit` (headless = nobody to approve). The deliverable is the
   branch diff, so every worker would have gated with zero commits. Fix:
   scoped `--allowedTools "Bash(python3:*)" "Bash(git:*)"`.

Loop lesson: **a dispatch config is a runtime contract and needs a
mechanical pre-flight** — one cheap canary per config entry proving
auth/edit/test/commit — before burning a tournament. Queued as a
`farnsworth preflight` CLI feature.

---

## task-001 — Core engine (5 workers, full tournament)

**Timeline (local).** Dispatch 15:28 → last worker done 15:33:55 (fastest:
Haiku 82s; slowest: Sonnet 329s) → reviewer 15:34–15:41 (474s, blind sketch
written before any diff was read) → run.json 15:41:57. **13.5 minutes wall
clock** for a 5-worker tournament plus empirical review; the manual-mode
equivalent took hours of orchestrator babysitting.

**Gate.** 5/5 first-pass (third consecutive 5/5 round 1 across runs).

**Verdict.** ADOPT C → unsealed to **w3, Sonnet 4.6, readability focus**.
The reviewer found the SAME defect class as run 2's round 1 in two
gate-passing candidates — terminal guess leaves the generic
"Good guess!"/"No match" `status_message` — and both were again the Haikus
(A=w2, E=w1). First time a round-1 field containing Opus was NOT won by
Opus.

**Cost (API-equivalent USD, from `--output-format json`).** Workers $3.03
(w1 H $0.17/82s, w2 H $0.28, w3 S $0.81, w4 S $0.73, w5 O $1.04); reviewer
**$3.61 — 119% of worker spend**. Round total ~$6.6.

**Distilled.** Seed entries sharpened with reconfirmation evidence; new
project-scoped "Game logic" section (terminal-message contract,
apply_guess reassignment rule).

---

## task-002 — UI, main loop, packaging (3 workers, triaged)

**Setup.** 1 Haiku (minimal focus), 1 Sonnet (readability), 1 Opus (spec
faithfulness), all briefings carrying 13 seed + task-001 tips. Run-1's
per-task gate extensions became FIRST-CLASS config entries for the first
time (`farnsworth-002.json`): `eof-exit-0` (DEVNULL-stdin run must exit 0)
and `engine-untouched` (`git diff --quiet master -- <engine files>`).
Brief = run 2's byte-for-byte except the engine-test count (40→49, adopted
engines differ).

**Timeline.** Dispatch 15:44 → workers done by 15:51:49 → reviewer
15:52–16:00 (585s) → run.json 16:01:50. ~17 minutes wall clock.

**Gate.** "3/3" — but see the bug below: one PASS was vacuous.

**Verdict.** ADOPT A → unsealed to **w5, Opus 4.8** (replicates run 2:
Opus wins the tips round; run 1's Sonnet win did not reproduce). The field
had one genuinely defective gate-passing candidate (B = w1 Haiku: ASCII
growth stage collapsed to a constant `*`, an e2e "win" test asserting the
vacuous `win OR loss` disjunction — the EXACT pattern the seed tips forbid
verbatim — and `output_fn(prompt, end="")` coupling that TypeErrors on a
plain sink).

**Cost.** Workers $3.60 (H $0.83/76 turns, S $0.93, O $1.84); reviewer
$3.40 (94%). Round total ~$7.0. Project total ~$13.6, ~45 min end to end
including orchestration.

**Distilled.** New "UI / rendering" section (ASCII fallback must preserve
every information channel; label+count, never symbols alone; end screens
are distinct artifacts but still constants), plus two seed entries
reconfirmed with task-002 evidence.

---

## Live loop bug #1: the empty-diff candidate (the run's best finding)

w3 (Sonnet) implemented all of task-002 — then never committed. Five
untracked files sat in its worktree.

- The gate runs IN the worktree; untracked files execute fine → w3 PASSED
  all four gates, including the new extensions.
- `gitutil.write_diff` captures `base..HEAD` → **candidate C was 0 lines**.
- The anonymized briefing then told the reviewer a lie the loop itself had
  manufactured: "Candidate C: candidates/C.diff" listed among gate-passers.

**The mechanical layer validated state the candidate artifact does not
represent.** PRD 4.3's artifact rule ("a phase is complete when commits
exist in the worktree") was stated but not enforced in code.

The semantic layer caught it: the reviewer applied C to base, watched the
gate fail (no `__main__`), called it "an empty diff (non-submission)" in
the verdict, and judged the remaining field on merits. Defence in depth
worked — but the gate's 3/3 is recorded as a vacuous pass, and a worker's
real work nearly vanished from the forensic record (`clean --force` would
have destroyed the only copy; the orchestrator archived it manually as
`w3-uncommitted.diff` before sweeping).

**Fixes folded into the loop** (with tests, same PR as this example):
a worker whose worktree HEAD equals the base commit is now a gate FAILURE
with autopsy "no commits on branch" (uncommitted work archived to
`<id>-uncommitted.diff` for forensics), and candidates are required to be
non-empty diffs.

## Live loop bug #2: `clean` inside a worktree targets the wrong repo

Running `farnsworth clean` with cwd INSIDE a linked worktree resolves
`repo_toplevel(cwd)` to the WORKTREE, which `clean` then protects as "the
main worktree" while still trying to delete its branch (`git branch -D`
fails: branch in use). Housekeeping must resolve the main repository
(`git rev-parse --git-common-dir`), not the nearest toplevel. Fixed with a
test alongside bug #1.

---

## Cumulative metrics (after 2 merged tasks)

| Metric                      | task-001 (13 seed tips) | task-002 (seed + t1 tips) |
|-----------------------------|--------------------------|----------------------------|
| Fleet                       | 5 (2H/2S/1O)             | 3 (1H/1S/1O) triaged       |
| First-pass gate rate        | 5/5                      | 3/3 (one vacuous — empty diff) |
| Correctness bugs in field   | 2 (gate-passing)         | 1 (gate-passing) + 1 non-submission |
| Verdict                     | adopt                    | adopt                      |
| Winning model (focus)       | Sonnet 4.6 (readability) | Opus 4.8 (spec faithfulness) |
| Worker cost                 | $3.03                    | $3.60                      |
| Reviewer cost (share)       | $3.61 (119%)             | $3.40 (94%)                |
| Wall clock                  | 13.5 min                 | 17 min                     |
| Round 2 triggered           | no                       | no                         |

Verdict distribution: adopt 2 / synthesize 0 / escalate 0.
Cumulative model wins across runs 1+2+4: Opus 4, Sonnet 2, Haiku 0.

## What run 4 changes about the loop

1. **The cross-project seed did NOT lower the round-1 defect floor.**
   Round 1 had 2 defects — same count, same defect class, same model tier
   as run 2's seedless round 1. The seed's domain-general "assert the full
   outcome including message fields" could not substitute for the
   project-specific "overwrite status_message on the terminal guess"
   contract: the defective workers' tests asserted what their wrong
   implementation produced, satisfying the general rule's letter. This is
   run 2's "memory is project-scoped" finding confirmed from the other
   direction — general tips don't transfer INTO a domain either. The seed
   isn't useless (see #2), but defect-class prevention needs the
   domain-specific tip only this project's own round 1 could generate.
2. **What the seed DID do: the predicted argparse defect did not recur.**
   Run 2's task-002 Haiku shipped the `try/except SystemExit` bug; this
   run's task-002 Haiku — same tier, same task, seed tip banning it
   verbatim — did not. One data point in favour, against one against:
   net read is that seeds prevent *mechanical* error classes (exact
   API-shaped rules) but not *semantic* ones (state-contract rules).
3. **Tier dominates focus.** First live focus round: foci visibly shaped
   style (the minimal-focus Haiku shipped the smallest diffs; the
   spec-focus Opus won on faithfulness), but the TEST-RIGOR-focused Haiku
   still shipped the flag-only-assertion defect, and a Haiku violated a
   verbatim seed rule in task-002. A focus is a lens, not a capability
   upgrade; correctness floor tracks tier, then tips, then focus.
4. **Reviewer cost has crossed 100% of worker spend** ($3.61 vs $3.03 with
   cheap fast workers; 94% in the triaged round). Manual-mode shares
   (50–68% of tokens) understated this: empirical per-candidate
   verification is the loop's dominant line item once dispatch is cheap.
   Review depth must scale with field DISAGREEMENT, not field size —
   convergent fields need spot-checks, not five full probe suites. Queued
   for M4 alongside divergence measurement.
5. **The CLI's phase-boundary enforcement had a hole** (bug #1) and its
   housekeeping a wrong-repo hazard (bug #2); both now fixed with tests.
   The artifact-is-the-boundary principle survived because the REVIEW
   layer is also artifact-driven — the verdict cites only evidence the
   reviewer produced itself. Worth keeping both layers skeptical.
6. **Dollar-denominated runs change the conversation.** $13.6 and 45
   minutes for a complete two-task project with full forensics. The
   summary tables now carry real prices; per-model win-rate economics
   (Section 7) can start accumulating against actual spend.
