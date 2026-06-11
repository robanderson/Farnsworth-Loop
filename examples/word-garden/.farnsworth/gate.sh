#!/bin/sh
# Mechanical gate, run per worktree: tests + compile. ASCII output only.
wt="$1"
cd "$wt" || exit 2
echo "== gate: $wt"
out=$(python3 -m unittest discover -s tests 2>&1)
t=$?
echo "$out" | tail -2
python3 -m compileall -q word_garden >/dev/null 2>&1
c=$?
echo "tests: exit $t / compile: exit $c"
[ "$t" -eq 0 ] && [ "$c" -eq 0 ]
