#!/usr/bin/env bash
# Farnsworth Loop GROK attempt runner — approved internal tool.
# Runs the attempt brief in _brief.txt (cwd) on an xAI Grok model via the `grok` headless CLI
# (`grok -p`), under BOTH per-attempt guards: --max-turns (grok HAS one, unlike codex) and a portable
# wall-clock timeout. Usage: grok-run.sh -m <grok-build|grok-composer-2.5-fast> [extra grok flags...]
# Timeout (seconds) from FL_TIMEOUT_SECS (default 600); max-turns from FL_MAX_TURNS (default 30).
set -uo pipefail
FLAG="${*:--m grok-composer-2.5-fast}"   # default to the CLI's own default model
LOG=_grok_run.log
TIMEOUT="${FL_TIMEOUT_SECS:-600}"   # wall-clock backstop (seconds)
MAXTURNS="${FL_MAX_TURNS:-30}"      # PRIMARY guard: cap agentic iterations (grok HAS --max-turns)

[ -f _brief.txt ] || { echo "FARNSWORTH-GROK-ERROR _brief.txt missing" | tee -a "$LOG"; exit 4; }
command -v grok >/dev/null 2>&1 || { echo "FARNSWORTH-GROK-ERROR grok CLI not found on PATH" | tee -a "$LOG"; exit 5; }

# Auth (the grok-specific part): grok resolves its OWN credential in order
#   model.api_key > model.env_key > active OAuth session (~/.grok/auth.json) > XAI_API_KEY (xai- prefix).
# On an OAuth-only box NO key is set and that is the NORMAL state — so, UNLIKE glm/minimax (which hard-fail
# on a missing env key), this runner requires NEITHER credential and injects NEITHER, exactly as codex-run.sh
# reads ~/.codex/auth.json with no env key. A present XAI_API_KEY is already inherited from the env and grok
# picks it up via its own resolution order (never sourced/grepped from rc files — uniform key handling).
# Record which mode was used (for the session-expiry diagnosis the OAuth path needs); does NOT gate.
if [ -n "${XAI_API_KEY:-}" ]; then AUTHMODE="env-key"; else AUTHMODE="oauth-session"; fi

# Write the PROVENANCE marker UNCONDITIONALLY, up front: a missing log at this path proves the runner
# never ran (a native-solve spoof or refusal) and must fail closed (P=0) downstream. Column-0 + provider-
# specific token so the staging validator's '^FARNSWORTH-GROK-' grep is mention-proof.
echo "FARNSWORTH-GROK-PROVENANCE endpoint=cli-chat-proxy.grok.com auth=${AUTHMODE} flag=${FLAG} max-turns=${MAXTURNS} timeout=${TIMEOUT}s" >> "$LOG"

# Headless grok policy (every flag CONFIRMED present in `grok --help`):
#   -p "<brief>"        : single non-interactive invocation; runs agentically (tools) under --max-turns then exits.
#   $FLAG (-m <id>)     : the model variant, pinned so grok never silently uses config.toml's default model.
#   --always-approve    : auto-approve ALL tool executions — the headless permission bypass (grok's analog of
#                         codex approval_policy="never" / claude --permission-mode acceptEdits).
#   --max-turns N       : PRIMARY iteration guard. Grok HAS this (codex does not) — the deliverable written
#                         before the cap is preserved.
#   --disable-web-search: hermetic attempts (no network reads skewing diversity); also quiets web/MCP tools.
#   --no-subagents      : an FL attempt is ONE independent piece of work; grok-build can otherwise spawn up to
#                         8 parallel sub-agents (an internal swarm), which both fights FL's "N independent
#                         attempts" model AND is the main variable-latency surface (a fanned-out run can
#                         balloon to minutes on a non-trivial task; a single agent loop stays ~15-30s).
#   --no-memory         : cross-session memory OFF, so each attempt is hermetic/reproducible and can't be
#                         influenced by — or leak state into — other sessions/attempts. Unrelated to reasoning.
#                         NOTE: we deliberately do NOT pass --no-plan. That flag toggles grok's read-only plan
#                         *permission mode*, not the model's reasoning; FL runs planning-heavy tasks and a
#                         measured A/B showed --no-plan gave NO speed benefit yet thinner plans, so it is omitted.
#   --no-alt-screen     : run INLINE — no fullscreen TUI takeover (mandatory under the `>> LOG` redirect).
#   --no-auto-update    : skip the background update check (CI gotcha) so a script run never stalls/mutates.
#   --cwd "$PWD"        : scope the agent's working root to this attempt workspace (analog of codex -C "$PWD").
# Portable hard timeout (macOS has no coreutils `timeout`): fork the call, SIGALRM -> TERM/KILL. $FLAG is
# unquoted so the outer shell word-splits `-m grok-build` into separate argv elements before perl exec.
# </dev/null pins grok's stdin: with a prompt ARG but an OPEN (non-TTY) stdin an agentic CLI can block
# waiting on stdin and stall the whole wall-clock (the bug that hit glm/codex/minimax). Close it here.
perl -e '
  my $t = shift @ARGV;
  my $p = fork; if (!defined $p) { exit 127 }
  if ($p == 0) { exec @ARGV; exit 127 }
  $SIG{ALRM} = sub { kill "TERM", $p; sleep 3; kill "KILL", $p; exit 124 };
  alarm $t; waitpid($p, 0); exit($? >> 8);
' "$TIMEOUT" grok -p "$(cat _brief.txt)" $FLAG \
    --always-approve \
    --max-turns "$MAXTURNS" \
    --disable-web-search \
    --no-subagents \
    --no-memory \
    --no-alt-screen \
    --no-auto-update \
    --cwd "$PWD" </dev/null >> "$LOG" 2>&1
RC=$?

# Defensive fail-closed (belt-and-suspenders beyond the exit code): if grok hit a terminal auth/model/version
# failure, force a nonzero RC so the provenance gate (DONE exit=0) rejects it even on the rare path where grok
# returns such an error yet still exits 0. GUARDED on "no deliverable file other than the engine files exists"
# (grok has no codex-style `-o` capture, so this stands in for codex's `[ ! -s "$LAST" ]` mention-proof guard):
# a SUCCESSFUL run that merely *discusses* these phrases in its deliverable is never force-failed. The phrase
# list is a VALIDATION ITEM — replace the placeholders with grok's real terminal strings once observed.
if grep -qiE '401 Unauthorized|403 Forbidden|invalid api key|model .* (not found|unavailable)|session (expired|token expired)|requires a newer version of Grok' "$LOG" \
   && ! find . -type f ! -name '_brief.txt' ! -name '_grok_run.log' | grep -q .; then
  echo "FARNSWORTH-GROK-ERROR grok reported a model/auth/version failure (see log)" >> "$LOG"
  [ "$RC" -eq 0 ] && RC=6
fi

[ "$RC" -eq 124 ] && echo "FARNSWORTH-GROK-TIMEOUT secs=${TIMEOUT}" >> "$LOG"
echo "FARNSWORTH-GROK-DONE exit=$RC" >> "$LOG"
tail -20 "$LOG"
