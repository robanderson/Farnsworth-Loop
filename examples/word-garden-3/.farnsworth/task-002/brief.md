# Dispatch briefing — task-002 (as sent to all three workers)

Triaged 3-worker round (haiku/sonnet/opus). Each worker received: the
blindness preamble, its worktree path and branch, the base commit to
verify (d8482866384dc9ee17c9f013d1c4ec305bd15c69), an instruction to read
the FULL `.code-tips.md` in its worktree (now 9 seed entries + 14
project-scoped task-001 distillations) and honor every entry as contract,
the full text of `tasks/task-002.md`, its focus directive with the
standard precedence sentence, and the gate it must pass locally:
unittest + compileall + the two per-task extensions (piped-EOF run of
`python3 -m word_garden` exits 0 with no traceback; engine files and
engine tests byte-identical to base).
