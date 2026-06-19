#!/usr/bin/env bash
# fl-git.sh — Farnsworth Loop grand-loop git/gh helper (approved internal tool).
#
# ALL real-repo side effects for grand loops (Feature 1) live here, as callable
# functions, so an agent never improvises git/gh. tournament.mjs is UNCHANGED and
# there is NO nested grand-loop workflow: the SKILL.md Phase-7 procedure drives the
# Z-loop and calls these functions for the deterministic, must-not-improvise parts.
#
# Dual interface:
#   - sourceable:   source fl-git.sh ; fl_branch 1
#   - CLI dispatch: bash fl-git.sh <fn> [args...]    (the benign-command pattern,
#                   matching glm-run.sh — the SKILL calls `bash fl-git.sh <fn> ...`)
#
# Portable on macOS: NO GNU coreutils, NO `timeout`/`gtimeout`, /dev/urandom for
# randomness (never Date/Math.random). Every gh/git call is rc-checked and the rc
# is propagated; failures fail closed.
#
# Functions (the SKILL Phase-7 driver calls exactly these signatures):
#   fl_suffix                              -> 7-char [0-9a-z]
#   fl_branch <loop>                       -> "FL-<loop>-<suffix>"
#   preflight <base> <runDir>              -> collects ALL failures; rc!=0 on any
#   detect_verify [<dir>]                  -> prints detected verify commands (one/line); rc 0 if any; <dir> default '.'
#   fl_run_with_timeout <secs> -- <cmd...> -> run argv with a wall-clock watchdog; 124 == timed out
#   fl_verify_sandbox_exec <cmd...>        -> run argv through the selected sandbox; fail closed if unavailable
#   run_verify                             -> reads commands on stdin or detects; fail-FAST; real rc
#   commit_and_push <branch> <base> <msg>  -> commit (guarded) + push -u; rc propagated
#   adopt_winner_branch <flBranch> <base> <winnerWorktreeBranch>
#                                          -> alias <flBranch> to the winner's EXACT commit (no new
#                                             commit/re-author) + push -u; rc propagated (repo-anchored)
#   open_pr <branch> <base> <title> <bodyFile>            -> normal PR; prints URL
#   open_pr_needs_human <branch> <base> <title> <bodyFile> -> draft + needs-human PR; prints URL
#   stop_file_check <runDir>               -> rc 0 if STOP present (caller halts), rc 1 otherwise
#   done_marker <runDir> <loop> [write]    -> check/write per-loop DONE marker
#
set -uo pipefail

# Cap on verify output appended to a PR body so a huge log can't blow the PR
# body limit. tail -c keeps the most-recent (usually most-relevant) bytes.
FL_VERIFY_TAIL_BYTES="${FL_VERIFY_TAIL_BYTES:-12000}"
FL_NEEDS_HUMAN_LABEL="${FL_NEEDS_HUMAN_LABEL:-needs-human}"

# Per-command wall-clock budget for run_verify. macOS has no `timeout`/`gtimeout`,
# so each verify command runs under fl_run_with_timeout (below). A command that
# overruns is killed (TERM->KILL) and reported as rc 124 (GNU-timeout-compatible),
# which run_verify treats as a normal verify FAIL. Overridable (tests use a tiny value).
FL_VERIFY_CMD_TIMEOUT="${FL_VERIFY_CMD_TIMEOUT:-600}"

# Sandboxed verify is deliberately DEFAULT OFF. Only the Phase-7 driver may set
# FL_VERIFY_SANDBOX=1, inline, after the nested audit cleared the exact diff.
# FL_VERIFY_SANDBOX_WRAPPER is an optional operator hook for a container/VM
# launcher. It must name one executable which accepts:
#
#   wrapper -- <verify-command> <arg>...
#
# When unset, fl_verify_sandbox_exec uses the macOS sandbox-exec reference
# profile below. Missing/invalid wrappers fail closed; there is no unsandboxed
# fallback while FL_VERIFY_SANDBOX=1.

# --------------------------------------------------------------------------
# fl_suffix — 7 chars from [0-9a-z], macOS-portable, /dev/urandom only.
# LC_ALL=C so tr treats bytes as bytes; head -c 7 caps it; trailing newline.
# --------------------------------------------------------------------------
fl_suffix() {
  LC_ALL=C tr -dc '0-9a-z' < /dev/urandom | head -c 7
  echo
}

# fl_branch <loop> -> FL-<loop>-<suffix>. Overrides the global rob/ prefix for
# loop branches only (the SKILL says so explicitly).
fl_branch() {
  local k="${1:?loop number required}"
  echo "FL-${k}-$(fl_suffix)"
}

# --------------------------------------------------------------------------
# detect_verify [<dir>] — scan a repo tree and print the verify commands we
# WOULD run, one per line (the driver runs them later via run_verify). Records,
# does not run. Prints nothing and returns rc 1 if no verify commands can be
# detected (the SKILL then opens a draft needs-human PR — we could not verify).
#
# <dir> (optional, default '.') is the tree to DETECT against — so the driver can
# freeze the command set from the WINNER'S WORKTREE at gate time (plan §9.2),
# which may have added a test suite the base tree lacked. Only the FILE-PRESENCE
# and CONTENT-GREP probes follow <dir>; tool-availability checks (command -v /
# `python3 -c import pytest`) and the EMITTED command strings are unchanged —
# they are host/run-time properties, evaluated later by run_verify FROM INSIDE
# the tree, so they must not be path-qualified. With no arg, behavior is
# byte-identical to before ('.' prefix is observationally inert for -f and for a
# single-named-file grep).
#
# Order is fail-fast-friendly: build/typecheck before test before lint.
# --------------------------------------------------------------------------
detect_verify() {
  local d="${1:-.}"
  local found=0

  # Node / JS: package.json scripts. Only emit scripts that actually exist.
  if [ -f "$d/package.json" ]; then
    local has
    for s in build typecheck test lint; do
      # crude but dependency-free: does a "<s>": key exist in scripts?
      if grep -Eq "\"${s}\"[[:space:]]*:" "$d/package.json"; then
        echo "npm run ${s} --if-present"
        found=1
      fi
    done
  fi

  # Python: pyproject.toml + pytest / ruff.
  if [ -f "$d/pyproject.toml" ] || [ -f "$d/setup.cfg" ] || [ -f "$d/tox.ini" ]; then
    if command -v ruff >/dev/null 2>&1; then echo "ruff check ."; found=1; fi
    if command -v pytest >/dev/null 2>&1; then echo "pytest -q"; found=1
    elif command -v python3 >/dev/null 2>&1 && python3 -c 'import pytest' >/dev/null 2>&1; then
      echo "python3 -m pytest -q"; found=1
    fi
  fi

  # Makefile: test / check targets.
  if [ -f "$d/Makefile" ] || [ -f "$d/makefile" ]; then
    local mf="$d/Makefile"; [ -f "$d/Makefile" ] || mf="$d/makefile"
    if grep -Eq '^test[[:space:]]*:' "$mf"; then echo "make test"; found=1; fi
    if grep -Eq '^check[[:space:]]*:' "$mf"; then echo "make check"; found=1; fi
  fi

  # Rust: cargo.
  if [ -f "$d/Cargo.toml" ] && command -v cargo >/dev/null 2>&1; then
    echo "cargo build"
    echo "cargo test"
    found=1
  fi

  # Go.
  if [ -f "$d/go.mod" ] && command -v go >/dev/null 2>&1; then
    echo "go build ./..."
    echo "go test ./..."
    found=1
  fi

  [ "$found" -eq 1 ] && return 0 || return 1
}

# --------------------------------------------------------------------------
# verify_safe_diff — SECURITY GATE for the unattended verify step (issue #21).
#
# The implementer leaves its changes UNSTAGED in the work tree. A verify command
# like `make test` / `npm run build` / `pytest` does not just run fixed code: it
# executes the *body* of the recipe/script/conftest the implementer just wrote
# from an LLM-authored proposal. So before run_verify executes ANYTHING, refuse
# if the implementer's changes touch any file whose CONTENTS a toolchain would
# execute. Those changes must be reviewed by a human (draft+needs-human) instead
# of auto-run with the operator's credentials.
#
# Inspects modified (unstaged + staged) AND new untracked files. rc 0 == safe
# (nothing executable touched), rc 1 == unsafe (prints the offending files). When
# FL_VERIFY_SANDBOX=1, an unsafe hit is reported as accepted for sandbox routing
# and returns 0; run_verify then MUST route every command through the sandbox
# leaf. With the flag unset/0, behavior is byte-identical to issue #21. When not
# inside a git work tree there is no implementer diff to gate, so rc 0.
# --------------------------------------------------------------------------
verify_safe_diff() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
  local -a changed=() hits=()
  local f
  while IFS= read -r f; do
    [ -n "$f" ] && changed+=("$f")
  done < <(
    {
      git diff --name-only 2>/dev/null
      git diff --cached --name-only 2>/dev/null
      git ls-files --others --exclude-standard 2>/dev/null
    } | sort -u
  )
  [ "${#changed[@]}" -gt 0 ] || return 0   # clean tree: nothing to gate (avoids empty-array nounset)
  for f in "${changed[@]}"; do
    case "$f" in
      # npm scripts can run anything; make recipes; python build/test config and
      # pytest-autoloaded conftest; rust build hooks; go module/tests; CI & hooks;
      # and the test sources the test runners EXECUTE.
      package.json|*/package.json|\
      Makefile|makefile|GNUmakefile|*/Makefile|*/makefile|*/GNUmakefile|*.mk|\
      pyproject.toml|*/pyproject.toml|setup.py|*/setup.py|setup.cfg|*/setup.cfg|\
      tox.ini|*/tox.ini|conftest.py|*/conftest.py|\
      Cargo.toml|*/Cargo.toml|build.rs|*/build.rs|\
      go.mod|*/go.mod|\
      test_*.py|*/test_*.py|*_test.py|*/*_test.py|\
      *_test.go|*/*_test.go|\
      .github/workflows/*|.gitlab-ci.yml|*/.gitlab-ci.yml|.git/hooks/*|*/.git/hooks/*)
        hits+=("$f") ;;
    esac
  done
  if [ "${#hits[@]}" -gt 0 ]; then
    if [ "${FL_VERIFY_SANDBOX:-0}" = "1" ]; then
      echo "FL-VERIFY-SANDBOX-ROUTE: verify-executable file(s) accepted only for sandboxed verify:" >&2
      for f in "${hits[@]}"; do echo "  - $f" >&2; done
      return 0
    fi
    # DEFAULT-OFF PATH: keep the issue-#21 output and return code exactly as
    # before P6.
    echo "FL-VERIFY-REFUSE-UNSAFE: implementer change touches verify-executable file(s); a human must review before local verify runs:" >&2
    for f in "${hits[@]}"; do echo "  - $f" >&2; done
    return 1
  fi
  return 0
}

# --------------------------------------------------------------------------
# fl_verify_sandbox_exec <cmd argv...>
# Sandbox LEAF for run_verify. The timeout remains the outer layer so a hung
# wrapper/container is killed by the existing watchdog.
#
# Operator hook: FL_VERIFY_SANDBOX_WRAPPER names one trusted executable which
# receives `--` followed by the untouched verify argv. It is responsible for
# enforcing the environment's no-network/no-operator-credentials invariant and
# for executing the current worktree (the audit-cleared candidate).
#
# Default: macOS sandbox-exec reference profile. It denies network and reads of
# common operator credential paths. Paths are passed as sandbox parameters;
# sandbox profile text does not expand shell variables. The profile otherwise
# allows filesystem access required by project toolchains. Existing run_verify
# secret-drop remains mandatory and happens before this function is called.
#
# rc 125 means the selected sandbox is unavailable. Never run argv unsandboxed.
# --------------------------------------------------------------------------
fl_verify_sandbox_exec() {
  [ "$#" -gt 0 ] || { echo "FL-VERIFY-SANDBOX-FAIL: no command given" >&2; return 125; }

  local requested="${FL_VERIFY_SANDBOX_WRAPPER:-}"
  local sandbox_bin=""
  if [ -n "$requested" ]; then
    sandbox_bin="$(command -v "$requested" 2>/dev/null || true)"
    if [ -z "$sandbox_bin" ]; then
      echo "FL-VERIFY-SANDBOX-UNAVAILABLE: wrapper '$requested' not found or not executable (fail-closed)" >&2
      return 125
    fi
    "$sandbox_bin" -- "$@"
    return $?
  fi

  sandbox_bin="$(command -v sandbox-exec 2>/dev/null || true)"
  if [ -z "$sandbox_bin" ]; then
    echo "FL-VERIFY-SANDBOX-UNAVAILABLE: sandbox-exec not found and FL_VERIFY_SANDBOX_WRAPPER is unset (fail-closed)" >&2
    return 125
  fi

  local home="${HOME:-/var/empty}"
  local profile='(version 1)
(allow default)
(deny network*)
(deny file-read*
  (subpath (param "FL_SSH_DIR"))
  (subpath (param "FL_AWS_DIR"))
  (subpath (param "FL_AZURE_DIR"))
  (subpath (param "FL_GCLOUD_DIR"))
  (subpath (param "FL_GH_DIR"))
  (subpath (param "FL_DOCKER_DIR"))
  (subpath (param "FL_KUBE_DIR"))
  (subpath (param "FL_CODEX_DIR"))
  (subpath (param "FL_CLAUDE_DIR"))
  (subpath (param "FL_GROK_DIR"))
  (subpath (param "FL_KEYCHAINS_DIR"))
  (literal (param "FL_NPMRC"))
  (literal (param "FL_PYPIRC"))
  (literal (param "FL_NETRC"))
  (literal (param "FL_GIT_CREDS")))'

  "$sandbox_bin" \
    -D FL_SSH_DIR="$home/.ssh" \
    -D FL_AWS_DIR="$home/.aws" \
    -D FL_AZURE_DIR="$home/.azure" \
    -D FL_GCLOUD_DIR="$home/.config/gcloud" \
    -D FL_GH_DIR="$home/.config/gh" \
    -D FL_DOCKER_DIR="$home/.docker" \
    -D FL_KUBE_DIR="$home/.kube" \
    -D FL_CODEX_DIR="$home/.codex" \
    -D FL_CLAUDE_DIR="$home/.claude" \
    -D FL_GROK_DIR="$home/.grok" \
    -D FL_KEYCHAINS_DIR="$home/Library/Keychains" \
    -D FL_NPMRC="$home/.npmrc" \
    -D FL_PYPIRC="$home/.pypirc" \
    -D FL_NETRC="$home/.netrc" \
    -D FL_GIT_CREDS="$home/.git-credentials" \
    -p "$profile" \
    "$@"
}

# --------------------------------------------------------------------------
# fl_run_with_timeout <secs> -- <cmd argv...>
# Run a command (as an argv vector — no eval) under a wall-clock watchdog.
# macOS-portable: NO `timeout`/`gtimeout`, pure bash 3.2 job control.
#
# Contract (GNU-timeout-compatible):
#   - returns the command's REAL exit status when it finishes on its own;
#   - if the command overruns <secs>, it is sent SIGTERM, then SIGKILL after a
#     short grace, and the result is normalised to rc 124 ("timed out") so the
#     caller can distinguish a timeout from a genuine nonzero exit;
#   - reaps BOTH the command AND the watchdog (and the watchdog's own sleep) so
#     no background process leaks — including on the common EARLY-COMPLETION path
#     where the command finishes well under the timeout and the watchdog is torn
#     down mid-sleep (a naive `( sleep N; kill ) &` orphans that sleep to init).
# NOTE: a sub-~10ms command has a benign residual orphan-sleep race (the parent
#   can tear the watchdog down before its TERM trap is installed) — out of scope;
#   real verify commands (node/bash/pytest) are >=50ms and never leak.
# Usage: fl_run_with_timeout 600 -- npm run build --if-present
# --------------------------------------------------------------------------
FL_VERIFY_KILL_GRACE="${FL_VERIFY_KILL_GRACE:-2}"
fl_run_with_timeout() {
  local secs="${1:?timeout seconds required}"; shift
  [ "${1:-}" = "--" ] && shift
  [ "$#" -gt 0 ] || { echo "FL-TIMEOUT: no command given" >&2; return 2; }

  # Run the verify command in the background.
  "$@" &
  local cmd_pid=$!

  # Watchdog: background ITS OWN sleep separately and remember that sleep's PID,
  # so tearing the watchdog down also stops the sleep (no orphaned sleep on the
  # fast-success path). The grace sleep is short and inline (only reached when the
  # timeout has already fired, i.e. the leak window does not exist there).
  ( sleep "$secs" &
    local sleep_pid=$!
    # When the watchdog is killed early (command finished first), reap the sleep
    # too, then exit without touching the (already-gone) command.
    trap 'kill "$sleep_pid" 2>/dev/null; exit 0' TERM
    wait "$sleep_pid" 2>/dev/null
    # Timeout fired: escalate TERM -> (grace) -> KILL on the command.
    kill -TERM "$cmd_pid" 2>/dev/null
    sleep "$FL_VERIFY_KILL_GRACE"
    kill -KILL "$cmd_pid" 2>/dev/null ) &
  local watch_pid=$!

  # Wait for the command; capture its REAL rc.
  wait "$cmd_pid" 2>/dev/null; local rc=$?

  # Tear down the watchdog (and, via its TERM trap, its sleep) and reap it so it
  # never leaks regardless of which side won the race.
  kill -TERM "$watch_pid" 2>/dev/null
  wait "$watch_pid" 2>/dev/null

  # A signal-coded result (>=128) means the watchdog killed it -> normalise to the
  # GNU-timeout code. Genuine nonzero exits (<128) pass through untouched.
  if [ "$rc" -ge 128 ]; then rc=124; fi
  return "$rc"
}

# --------------------------------------------------------------------------
# run_verify — run the FROZEN verify commands FAIL-CLOSED and FAIL-FAST.
# Commands come from stdin (one per line). The set is frozen at preflight and
# piped in by the driver; run_verify NEVER re-detects on the (implementer-mutated)
# tree — see issue #21.
# CONTRACT (the crown jewel):
#   (a) returns a real NONZERO status on ANY failing command;
#   (b) breaks on the FIRST failure (fail-fast);
#   (c) NEVER lets a later command's success mask an earlier failure.
# We capture each command's rc DIRECTLY with `if cmd; then ... else rc=$?; break`.
# We do NOT pipe through tee/grep to recover rc (tee masks rc; a later exit=0 in a
# combined log would mask an earlier failure). All output goes to stdout/stderr so
# the caller can `> verify.log 2>&1` it.
#
# Hardening (issue #21 — unattended verify-time RCE):
#   - GATE: refuse (rc 1) if the implementer's changes touch a verify-executable
#     file (verify_safe_diff) — that is the path by which a proposal smuggles code
#     into `make test`/`npm run`/`pytest`.
#   - SECRET-DROP: unset provider credentials so a verify command can neither read
#     nor exfiltrate them (gh/git auth is used by OTHER helper calls, in separate
#     processes — not here).
#   - NO LIVE RE-DETECT: empty stdin -> rc 2 (unverifiable), never re-scan a tree
#     the implementer just mutated.
#   - ARGV EXEC: run each command as a word-split argv vector, NOT via `eval`, so
#     `;`/`|`/`$()`/backticks in a command line are inert literal args.
#
# rc 0  -> all passed
# rc 1  -> a command failed, OR the gate refused (caller -> draft needs-human PR)
# rc 2  -> no (frozen) verify commands provided (caller -> draft needs-human PR)
# --------------------------------------------------------------------------
run_verify() {
  # GATE first: never execute anything when the implementer touched executable code.
  if ! verify_safe_diff; then
    echo "FL-VERIFY-HALT: refusing to run verify on implementer-authored executable changes (fail-closed)" >&2
    return 1
  fi

  # SECRET-DROP: strip credentials from this process (and thus every command it runs).
  unset ZAI_API_KEY MINIMAX_API_KEY OMLX_AUTH_TOKEN OPENAI_API_KEY \
        ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN GH_TOKEN GITHUB_TOKEN 2>/dev/null || true

  local -a cmds=()
  if [ ! -t 0 ]; then
    # read the FROZEN commands from stdin (one per line)
    while IFS= read -r line; do
      [ -n "$line" ] && cmds+=("$line")
    done
  fi

  # NO LIVE RE-DETECT: an empty frozen set is "unverifiable", not "go scan the
  # (mutated) tree and run whatever you find".
  if [ "${#cmds[@]}" -eq 0 ]; then
    echo "FL-VERIFY: no verify commands provided on stdin (frozen set empty; not re-detecting a mutated tree)" >&2
    return 2
  fi

  local rc=0 c
  local -a words
  for c in "${cmds[@]}"; do
    echo "FL-VERIFY-RUN: $c"
    # ARGV EXEC: split on whitespace and run as a vector — no `eval`, so shell
    # metacharacters are inert. (The frozen verify commands are simple argv.)
    words=()
    read -r -a words <<< "$c"
    [ "${#words[@]}" -gt 0 ] || continue
    # Direct rc capture; break on first failure so a later success cannot mask it.
    # Per-command wall-clock watchdog (macOS has no `timeout`); a 124 (timed out)
    # is a nonzero rc and so is handled by the existing fail path below, as a FAIL.
    if [ "${FL_VERIFY_SANDBOX:-0}" = "1" ]; then
      # Timeout OUTSIDE, sandbox at the LEAF. The wrapper receives argv, not a
      # shell string. Missing wrapper/profile returns nonzero before argv runs.
      if fl_run_with_timeout "$FL_VERIFY_CMD_TIMEOUT" -- fl_verify_sandbox_exec "${words[@]}"; then
        echo "FL-VERIFY-OK: $c"
      else
        rc=$?
        echo "FL-VERIFY-FAIL: $c (exit $rc)" >&2
        break
      fi
    else
      # DEFAULT-OFF PATH: intentionally identical to pre-P6 execution.
      if fl_run_with_timeout "$FL_VERIFY_CMD_TIMEOUT" -- "${words[@]}"; then
        echo "FL-VERIFY-OK: $c"
      else
        rc=$?
        echo "FL-VERIFY-FAIL: $c (exit $rc)" >&2
        break
      fi
    fi
  done

  if [ "$rc" -eq 0 ]; then
    echo "FL-VERIFY-ALL-PASS"
  else
    echo "FL-VERIFY-HALT: chain should stop (fail-closed)" >&2
    # Normalise to 1 so the caller's `if run_verify` test is simple, but it is
    # genuinely nonzero (never masked).
    return 1
  fi
  return 0
}

# --------------------------------------------------------------------------
# preflight <base> <runDir>
# Zero-token gate run ONCE before loop 1. Collects ALL failures (does not bail on
# the first) and prints them, then returns rc = number-of-failures capped to 1
# (rc 0 == all good, rc 1 == one or more failures). Resolves the remote from the
# base branch's actual upstream, with an origin fallback.
# --------------------------------------------------------------------------
preflight() {
  local base="${1:?base branch required}"
  local runDir="${2:-.}"
  local -a fails=()

  # inside a git work tree?
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fails+=("not inside a git work tree (run from the repo root)")
  fi

  # working tree clean? (refuse on dirty — never auto-stash unrelated work)
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    fails+=("working tree is dirty — commit/stash your changes first (refusing to risk committing unrelated work)")
  fi

  # gh authenticated?
  if ! command -v gh >/dev/null 2>&1; then
    fails+=("gh CLI not found on PATH")
  elif ! gh auth status >/dev/null 2>&1; then
    fails+=("gh is not authenticated (run: gh auth login)")
  fi

  # a remote exists? prefer the base branch's upstream remote, fall back to origin.
  local remote=""
  remote="$(fl_resolve_remote "$base")"
  if [ -z "$remote" ]; then
    fails+=("no git remote resolvable (base upstream nor 'origin' has a URL)")
  fi

  # base branch resolves?
  if ! git rev-parse --verify --quiet "$base" >/dev/null 2>&1; then
    fails+=("base branch '$base' does not resolve (git rev-parse --verify failed)")
  fi

  # verify commands detected? (record only; missing -> draft needs-human PR later,
  # so this is a WARNING, not a hard fail.)
  if detect_verify >/dev/null 2>&1; then
    : # detected
  else
    echo "FL-PREFLIGHT-WARN: no verify commands auto-detected; PRs will be draft+${FL_NEEDS_HUMAN_LABEL}" >&2
  fi

  if [ "${#fails[@]}" -gt 0 ]; then
    echo "FL-PREFLIGHT-FAIL (${#fails[@]} problem(s)):" >&2
    local f
    for f in "${fails[@]}"; do echo "  - $f" >&2; done
    return 1
  fi
  echo "FL-PREFLIGHT-OK base=$base remote=$remote runDir=$runDir"
  return 0
}

# fl_resolve_remote <base> -> prints the remote name to push to, or empty.
# Prefers the base branch's configured upstream remote; falls back to origin if it
# has a URL.
fl_resolve_remote() {
  local base="${1:-}"
  local up rem=""
  # base@{upstream} -> e.g. "origin/main"; take the part before the first /.
  up="$(git rev-parse --abbrev-ref --symbolic-full-name "${base}@{upstream}" 2>/dev/null || true)"
  if [ -n "$up" ]; then
    rem="${up%%/*}"
  fi
  if [ -n "$rem" ] && git remote get-url "$rem" >/dev/null 2>&1; then
    echo "$rem"; return 0
  fi
  if git remote get-url origin >/dev/null 2>&1; then
    echo "origin"; return 0
  fi
  echo ""
  return 1
}

# --------------------------------------------------------------------------
# commit_and_push <branch> <base> <message>
# Guarded commit: only commits when HEAD is the expected FL- branch AND the diff
# (against the index AND the worktree) is non-empty. The implementer leaves
# changes UNSTAGED, so we `git add -A` here. Then push -u to the resolved remote.
# rc propagated on any git failure.
# --------------------------------------------------------------------------
commit_and_push() {
  local branch="${1:?branch required}"
  local base="${2:?base required}"
  local msg="${3:?commit message required}"

  # Guard: HEAD must be the expected FL- branch (never commit on base/main).
  local cur
  cur="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  if [ "$cur" != "$branch" ]; then
    echo "FL-COMMIT-REFUSE: HEAD is '$cur', expected '$branch' (refusing to commit on the wrong branch)" >&2
    return 2
  fi
  case "$branch" in
    FL-*) : ;;
    *) echo "FL-COMMIT-REFUSE: branch '$branch' is not an FL- branch (refusing)" >&2; return 2 ;;
  esac

  # Guard: there must be something to commit.
  git add -A || { echo "FL-COMMIT-FAIL: git add failed" >&2; return 1; }
  if git diff --cached --quiet; then
    echo "FL-COMMIT-REFUSE: empty diff after staging (nothing to commit)" >&2
    return 3
  fi

  if ! git commit -m "$msg"; then
    echo "FL-COMMIT-FAIL: git commit failed" >&2
    return 1
  fi

  local remote
  remote="$(fl_resolve_remote "$base")"
  if [ -z "$remote" ]; then
    echo "FL-PUSH-FAIL: no remote resolvable" >&2
    return 1
  fi
  if ! git push -u "$remote" "$branch"; then
    echo "FL-PUSH-FAIL: git push -u $remote $branch failed" >&2
    return 1
  fi
  echo "FL-COMMIT-PUSH-OK branch=$branch remote=$remote"
  return 0
}

# --------------------------------------------------------------------------
# adopt_winner_branch <flBranch> <base> <winnerWorktreeBranch>
# REPO-ANCHORED adoption (plan §7/§11). The winning attempt already produced a
# real, GATED commit on its own worktree branch <winnerWorktreeBranch> (P1 made
# the commit; the P3 verify+audit gate cleared it BEFORE this is ever called).
# Adoption is a PURE REF ALIAS of that exact commit:
#
#     git branch <flBranch> <winnerWorktreeBranch>
#
# This creates <flBranch> pointing at the WINNER'S EXACT commit object — no new
# commit, no re-author/squash/cherry-pick — so the commit a human reviews/merges
# is byte-for-byte the commit that was verified+audited ("validated ref == merged
# ref", §11). Then push -u to the resolved remote.
#
# This is a SIBLING of commit_and_push, NOT a reuse of it: commit_and_push assumes
# an UNSTAGED implementer diff it `git add -A`/commits (and refuses an empty diff),
# which would either refuse here (nothing staged) or mint a NEW sha and break the
# invariant. commit_and_push is left untouched for the legacy (repoMode:false) path.
#
# Guards mirror commit_and_push (FL-* prefix, fl_resolve_remote, rc-propagation,
# fail-closed). There is deliberately NO HEAD guard: we create <flBranch> fresh
# from the winner's commit and never switch to it, so HEAD is irrelevant here.
#
# rc 0  -> aliased + pushed
# rc 2  -> refused: <flBranch> is not an FL- branch, or the winner branch is missing
# rc 1  -> a git/gh step failed (branch create, remote resolve, or push)
# --------------------------------------------------------------------------
adopt_winner_branch() {
  local branch="${1:?fl branch required}"
  local base="${2:?base required}"
  local winner="${3:?winner worktree branch required}"

  # Guard: the adopted branch MUST be an FL- branch (mirrors commit_and_push's
  # guard; the SKILL hard-requires the prefix). Refuse anything else, fail-closed.
  case "$branch" in
    FL-*) : ;;
    *) echo "FL-ADOPT-REFUSE: branch '$branch' is not an FL- branch (refusing)" >&2; return 2 ;;
  esac

  # Guard: the winner's commit must actually exist (resolve the start-point) before
  # we create anything — fail-closed instead of creating a dangling/empty branch.
  if ! git rev-parse --verify --quiet "${winner}^{commit}" >/dev/null 2>&1; then
    echo "FL-ADOPT-REFUSE: winner branch '$winner' does not resolve to a commit (refusing)" >&2
    return 2
  fi

  # Guard: do not clobber an existing FL- branch (an adoption must be a clean
  # create; a pre-existing branch means a half-applied/duplicate loop — fail-closed).
  if git rev-parse --verify --quiet "refs/heads/${branch}" >/dev/null 2>&1; then
    echo "FL-ADOPT-REFUSE: branch '$branch' already exists (refusing to clobber)" >&2
    return 2
  fi

  # PURE REF ALIAS: <flBranch> = the winner's EXACT commit. No new sha, no re-author.
  if ! git branch "$branch" "$winner"; then
    echo "FL-ADOPT-FAIL: git branch '$branch' '$winner' failed" >&2
    return 1
  fi

  local remote
  remote="$(fl_resolve_remote "$base")"
  if [ -z "$remote" ]; then
    echo "FL-PUSH-FAIL: no remote resolvable" >&2
    return 1
  fi
  if ! git push -u "$remote" "$branch"; then
    echo "FL-PUSH-FAIL: git push -u $remote $branch failed" >&2
    return 1
  fi
  echo "FL-ADOPT-PUSH-OK branch=$branch winner=$winner remote=$remote"
  return 0
}

# --------------------------------------------------------------------------
# _ensure_label — idempotently create the needs-human label. If creation fails
# (no permission, etc.) we return nonzero so the caller can fall back to a
# label-less draft PR rather than failing the whole loop.
# --------------------------------------------------------------------------
_ensure_label() {
  local label="${1:-$FL_NEEDS_HUMAN_LABEL}"
  # Already exists?
  if gh label list --limit 200 2>/dev/null | grep -qiE "^${label}([[:space:]]|$)"; then
    return 0
  fi
  # Create (idempotent: --force updates if it raced into existence).
  if gh label create "$label" --color "B60205" --description "Farnsworth Loop: needs human review (verify failed or unverifiable)" --force >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

# --------------------------------------------------------------------------
# open_pr <branch> <base> <title> <bodyFile>
# Normal (non-draft) PR. Body is read from a file (portable mktemp composed by
# the caller). Prints the PR URL on success. rc propagated.
# --------------------------------------------------------------------------
open_pr() {
  local branch="${1:?branch required}"
  local base="${2:?base required}"
  local title="${3:?title required}"
  local bodyFile="${4:?body file required}"
  [ -f "$bodyFile" ] || { echo "FL-PR-FAIL: body file '$bodyFile' missing" >&2; return 1; }

  local url
  if url="$(gh pr create --base "$base" --head "$branch" --title "$title" --body-file "$bodyFile" 2>&1)"; then
    echo "$url" | tail -1
    return 0
  fi
  echo "FL-PR-FAIL: gh pr create failed: $url" >&2
  return 1
}

# --------------------------------------------------------------------------
# open_pr_needs_human <branch> <base> <title> <bodyFile>
# DRAFT PR labelled needs-human (verify failed, or could not verify). The body
# file should already contain the (capped) failing verify output — the caller
# composes it; see fl_compose_body / fl_append_verify_tail below. Creates the
# label idempotently; on label failure falls back to a label-LESS draft PR (the
# draft + body still convey "needs human"). Prints URL; rc propagated.
# --------------------------------------------------------------------------
open_pr_needs_human() {
  local branch="${1:?branch required}"
  local base="${2:?base required}"
  local title="${3:?title required}"
  local bodyFile="${4:?body file required}"
  [ -f "$bodyFile" ] || { echo "FL-PR-FAIL: body file '$bodyFile' missing" >&2; return 1; }

  local labelArgs=()
  if _ensure_label "$FL_NEEDS_HUMAN_LABEL"; then
    labelArgs=(--label "$FL_NEEDS_HUMAN_LABEL")
  else
    echo "FL-PR-WARN: could not create/find label '$FL_NEEDS_HUMAN_LABEL'; opening label-less draft" >&2
  fi

  local url
  if url="$(gh pr create --draft "${labelArgs[@]}" --base "$base" --head "$branch" --title "$title" --body-file "$bodyFile" 2>&1)"; then
    echo "$url" | tail -1
    return 0
  fi
  # If the failure was the label, retry once without it (label-less draft fallback).
  if [ "${#labelArgs[@]}" -gt 0 ]; then
    echo "FL-PR-WARN: draft+label create failed, retrying label-less: $url" >&2
    if url="$(gh pr create --draft --base "$base" --head "$branch" --title "$title" --body-file "$bodyFile" 2>&1)"; then
      echo "$url" | tail -1
      return 0
    fi
  fi
  echo "FL-PR-FAIL: gh pr create --draft failed: $url" >&2
  return 1
}

# --------------------------------------------------------------------------
# fl_compose_body <outFile> -- writes the body file from stdin (a here-doc the
# caller pipes in). A convenience so the SKILL can compose in a portable mktemp.
# Usage:  fl_compose_body /tmp/body.md <<'EOF' ... EOF
# --------------------------------------------------------------------------
fl_compose_body() {
  local out="${1:?out file required}"
  cat > "$out"
}

# fl_append_verify_tail <bodyFile> <verifyLogFile>
# Appends a capped tail of the verify log to the PR body inside a fenced block,
# so a huge log cannot blow the PR body limit. Safe if the log is missing.
fl_append_verify_tail() {
  local body="${1:?body file required}"
  local vlog="${2:?verify log required}"
  {
    echo
    echo '### Verify output (tail)'
    echo '```'
    if [ -f "$vlog" ]; then
      tail -c "$FL_VERIFY_TAIL_BYTES" "$vlog"
    else
      echo "(verify log not found: $vlog)"
    fi
    echo '```'
  } >> "$body"
}

# --------------------------------------------------------------------------
# stop_file_check <runDir>
# Between-loops kill switch. rc 0 (success) when a STOP file EXISTS — the caller
# treats rc 0 as "halt now". rc 1 when absent (keep going). This is the inverse
# of the usual convention but matches the caller pattern
#   `if stop_file_check "$runDir"; then halt; fi`.
# --------------------------------------------------------------------------
stop_file_check() {
  local runDir="${1:?runDir required}"
  if [ -e "${runDir}/STOP" ]; then
    echo "FL-STOP: kill-switch file present at ${runDir}/STOP — halting before next loop"
    return 0
  fi
  return 1
}

# --------------------------------------------------------------------------
# done_marker <runDir> <loop> [write]
# Per-loop idempotency. Without 'write': rc 0 if the loop's DONE marker exists
# (caller skips the loop), rc 1 otherwise. With 'write' as 3rd arg: create the
# marker (call ONLY after the PR is created). Marker lives at
# <runDir>/loop-<loop>/DONE.
# --------------------------------------------------------------------------
done_marker() {
  local runDir="${1:?runDir required}"
  local k="${2:?loop number required}"
  local mode="${3:-check}"
  local marker="${runDir}/loop-${k}/DONE"
  if [ "$mode" = "write" ]; then
    mkdir -p "${runDir}/loop-${k}" || return 1
    {
      echo "loop=${k}"
      echo "ts=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
      [ -n "${2:-}" ] && true
    } > "$marker" || return 1
    echo "FL-DONE-WRITTEN ${marker}"
    return 0
  fi
  if [ -e "$marker" ]; then
    echo "FL-DONE-EXISTS ${marker}"
    return 0
  fi
  return 1
}

# fl_detect_orphan_branch <loop>
# Re-entry safety: detect a half-applied FL-<loop>-* branch with NO DONE marker
# (a mid-loop death). Prints the branch name(s) if any; caller tells the human to
# inspect/delete rather than auto-resuming. (detect-and-stop, never auto-resume.)
fl_detect_orphan_branch() {
  local k="${1:?loop number required}"
  git branch --list "FL-${k}-*" --format '%(refname:short)' 2>/dev/null
}

# --------------------------------------------------------------------------
# CLI dispatcher (the benign-command pattern, like glm-run.sh). Lets the SKILL
# call `bash fl-git.sh <fn> args...` without sourcing.
# --------------------------------------------------------------------------
# Only dispatch when executed directly, not when sourced.
_fl_is_sourced() {
  # bash: ${BASH_SOURCE[0]} != $0 when sourced.
  [ "${BASH_SOURCE[0]:-}" != "${0:-}" ]
}

if ! _fl_is_sourced; then
  cmd="${1:-}"
  shift || true
  case "$cmd" in
    fl_suffix)             fl_suffix ;;
    fl_branch)             fl_branch "$@" ;;
    preflight)             preflight "$@" ;;
    detect_verify)         detect_verify "$@" ;;
    verify_safe_diff)      verify_safe_diff "$@" ;;
    fl_run_with_timeout)   fl_run_with_timeout "$@" ;;
    fl_verify_sandbox_exec) fl_verify_sandbox_exec "$@" ;;
    run_verify)            run_verify "$@" ;;
    commit_and_push)       commit_and_push "$@" ;;
    adopt_winner_branch)   adopt_winner_branch "$@" ;;
    open_pr)               open_pr "$@" ;;
    open_pr_needs_human)   open_pr_needs_human "$@" ;;
    fl_compose_body)       fl_compose_body "$@" ;;
    fl_append_verify_tail) fl_append_verify_tail "$@" ;;
    stop_file_check)       stop_file_check "$@" ;;
    done_marker)           done_marker "$@" ;;
    fl_resolve_remote)     fl_resolve_remote "$@" ;;
    fl_detect_orphan_branch) fl_detect_orphan_branch "$@" ;;
    ""|-h|--help|help)
      cat <<'USAGE'
fl-git.sh — Farnsworth Loop grand-loop git/gh helper.
Usage: bash fl-git.sh <fn> [args...]   (or: source fl-git.sh)
Functions:
  fl_suffix
  fl_branch <loop>
  preflight <base> <runDir>
  detect_verify [<dir>]           (detect against <dir>, default '.'; e.g. a winner worktree)
  verify_safe_diff                (rc 0 safe, rc 1 implementer touched executable file)
  fl_run_with_timeout <secs> -- <cmd...>   (run argv with a wall-clock watchdog; rc 124 == timed out)
  fl_verify_sandbox_exec <cmd...> (run argv through the selected sandbox; rc 125 == sandbox unavailable, fail-closed)
  run_verify                      (FROZEN commands on stdin one/line; gated + secrets dropped)
  commit_and_push <branch> <base> <message>
  adopt_winner_branch <flBranch> <base> <winnerWorktreeBranch>   (repo-anchored: alias FL- branch to winner's EXACT commit + push -u)
  open_pr <branch> <base> <title> <bodyFile>
  open_pr_needs_human <branch> <base> <title> <bodyFile>
  fl_compose_body <outFile>       (body text on stdin)
  fl_append_verify_tail <bodyFile> <verifyLogFile>
  stop_file_check <runDir>        (rc 0 == STOP present == halt)
  done_marker <runDir> <loop> [write]
  fl_resolve_remote <base>
  fl_detect_orphan_branch <loop>
USAGE
      ;;
    *)
      echo "fl-git.sh: unknown function '$cmd' (try: bash fl-git.sh help)" >&2
      exit 64
      ;;
  esac
fi
