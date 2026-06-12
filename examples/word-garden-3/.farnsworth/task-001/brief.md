# Dispatch briefing — task-001 (as sent to all five workers)

Each worker received, verbatim: the blindness preamble (work only in your
assigned worktree; no other worktree, branch, or repo may enter context),
its worktree path and branch, the base commit to verify
(6cfef01b03023ef77b291601caa94a65d555800d), a summary of the 9
cross-project seed entries in `.code-tips.md` with an instruction to read
and honor the full file, the full text of `tasks/task-001.md`, its own
focus directive (per `farnsworth.json`; foci differ per worker and are
sealed from the reviewer until post-verdict), and the precedence sentence:

> Precedence: the task brief and its acceptance criteria ALWAYS take
> precedence over this focus directive. The focus is a lens for your
> discretionary decisions only, never a license to deviate from the brief.

Process requirements: run the gate locally before finishing (unittest
discover + compileall), commit everything to the assigned branch
(uncommitted work does not exist), never commit bytecode, never write
`.code-tips.md`, never modify `SPEC.md`/`farnsworth.json`/`tasks/`,
and end with an approach summary + a line on how the focus shaped
discretionary choices + the final test count.

Tips state at dispatch: the cross-project seed only (9 entries) — the
first live trial of cross-project memory; no project-scoped tips exist yet.
