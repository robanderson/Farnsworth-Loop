# Changelog

All notable changes to the **farnsworth-loop** plugin are documented here.
The format loosely follows [Keep a Changelog](https://keepachangelog.com/); each version maps to a git tag.

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
