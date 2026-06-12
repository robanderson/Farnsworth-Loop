# The Farnsworth Loop

> *"Good news, everyone!"*

**The Farnsworth Loop is the Ralph loop made self-evaluating.** Keep
Ralph's shape — a dumb driver, fresh contexts every pass, all memory
on disk in git, run unattended — and substitute intelligence at the
three places Ralph has none: each iteration's single attempt becomes a
two-round, best-of-N blind tournament where round one's distilled
lessons and champion (never its code) advance into round two; Ralph's
human guardrail-tuner becomes the judge's automated distillation into
the tips file; and Ralph's infinite `while :` becomes a termination
contract — every cycle is scored against the rubric and the test
suite, and completion is decided against the *original goal*,
mechanically and by attestation.

---

## The idea in thirty seconds

Agent loops differ on exactly one axis: **what flows back through the
feedback path.**

| Loop | Feedback | Ignition | Knows when it's done |
|---|---|---|---|
| **Ralph** | nothing — same prompt, fresh context, persistence as strategy | one command, unattended | never: `while :` ends at Ctrl-C or an empty wallet |
| **Karpathy** | a number — keep what beats the metric, revert the rest | one command, unattended | never: hill-climbs until you stop paying |
| **Farnsworth** | *lessons* — every attempt, winners **and** losers, distilled into every future briefing | one command, unattended | **yes** — done checks + attestation against the original goal |

Most software work has no cheap metric to thermostat against, and
persistence alone just repeats yesterday's mistakes with today's
tokens. The Farnsworth Loop closes the loop with **semantic feedback**:
failures are not wasted tokens, they are gotchas passed forward —
inspectable, diffable, versioned in git next to the code they describe.

## The loop, end to end

It is a loop twice over: rounds repeat **inside** a task until
something is adoptable, and tasks repeat until the goal is done — two
cycles for a small brief, two hundred for a hard one. Each pass is
deliberately small: explore, learn, rebuild with the knowledge (never
the code), select, inspect against the goal, and **go around again**
with the next instruction added.

```
            GOAL — the termination contract: what done means
              │
              ▼
   ┌──────▶ DERIVE the next task — the smallest gateable
   │         slice of what's still missing
   │          │
   │          ▼
   │      EXPLORE    N blind parallel coders, focus-diversified —
   │          │      your fleet: Claude tiers, GLM, Qwen, local…
   │          ▼
   │      GATE-1 ─▶ JUDGE (anonymized A/B/C/D, blind sketch first)
   │          │      ─▶ VERDICT-1: crown a CHAMPION
   │          ▼
   │      DISTILL    lessons → .code-tips.md — the code is thrown
   │          │      away; the lessons enter every future briefing
   │          ▼
   │      REBUILD    fresh blind coders, clean slate: the brief +
   │          │      the lessons, never round-1 code
   │          ▼
   │      GATE-2 ─▶ JUDGE (champion relabeled in, judged blind)
   │          │      ─▶ VERIFY (fresh eyes attack the verdict)
   │          │
   │      nothing adoptable? ──▶ distill again, rebuild again
   │          │                  (each extra round must show
   │          ▼                   progress, or the task escalates)
   │      MERGE the winner
   │          │
   │          ▼
   │      INSPECT against the goal — `farnsworth done` + attestation
   │          │
   └── not done: bank the lessons, name the gap,
              │  derive the next slice — GO AGAIN
              ▼
        DONE — both halves attested · or ESCALATED / STOPPED / STALLED,
        always recorded, never silent
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

## The premise engine (why "Farnsworth")

Professor Hubert J. Farnsworth's role in Futurama is to **create the
premise**: he announces *"Good news, everyone!"* — news that is
frequently terrible — and the crew gets dispatched to suffer the
consequences. The loop adopts its namesake faithfully:

- **Every cycle opens with a premise.** The orchestrator reads the gap
  between the merged state and the goal and announces the next mission
  — the smallest gateable slice of what's missing. The task brief *is*
  the premise.
- **The crew implements it, blind.** Workers are sent into isolated
  worktrees on what may well be a lethal mission; their failures are
  not wasted, they're distilled.
- **The episode gets judged.** A premise can be absurd, dangerous, or
  wrong — the Professor is brilliant but careless — so nothing trusts
  it blindly: the judge can escalate a broken premise, the verifier
  attacks the verdict, and the attestor can refuse to call the goal
  met. The end of every cycle asks the only question that matters:
  *did the premise advance the goal?*
- And per house convention, every distilled lesson lands in git as
  `Good news, everyone! <what we learned>` — delivered exactly the way
  the Professor would, whether or not the news is good.

## Ignition

One action, then it runs wild until the job is attested done — that is
the contract. With dynamic workflows enabled (Claude Code ≥ 2.1.154),
ask Claude to run the `farnsworth-loop` workflow:

```js
{ repo: '/abs/path/to/your-project',
  fleet: [ /* optional override — confirmed in the Fleet phase */ ] }
```

It cycles: **premise** (derive the smallest next task) → nested
`farnsworth-task` tournament (Fleet → R1 Explore → R1 Gate → R1 Judge
→ Distill → R2 Rebuild → R2 Gate → R2 Judge → Verify → Finalize) →
merge → probe + attest against the goal → **go again**, exiting only
at DONE / ESCALATED / STOPPED / STALLED. Run `farnsworth-task` with
`{ repo, brief: 'tasks/task-001.md' }` for a single turn of the crank.
Watch either in `/workflows`: live per-agent token counts, pause/stop
keys. (A Ralph-grade `python3 -m farnsworth loop` one-liner for
subprocess and local fleets is the next build — see Now and next.)

Seed a new project's `.code-tips.md` from
[`seed-tips.md`](seed-tips.md) — the cross-project lessons distilled
from every recorded run — and declare a `goal` with done checks in
`farnsworth.json`: a loop without a termination contract either stops
early or never.

### Under the hood: the forensic interface

The conductors drive a Python CLI that owns every mechanical phase —
`preflight`, `run`, `gate`, `finalize`, `adopt`, `done`, `report`,
`metrics`, `clean` — each emitting `--json` records and exit codes the
scripts consume. You never need to drive it by hand to *use* the loop;
you reach for it to **replay, audit, or debug** a round, because every
phase boundary is a file in git: briefings, anonymized diffs, gate
autopsies, verdicts, attestations. No database, no hidden state — any
decision reconstructible from history alone.

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
- [ ] **`python3 -m farnsworth loop` — the Ralph-grade CLI ignition:**
      one terminal command cycling premise → tournament → merge →
      attest, unattended, for subprocess/local fleets (M7's CLI
      mechanization of the two-round spine, plus the loop driver)
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
