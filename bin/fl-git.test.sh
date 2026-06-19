#!/usr/bin/env bash
# fl-git.test.sh — tests for bin/fl-git.sh run_verify hardening (issue #21).
#
# Covers the unattended verify-time RCE fix:
#   - diff-gate: refuse verify when the implementer's changes touch a file a
#     toolchain would EXECUTE (package.json / Makefile / conftest.py / …)
#   - secret-drop: provider keys are removed from the verify environment
#   - no live re-detection: empty frozen set -> rc 2, never re-scan a mutated tree
#   - argv execution: command lines run as argv (no `eval`), so `;`/`|`/`$()` are inert
#   - preserved contract: fail-FAST (break on first failure), all-pass rc 0
#
# Self-contained: builds throwaway git repos in mktemp dirs; no network, no toolchains.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLGIT="$HERE/fl-git.sh"

pass=0; fail=0
ok()   { printf '  ok   %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  FAIL %s\n' "$1"; fail=$((fail+1)); }
check(){ # check <desc> <actual> <expected>
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2', want '$3')"; fi
}

# mkrepo <dir> [files...] — init a git repo with an initial commit containing the
# given "path=content" files (content may be empty after '=').
mkrepo() {
  local dir="$1"; shift
  mkdir -p "$dir"
  git -C "$dir" init -q
  git -C "$dir" config user.email t@example.com
  git -C "$dir" config user.name  tester
  git -C "$dir" config commit.gpgsign false
  printf 'hello\n' > "$dir/README.md"
  local f name body
  for f in "$@"; do
    name="${f%%=*}"; body="${f#*=}"
    mkdir -p "$dir/$(dirname "$name")"
    printf '%s' "$body" > "$dir/$name"
  done
  git -C "$dir" add -A
  git -C "$dir" commit -q -m init --no-gpg-sign
}

# rv <repo> <stdin> — run `run_verify` in <repo> with <stdin> piped; echoes rc on
# the last line, full output captured to $RV_OUT.
RV_OUT=""
rv() {
  local repo="$1" input="$2" out rc
  out="$( cd "$repo" && printf '%s' "$input" | bash "$FLGIT" run_verify 2>&1 )"
  rc=$?
  RV_OUT="$out"
  return $rc
}

echo "== fl-git.sh run_verify hardening (#21) =="

# ---------------------------------------------------------------------------
# A) diff-gate REFUSES when the implementer added a verify-executable file, and
#    runs NOTHING (the malicious command never executes).
# ---------------------------------------------------------------------------
A=$(mktemp -d); repo="$A/repo"; mkrepo "$repo"
# implementer "creates" package.json (untracked) — a verify-executable change
printf '{"scripts":{"build":"true"}}' > "$repo/package.json"
proof="$A/PROOF"; rm -f "$proof"
rv "$repo" "touch $proof"$'\n'; rc=$?
[ "$rc" -ne 0 ] && ok "A: refused (rc=$rc nonzero)" || bad "A: expected nonzero rc, got 0"
[ ! -e "$proof" ] && ok "A: malicious command did NOT run" || bad "A: command executed despite unsafe diff"
case "$RV_OUT" in *REFUSE-UNSAFE*package.json*) ok "A: names the offending file";; *) bad "A: missing refuse/package.json marker";; esac
rm -rf "$A"

# ---------------------------------------------------------------------------
# B) diff-gate ALLOWS when only a non-verify file changed; the command runs.
# ---------------------------------------------------------------------------
B=$(mktemp -d); repo="$B/repo"; mkrepo "$repo"
printf 'edited\n' >> "$repo/README.md"   # safe change only
ran="$B/RAN"; rm -f "$ran"
rv "$repo" "touch $ran"$'\n'; rc=$?
check "B: allowed (rc 0)" "$rc" "0"
[ -e "$ran" ] && ok "B: command ran on safe diff" || bad "B: command did not run on safe diff"
rm -rf "$B"

# ---------------------------------------------------------------------------
# C) secret-drop: provider keys are removed from the verify environment.
# ---------------------------------------------------------------------------
C=$(mktemp -d); repo="$C/repo"; mkrepo "$repo"
printf 'edited\n' >> "$repo/README.md"
leak="$C/leak.sh"; keyout="$C/KEYOUT"; rm -f "$keyout"
printf '#!/usr/bin/env bash\necho "${ZAI_API_KEY:-EMPTY}" > "$1"\n' > "$leak"
( cd "$repo" && printf '%s\n' "bash $leak $keyout" | ZAI_API_KEY=secret123 bash "$FLGIT" run_verify ) >/dev/null 2>&1
got="$(cat "$keyout" 2>/dev/null || echo MISSING)"
check "C: ZAI_API_KEY dropped from verify env" "$got" "EMPTY"
rm -rf "$C"

# ---------------------------------------------------------------------------
# D) no live re-detection: empty frozen set -> rc 2, never scans the tree.
#    (committed package.json, clean tree -> gate passes; empty stdin -> rc 2.)
# ---------------------------------------------------------------------------
D=$(mktemp -d); repo="$D/repo"; mkrepo "$repo" 'package.json={"scripts":{"build":"true"}}'
rv "$repo" ""; rc=$?
check "D: empty stdin -> rc 2 (unverifiable)" "$rc" "2"
case "$RV_OUT" in *FL-VERIFY-RUN*) bad "D: re-detected and tried to run a command";; *) ok "D: did not re-detect/run";; esac
rm -rf "$D"

# ---------------------------------------------------------------------------
# G) argv execution: a `;`-chained second command is inert (no eval).
# ---------------------------------------------------------------------------
G=$(mktemp -d); repo="$G/repo"; mkrepo "$repo"
printf 'edited\n' >> "$repo/README.md"
inj="$G/INJECTED"; rm -f "$inj"
rv "$repo" "true; touch $inj"$'\n'
[ ! -e "$inj" ] && ok "G: ;-chained command did NOT execute (argv, not eval)" || bad "G: injected command executed (eval still in use)"
rm -rf "$G"

# ---------------------------------------------------------------------------
# E) fail-FAST preserved: first command fails -> stop, second never runs, rc 1.
# ---------------------------------------------------------------------------
E=$(mktemp -d); repo="$E/repo"; mkrepo "$repo"
printf 'edited\n' >> "$repo/README.md"
snr="$E/SHOULD_NOT_RUN"; rm -f "$snr"
rv "$repo" "false"$'\n'"touch $snr"$'\n'; rc=$?
check "E: failing command -> rc 1" "$rc" "1"
[ ! -e "$snr" ] && ok "E: fail-fast (second command skipped)" || bad "E: second command ran after a failure"
rm -rf "$E"

# ---------------------------------------------------------------------------
# F) all-pass preserved: every command succeeds -> rc 0.
# ---------------------------------------------------------------------------
F=$(mktemp -d); repo="$F/repo"; mkrepo "$repo"
printf 'edited\n' >> "$repo/README.md"
rv "$repo" "true"$'\n'"true"$'\n'; rc=$?
check "F: all-pass -> rc 0" "$rc" "0"
case "$RV_OUT" in *FL-VERIFY-ALL-PASS*) ok "F: reports all-pass";; *) bad "F: missing all-pass marker";; esac
rm -rf "$F"

# ---------------------------------------------------------------------------
# H) gate pattern coverage: each verify-executable file type trips the gate;
#    ordinary deliverables (incl. the implementer's own FL-NOTES.md) do not.
# ---------------------------------------------------------------------------
gate_trips() { # gate_trips <relpath> -> echoes "unsafe"/"safe"
  local rel="$1" d repo
  d=$(mktemp -d); repo="$d/repo"; mkrepo "$repo" >/dev/null 2>&1
  mkdir -p "$repo/$(dirname "$rel")"; printf 'x' > "$repo/$rel"   # untracked new file
  if ( cd "$repo" && bash "$FLGIT" verify_safe_diff >/dev/null 2>&1 ); then echo safe; else echo unsafe; fi
  rm -rf "$d"
}
for u in package.json src/web/package.json Makefile makefile build.mk \
         pyproject.toml conftest.py pkg/conftest.py tests/test_login.py api_test.py \
         Cargo.toml build.rs go.mod .github/workflows/ci.yml; do
  check "H: gate trips on $u" "$(gate_trips "$u")" "unsafe"
done
for s in README.md FL-NOTES.md docs/notes.txt src/app.py main.go util.rs; do
  check "H: gate allows $s" "$(gate_trips "$s")" "safe"
done

# ---------------------------------------------------------------------------
# T) fl_run_with_timeout in isolation: real rc passthrough, timeout->124, and
#    NO leaked background process on the EARLY-COMPLETION path (fast command
#    under a large timeout — where a naive watchdog orphans its sleep).
# ---------------------------------------------------------------------------

# T1: a fast command returns its REAL rc (0). Small timeout so any residual
#     benign orphan is short-lived; watchdog torn down early.
( bash "$FLGIT" fl_run_with_timeout 5 -- true ) >/dev/null 2>&1; rc=$?
check "T1: fast success -> real rc 0" "$rc" "0"

# T2: a fast NONZERO exit passes through unchanged (NOT normalised to 124).
( bash "$FLGIT" fl_run_with_timeout 30 -- sh -c 'exit 7' ) >/dev/null 2>&1; rc=$?
check "T2: fast failure -> real rc 7 (not 124)" "$rc" "7"

# T3: a command that sleeps past a tiny timeout is killed and reported as 124.
( bash "$FLGIT" fl_run_with_timeout 1 -- sleep 30 ) >/dev/null 2>&1; rc=$?
check "T3: overrun -> rc 124 (timed out)" "$rc" "124"

# T4: NO LEAK on the early-completion path. A reparented orphan is invisible to
#     `jobs -p`, so we scan the REAL process table for the watchdog's sleep.
#     Use a unique marker timeout value so we match THIS test's sleep only, then
#     run a SHORT NON-INSTANT command (sleep 0.2 — >=200ms guarantees the
#     watchdog's TERM trap is installed before teardown, so this is DETERMINISTIC,
#     no flake, while still exercising the real early-completion leak path).
#     Generous settle window so a loaded machine doesn't flake. NOTE: we scan only
#     for the UNIQUE marker `sleep 98765`, never the command's own `sleep 0.2`.
T4=$(mktemp -d)
marker=98765                                   # unique sleep duration -> greppable
# Run a short non-instant command under a (marker-second) timeout; the watchdog
# will `sleep 98765`. The command finishes first -> early-completion teardown.
( bash "$FLGIT" fl_run_with_timeout "$marker" -- sleep 0.2 ) >/dev/null 2>&1
# Give any orphan a moment to show up, then look for a `sleep 98765` we own.
leak=""
for _try in 1 2 3 4 5 6 7 8 9 10; do
  # match the literal marker arg; exclude our own grep/ps pipeline.
  if ps -A -o pid=,args= 2>/dev/null | grep -E "sleep[[:space:]]+$marker([[:space:]]|$)" | grep -v grep >/dev/null 2>&1; then
    leak="present"
  else
    leak=""; break
  fi
  sleep 1
done
# Best-effort cleanup so a (buggy) leaked sleep doesn't linger past the test run.
ps -A -o pid=,args= 2>/dev/null | grep -E "sleep[[:space:]]+$marker([[:space:]]|$)" | grep -v grep \
  | awk '{print $1}' | while read -r p; do kill "$p" 2>/dev/null; done
rm -rf "$T4"
[ -z "$leak" ] && ok "T4: no leaked watchdog sleep after fast success (early-completion path)" \
               || bad "T4: watchdog 'sleep $marker' orphaned to init on the fast-success path"

# T5: integration — run_verify still PASSES a quick command set unchanged.
T5=$(mktemp -d); repo="$T5/repo"; mkrepo "$repo"
printf 'edited\n' >> "$repo/README.md"            # safe diff -> gate allows
out="$( cd "$repo" && printf 'true\ntrue\n' | FL_VERIFY_CMD_TIMEOUT=30 bash "$FLGIT" run_verify 2>&1 )"; rc=$?
check "T5: run_verify quick set -> rc 0" "$rc" "0"
case "$out" in *FL-VERIFY-ALL-PASS*) ok "T5: reports all-pass";; *) bad "T5: missing all-pass marker";; esac
rm -rf "$T5"

# T6: integration — a hung command past a tiny timeout makes run_verify FAIL
#     (nonzero), AND fail-fast survives the wrapper: the next command does NOT run.
T6=$(mktemp -d); repo="$T6/repo"; mkrepo "$repo"
printf 'edited\n' >> "$repo/README.md"
snr="$T6/SHOULD_NOT_RUN"; rm -f "$snr"
out="$( cd "$repo" && printf '%s\n' "sleep 30" "touch $snr" | FL_VERIFY_CMD_TIMEOUT=1 bash "$FLGIT" run_verify 2>&1 )"; rc=$?
[ "$rc" -ne 0 ] && ok "T6: hung command -> run_verify rc nonzero ($rc)" || bad "T6: hung command did not fail run_verify"
[ ! -e "$snr" ] && ok "T6: fail-fast survives wrapper (command after the timeout did NOT run)" \
               || bad "T6: command after a timed-out command still ran (fail-fast broken)"
rm -rf "$T6"

echo "== $pass passed, $fail failed =="
[ "$fail" -eq 0 ]
