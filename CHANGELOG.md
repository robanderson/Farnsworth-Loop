# Changelog

All notable changes to the **farnsworth-loop** plugin are documented here.
The format loosely follows [Keep a Changelog](https://keepachangelog.com/); each version maps to a git tag.

## [Unreleased]

### Added — dynamic per-attempt limits (task-size–aware turn caps + timeouts)

The per-attempt iteration caps and wall-clock timeouts were hard-coded (GLM 30 turns / 300s, local 20 turns,
codex 600s, etc.). They now scale to how big the task is — a one-line script and a heavy multi-file build get
very different headroom.

- **Orchestrator estimate.** In a new SKILL **Phase 1c**, the orchestrator classifies the task as `short`,
  `medium` (the default when unsure), or `long`, and passes that size's limit profile into the tournament
  workflow.
- **Manual override via the sigil.** A marker-adjacent `short` / `medium` / `long` next to `@@FL`
  (e.g. `@@FL:5 long`, `@@FL short, fix the bug`, `tidy up long @@FL:4`) forces the size. It is recognised
  only adjacent to the marker and stripped from the task (the AFTER form needs a comma/semicolon/end right
  after it), so an ordinary size word in the task body (`long division solver`, `short-circuit evaluator`) is
  left untouched. `fl-parse.mjs` now emits a `size` field (`short|medium|long|null`).
- **Single source of truth.** `SIZE_PROFILES` in `bin/fl-parse.mjs` defines each label's full guard set;
  `node bin/fl-parse.mjs --size <label>` prints it as JSON. The keys are exactly the workflow arg names
  (`attemptMaxTurns`, `localMaxTurns`, `minimaxMaxTurns`, `grokMaxTurns`, `attemptTimeoutSecs`,
  `glmTimeoutSecs`, `codexTimeoutSecs`, `grokTimeoutSecs`), so they flow through to the runners as
  `FL_MAX_TURNS` / `FL_TIMEOUT_SECS` unchanged. `medium` matches the historical engine defaults in spirit.
- **Scope.** Engine (`tournament.mjs`) and the runner scripts are unchanged — they already accepted these
  args/env vars; this wires the orchestrator to set them per task. Native Anthropic attempts remain uncapped
  (the workflow `agent()` primitive exposes no turn/time cap). New parser tests cover the override, the
  false-positive guards, the profiles, and the `--size` CLI.

## [0.1.1] — 2026-06-20

### Fixed — repoMode runner-provider failures + a verify-gate hang (found dogfooding the first repoMode grand loop)

The first full repoMode grand loop (Z=2) surfaced two real bugs that broke repoMode for the non-Anthropic
providers and intermittently hung the verify gate. Both are fixed; the default (`repoMode:false` /
`FL_VERIFY_SANDBOX` unset) behavior is unchanged.

- **#44 — repoMode attempt worktrees moved out of `~/.claude/`.** They were created under
  `${runDir}` (= `~/.claude/.../.runs/...`), which the harness sandboxes — so runner sub-agents
  (glm/minimax/codex/grok) were denied `Write`/`Edit`/shell-redirect in their own worktree and failed or
  burned their turn budget (only native opus, and runner models that found the allow-listed `python3`
  workaround, succeeded). The worktree **checkout** now lives at `/tmp/fl-worktrees/<runId>/round-N/<label>`
  (configurable via `args.worktreeRoot`; hardcoded `/tmp` default because the engine sandbox has no `process`).
  Only the checkout moved — staging, `_engine-logs`, and the run dir stay under `runDir`; `repoMode:false` is
  byte-identical. Validated: glm-5.2 / codex-high / minimax-m3 now produce valid deliverables in repoMode.
- **#46 — `fl_run_with_timeout` no longer hangs command-substitution callers.** Its watchdog subshell
  inherited fd 1; the residual instant-command race could orphan the watchdog `sleep`, which then held a
  `$(...)` capture pipe open for the full timeout — so `run_verify` / `bin/fl-git.test.sh` (whose helper
  captures output via `$()`) hung 600s (`exit 124`) ~55%/run, flaking the verify gate. The watchdog's fds are
  now detached (`>/dev/null 2>&1`); the command keeps fd 1 so captured output is unchanged. Repro: 5/40 → 0/40
  hangs; added regression test.

Known: `farnsworth-grok` attempts require a session in which the agent type is registered (it is in the
plugin; a session started before the agent was installed cannot dispatch it) — tracked in #45 (not a code bug).

## [0.1.0] — 2026-06-20

### Added — repo-anchored worktree mode (P0–P6): attempts build real code in git worktrees

A new **opt-in repo-anchored** task mode: each tournament attempt is a real `git worktree` branched off a
single pinned base, the winning attempt's commit is adopted directly as the mergeable ref (collapsing the
lossy "Opus implementer re-derives the proposal" hop), and a fail-closed validation gate (verify + a nested
security audit) guards it before any PR. Every new path is gated on `repoMode` / `FL_VERIFY_SANDBOX`, so the
default (off) behavior is **byte-for-byte unchanged**. Shipped in seven staged, independently-valuable phases —
themselves implemented end-to-end by the Farnsworth Loop (a 7-loop grand-loop) and validated with a live
repo-anchored tournament. Design doc: `docs/git-worktree-implementation-plan-v2.md`.

- **P0 — mode plumbing** (`bin/fl-parse.mjs`): `repoMode`/`baseRef` result fields; marker-adjacent
  `repo-anchored` / `--no-repo` / `self-contained` keywords (stripped at source); `Z>=2` defaults it on;
  `repoMode && z<2` is a fail-closed parser error. Parser stays pure/total.
- **`run_verify` wall-clock timeout** (`bin/fl-git.sh`): portable bash-3.2 `fl_run_with_timeout` watchdog
  (TERM→KILL, reaps both the command and its watchdog, rc→124), wired per verify command;
  `FL_VERIFY_CMD_TIMEOUT` (default 600s) — the one missing `run_verify` hardening.
- **P1 — worktree-per-attempt** (`workflows/tournament.mjs`): `buildWorktrees`/`snapshotWorktrees`, the
  repo-anchored brief ("apply your change on this branch"), a fixed-identity harness commit (no
  author/timestamp/branch leak), and diff-based blind staging; engine/provenance logs kept OUTSIDE the
  worktree so `git add -A` can never commit a provider token.
- **P3 — validation gate**: `detect_verify [<dir>]` (freeze the verify set from the winner's worktree); SKILL
  Phase-7 nested `@@FL` security audit (sibling Workflow, union-of-findings reconciler — not the competitive
  judge) + bounded runner-up→needs-human fallback, disambiguating `run_verify`'s overloaded rc 1.
- **P2 — winner-as-ref adoption** (`adopt_winner_branch`): aliases the `FL-` branch to the winner's EXACT
  gated commit (no re-author/squash/cherry-pick — "validated ref == merged ref"); `farnsworth-implementer`
  scoped to legacy (`repoMode:false`) mode.
- **P5 — test/lint enrichment** (`enrichBlindPool`): per-candidate test/lint run in the worktree (reusing
  `detect_verify` + `fl_run_with_timeout`) → a blind-safe, counts-only summary into the judge's pool; secrets
  dropped before running candidate code.
- **P6 — sandboxed verify**: relax `verify_safe_diff`'s config-touch refusal ONLY under `FL_VERIFY_SANDBOX=1`
  (set by the driver after the audit clears), running verify under a no-network/no-credentials sandbox
  (macOS `sandbox-exec` reference profile, or an operator `FL_VERIFY_SANDBOX_WRAPPER`); fail-closed (rc 125)
  if the sandbox is unavailable — never unsandboxed.

Tests: `fl-parse` 322→398, `fl-git` 33→81, plus new `workflows/tournament-worktree-mode.test.mjs`.

## [0.0.4] — 2026-06-19

### Changed — grok runner: bound to one independent agent loop + web-search knob

- **`bin/grok-run.sh`** now passes **`--no-subagents`** so a grok attempt is ONE independent unit. grok-build
  can otherwise spawn up to 8 parallel sub-agents (an internal swarm) — that fights FL's "N **independent**
  attempts" model and is the main variable-latency surface. (`bin/fl-bench.mjs` `dispatchGrok` too.)
- **Web search is a per-run knob, OFF by default.** Hermetic and consistent with the other runner-based
  providers (glm/minimax/local have no web tools; codex sets `mcp_servers={}`), so a *mixed* blind review stays
  fair. Enable it for a run with **`grokWebSearch: true`** (→ `FL_GROK_WEB=1`) when a task needs LIVE web at
  attempt time (validate a URL/doc, check a link) — something the shared `contextFiles` bundle can't pre-provide.
  The provenance line records `web=on|off`.
- **Deliberately NOT `--no-plan`** (toggles grok's read-only plan *permission* mode, not reasoning; FL runs
  planning-heavy tasks and a measured A/B showed it gave no speed benefit yet thinner plans) and **not
  `--no-memory`** (cross-session memory is the opt-in `--experimental-memory` feature, off by default → no-op).
- **Context:** a live-fire tournament saw one grok-build attempt run ~6 min once; it was **not reproducible**
  (follow-up runs were 15–50s), so the sub-agent bound is defensive hardening that removes the fan-out latency
  surface rather than a confirmed fix for that specific transient. grok itself completed correctly and a grok
  variant (`grok-composer-2.5-fast`) won that tournament's blind review.

## [0.0.3] — 2026-06-19

### Added — xAI Grok provider (the `grok` CLI)

Grok joins GLM, MiniMax, codex, and the local/Anthropic backends as a sixth tournament provider,
exposing **both** model variants an operator can select:

- **`grok-build`** — xAI's own agentic-coding model (`grok-code-fast-1` lineage, 256K context).
- **`grok-composer-2.5-fast`** — Cursor Composer 2.5 (Kimi K2.5 lineage), the `grok` CLI default.

New and changed files:

- **`bin/grok-run.sh`** *(new)* — headless runner shelling to `grok -p "$(cat _brief.txt)" -m <id>
  --always-approve --max-turns <N> --disable-web-search --no-alt-screen --no-auto-update --cwd "$PWD"`
  under the portable perl wall-clock timeout, with stdin pinned and a mention-proof defensive fail-closed
  guard. Writes `FARNSWORTH-GROK-PROVENANCE` / `-DONE` / `-TIMEOUT` markers to `_grok_run.log`.
- **`agents/farnsworth-grok.md`** *(new)* — one generic `haiku` command-runner stub serving **both**
  variants (the `-m <id>` rides in the command, like `farnsworth-codex`).
- **`workflows/tournament.mjs`** — `GROK_FLAG` map; `dispatch:'grok'` branch using the **standard
  `runnerCmd` (both `FL_MAX_TURNS` + `FL_TIMEOUT_SECS`), not `codexRunnerCmd`**; `grokRunner` /
  `grokMaxTurns` (default 30) / `grokTimeoutSecs` (default 600) knobs; `_grok_run.log` added to
  `engineFiles` and the staging strip list; `GROK` provenance token in the line-anchored validator.
- **`bin/fl-parse.mjs`** — prose-spec recognition for `2 grok`, `grok-build`, `grok composer 2.5 fast`,
  and bare `composer …`; bare `grok` resolves to **`grok-build`** (the operator's `/model grok`). Adds
  11 regression tests (398 total passing).
- **`bin/fl-bench.mjs`** — `GROK_MODELS` (both variants), `dispatchGrok`, and `grok` provider registration
  so `fl-bench --models grok` (and `grok:grok-build` / `grok:grok-composer-2.5-fast`) benchmark throughput.
- **`skills/farnsworth-loop/SKILL.md`** — Phase 1 menu option 10 (Grok → variant submenu), Specify-Mix
  entry, Phase 2 dispatch, Phase 6 provenance check, quick-reference.
- **`skills/farnsworth-loop/references/orchestration.md`** — Grok model-identifier and dispatch sections,
  ARGS-shape additions (`grokRunner` / `grokTimeoutSecs`).
- **`.claude-plugin/plugin.json`** — registers the `farnsworth-grok` agent; bumps version; description
  now lists Grok as a selectable provider.

### Auth & design notes

- Grok authenticates from the operator's **grok.com OAuth session** (`~/.grok/auth.json`, `auth_mode=oidc`);
  `XAI_API_KEY` (`xai-` prefix) is the headless/CI fallback. The runner injects **neither** credential and —
  unlike glm/minimax — does **not** hard-fail on a missing env key; grok resolves its own, exactly like codex
  reads `~/.codex/auth.json`. The active mode is recorded as `auth=oauth-session|env-key` in the provenance line.
- Provenance endpoint is the default OAuth inference route, `cli-chat-proxy.grok.com` (not `api.x.ai`).
- Unlike codex, grok **has `--max-turns`**, so it uses **both** per-attempt guards (max-turns + wall-clock).
- The agentic file-write path (`grok -p --always-approve --max-turns` actually writing a deliverable) was
  verified end-to-end against the live `grok` v0.2.56 binary before release.

### Provenance

The integration design was produced by a Farnsworth Loop **two-pass tournament** (N=6: 2× opus, 2× glm-5.2,
2× codex-medium); the winning Opus plan is preserved at [`docs/grok-roster-plan.md`](docs/grok-roster-plan.md).

## [0.0.2]

Prior release (tag `v0.0.2`): MiniMax provider, grand-loop (`Z`) hardening, repoMode worktree-per-attempt,
shared context bundling, and parser / bench / orchestration refinements.
