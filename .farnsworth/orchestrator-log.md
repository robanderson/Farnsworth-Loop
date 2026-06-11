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
`examples/word-garden/`, a terminal word-guessing game built in two
iterations (5-worker tournament for the core engine, triaged 3-worker
tournament for the UI; both verdicts ADOPT). Full forensics and the
process report live with the example: `examples/README.md` and
`examples/word-garden/.farnsworth/orchestrator-log.md`.

Headline: the thesis generalized. No-tips round won by Opus; tips-in-
briefing round won by Sonnet over Opus, with field defects falling from
one gate-passing logic bug to zero. New process lessons folded into the
PRD (Section 12, risk table, Section 7 measurement notes): distill tips
in contract language, not advisory language; triage lowers absolute cost
but raises the reviewer's share of spend; per-task gate extensions are
worth first-class support; manual agent dispatch is the working fallback
where nested `claude -p` cannot authenticate; seed repos with
`commit.gpgsign=false` under signing-enforced hosts.
