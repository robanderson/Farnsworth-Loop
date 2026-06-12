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

## One task, end to end: explore, distill, rebuild

```
         tasks/task-042.md  +  .code-tips.md (the project's memory)
                                │
  ROUND 1 — EXPLORE             ▼
        ┌───────┬───────────┬───┴───────┬─────── ─ ─ ┐   N blind, parallel,
      coder   coder       coder       coder        coder  focus-diversified
        └───────┴───────────┴───┬───────┴─────── ─ ─ ┘   agents — your pick
                                ▼
              GATE-1   mechanical evidence — tests, build, hygiene,
                       commits-as-artifact; results travel WITH each
                       candidate, they don't filter the field
                                ▼
               JUDGE   anonymized diffs A/B/C/D, randomized order,
                       blind sketch first; probe the passers,
                       idea-mine the failers
                                ▼
           VERDICT-1   crown a CHAMPION (or none) · escalate
                                ▼
             DISTILL   lessons → .code-tips.md; mechanizable lessons
                       ratchet into gate-2 — code is thrown away,
                       lessons travel
                                │
  ROUND 2 — INFORMED REBUILD    ▼
                       fresh blind coders, clean slate:
                       brief + distilled lessons — never round-1 code
                                ▼
              GATE-2   strict, including the round-1 ratchets
                                ▼
               JUDGE   round-2 field + the champion, relabeled
                       together — "did learning beat blind
                       exploration?" is decided blind
                                ▼
              VERIFY   fresh eyes attack the verdict's claims
                                ▼
           VERDICT-2   adopt · synthesize · escalate  →  MERGE
                                ▼
             DISTILL → derive the next task from the goal gap,
                       until `farnsworth done` says DONE
```

Anonymity is load-bearing twice over: the judge never learns which
model wrote which diff — so cheap models win on merit, and they do —
and the verdict-2 judge never learns which candidate is the round-1
champion, so the loop's core claim is tested blind every task. A
champion that survives the rebuild is recorded as a negative learning
result, never hidden. In the loop's first dogfooding cycle, the
empty-tips round went to Opus; with fourteen distilled lessons in the
briefing, the rebuild went to **Haiku**.

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

## Pick your fleet

The field is **declared per run, never hardcoded**: `farnsworth.json`
names the workers, and every dispatch starts by confirming the fleet
you actually want — the conductor asks before any tokens are spent.
The protocol doesn't care who codes; anonymized review means every
entrant wins on merit alone.

```jsonc
// Anthropic fleet — delegate dispatch (subscription-billed subagents)
"workers": [
  {"id": "w1", "model": "claude-haiku-4-5",  "focus": "test rigor"},
  {"id": "w2", "model": "claude-sonnet-4-6", "focus": "simplicity"},
  {"id": "w3", "model": "claude-opus-4-8",   "focus": "spec faithfulness"}
]

// Third-party / local fleet — the command adapter: anything with a CLI
"workers": [
  {"id": "w1", "command": ["qwen-code", "-p", "{prompt}"]},          // Qwen
  {"id": "w2", "command": ["codex", "exec", "{prompt}"]},            // Codex
  {"id": "w3", "command": ["glm-cli", "run", "{prompt}"]},           // GLM
  {"id": "w4", "command": ["ollama", "run", "qwen3-coder", "{prompt}"]} // local:
]                                            // Ollama / LM Studio / MLX…
```

The 2× Haiku / 2× Sonnet / 1× Opus mix you'll see in the recorded runs
is a *default and an experiment* — per-model win rates accumulate in
the run logs to answer whether cheap workers plus a strong judge beat
expensive workers — not a fixture of the design. A fleet runs one
dispatch mode per round today; heterogeneous Claude+local fields in a
single round are on the roadmap (PRD M8).

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

## Now and next

What's proven in recorded runs versus what's on the bench
(full milestone detail in [PRD.md](PRD.md), Section 9):

**Working today**

- [x] Blind parallel dispatch into per-worker git worktrees, with
      focus-diversified briefings and the project's tips injected
- [x] Mechanical gate: tests/build/hygiene with per-command deadlines,
      commit-as-artifact enforcement, parallel execution, live progress
- [x] Anonymized review in a constructed environment (no branches, no
      config, no attribution surfaces) with a validated three-outcome
      verdict — plus an adversarial Verify pass on the verdict's claims
- [x] Distillation: reviewer-owned `.code-tips.md` per project and the
      cross-project [`seed-tips.md`](seed-tips.md) pile — zero
      recurrence of seed-covered defect classes across runs and domains
- [x] Goal termination contract: `farnsworth done` + semantic
      attestation; four honest exits (DONE/ESCALATED/STOPPED/STALLED)
- [x] Dynamic-workflow conductor (`.claude/workflows/`) running the
      two-round explore→rebuild spine, with skills as the fallback
      conductor and `--json` phase records throughout
- [x] Dynamic fleet selection: the field is confirmed per run — never
      a hardcoded mix
- [x] The subprocess `command` adapter, proven end-to-end with headless
      `claude -p` fleets (word-garden-4, dollar-true costs)

**Planned**

- [ ] **Third-party and local coders in the parallel field:** GLM,
      MiniMax, Qwen, Codex, and local models via Ollama / LM Studio /
      MLX through the command adapter — the adapter works; the first
      live non-Anthropic fleet hasn't run yet
- [ ] **Heterogeneous fields:** Claude + third-party + local agents
      competing in the *same* anonymized round (config currently
      enforces one dispatch mode per fleet)
- [ ] Workflow conduction of subprocess/local fleets (today they run
      end-to-end via `farnsworth run`)
- [ ] M7: the two-round v2 protocol mechanized in the CLI itself —
      verdict-1 champion schema, scripted champion relabeling retired,
      gate-as-evidence for no-candidate explore rounds
- [ ] Per-agent token telemetry from `/workflows` into `run.json`, and
      `maxTurns` caps on coder dispatch
- [ ] The gate-success-over-time chart rendered from the banked run
      logs (`farnsworth metrics` already emits the data)
- [ ] M6: the TUI memory-map visualization of a running fleet

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
