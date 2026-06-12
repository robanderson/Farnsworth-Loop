# The Farnsworth Loop

> *"Good news, everyone!"*

**Five AI coders attempt your task in parallel, blind. An AI judge
reviews their diffs anonymized — no names, no models, no order. The
winner merges. The losers' mistakes become lessons in every future
briefing. The models never get smarter; your project does.**

---

## The idea in thirty seconds

Agent loops differ on exactly one axis: **what flows back through the
feedback path.**

| Loop | Feedback | What it is |
|---|---|---|
| **Ralph** | nothing | same prompt, fresh context, persistence as strategy |
| **Karpathy** | a number | keep or discard against a metric — a thermostat |
| **Farnsworth** | *lessons* | a review phase distills every attempt — winners **and** losers — into tips injected into every future briefing |

Most software work has no cheap metric to thermostat against, and
persistence alone just repeats yesterday's mistakes with today's
tokens. The Farnsworth Loop closes the loop with **semantic feedback**:
failures are not wasted tokens, they are gotchas passed forward —
inspectable, diffable, versioned in git next to the code they describe.

## One round, end to end

```
            tasks/task-042.md  +  .code-tips.md (the project's memory)
                                 │
        ┌───────┬───────────┬────┴──────┬───────────┐   blind, parallel,
      coder   coder       coder       coder       coder  focus-diversified
     (haiku) (haiku)    (sonnet)    (sonnet)     (opus)
        └───────┴───────────┴────┬──────┴───────────┘
                                 ▼
                GATE   mechanical: tests, build, hygiene,
                       commits-as-artifact — evidence, not opinion
                                 ▼
               JUDGE   anonymized diffs A/B/C/D, randomized order,
                       blind sketch first, empirical probes
                                 ▼
              VERIFY   fresh eyes attack the verdict's claims
                                 ▼
             VERDICT   adopt · synthesize · escalate
                                 ▼
             DISTILL   lessons → .code-tips.md → every future briefing
```

Anonymity is load-bearing: the judge never learns which model wrote
which diff, so cheap models win on merit — and they do. In the loop's
first dogfooding cycle, round 1 (empty tips) went to Opus; round 2,
with fourteen distilled lessons in the briefing, went to **Haiku**.

## The architecture (June 2026)

Three layers, each doing what it does best:

```
.claude/workflows/farnsworth-task.js   CONDUCTOR — dynamic workflow:
                                       phases, agent fan-out, live
                                       token telemetry in /workflows
.claude/agents/farnsworth-*.md         JUDGMENT — coder, judge,
                                       verifier, attestor roles
farnsworth/  (Python CLI)              TRUST — deterministic, token-free,
                                       tested: worktrees, gates,
                                       anonymization, audit artifacts
```

Agents never grade their own work; code never asks an agent to do what
a subprocess does for free; and every decision is reconstructible from
git history alone — no database, no hidden state.

## Quickstart

```bash
cd your-project            # a clean git repo
# with dynamic workflows enabled (Claude Code ≥ 2.1.154):
/farnsworth-task tasks/task-001.md

# or phase by phase, any host:
python3 -m farnsworth preflight        # canary before you spend
python3 -m farnsworth run tasks/task-001.md   # worktrees + briefings
#   …spawn one coder subagent per briefing…
python3 -m farnsworth gate task-001    # gate, anonymize, brief the judge
#   …spawn the judge subagent…
python3 -m farnsworth finalize task-001
python3 -m farnsworth adopt task-001 --clean   # merge + install lessons
python3 -m farnsworth done             # goal met? 0 done / 1 keep looping
```

Every phase command takes `--json` for machine-readable output. Seed a
new project's `.code-tips.md` from [`seed-tips.md`](seed-tips.md) — the
cross-project lessons distilled from every recorded run.

## Receipts

Seven recorded runs, every artifact committed
([`examples/`](examples/)):

- **Tips raise the floor, fast.** Spec/hygiene violations went 2 → 0 in
  one distillation cycle; defect classes covered by seed tips recurred
  **zero** times across projects *and domains* (terminal game → CSV
  reporting).
- **The gate filters mechanics; the judge filters meaning.** Every
  recorded review found real defects in candidates that passed every
  mechanical check.
- **The residual defect rate concentrates exactly where memory hasn't
  been yet** — the learning thesis, read from the other side.
- A full five-coder tournament with empirical review: ~13 minutes.

## Going deeper

- [`PRD.md`](PRD.md) — the full specification and lab notebook: the
  protocol, the two-round explore→rebuild structure, the goal
  termination contract, every recorded run and every distilled lesson
- [`examples/`](examples/) — complete forensic records of real runs
- [`.claude/`](.claude/) — the workflow, agent roles, and skills

## Standing on shoulders

- The **Ralph loop** — [Geoffrey Huntley](https://ghuntley.com/ralph/):
  persistence as strategy, the baseline we measure against
- The **Karpathy loop** — Andrej Karpathy's keep/discard-against-a-metric
  framing of agentic iteration
- **Warnier/Orr output decomposition**
  ([structured design, 1970s](https://en.wikipedia.org/wiki/Warnier/Orr_diagram))
  — our requirements grammars are sixty-year-old medicine
- **Anthropic's June 2026 orchestration stack** —
  [dynamic workflows](https://code.claude.com/docs/en/workflows),
  [subagents](https://code.claude.com/docs/en/sub-agents),
  [best practices](https://code.claude.com/docs/en/best-practices)
- **Professor Hubert J. Farnsworth**, who delivered bad news the same
  way every time, and good news only when there was some

---

*Ralph persists. Karpathy measures. Farnsworth learns.*
