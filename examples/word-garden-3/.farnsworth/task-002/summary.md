# Run summary -- task-002

Base commit `d848286638`, 2026-06-12T01:00:00Z -> 2026-06-12T01:45:00Z.
Tips at dispatch: 9 seed + 14 project entries. Triaged 3-worker fleet.

| Worker | Focus | Exit | Gate | Candidate | Result |
|---|---|---:|---|---|---|
| w1 | test rigor and edge cases | 0 | PASS | C |  |
| w2 | accessibility / display contracts | 0 | PASS | B |  |
| w3 | readability and maintainability | 0 | PASS | A | ADOPTED |

**Verdict:** adopt candidate A

**Defects found in gate-passing field:** 2, both contract-level; ZERO
behavioral bugs (both prior runs' UI rounds shipped one). B: required
`main()` signature extended with `new_game_fn` (own tests depend on it).
C: message-constant rule violated in source and tests.

**Seed result:** the argparse/SystemExit defect that shipped in BOTH prior
projects' UI rounds did not occur — all three candidates honored the seed
entry the moment it became applicable.

**Reasoning (abridged):** A renders the SPEC display contracts faithfully
(order, five growth stages, label+count accessibility, whole-game ASCII),
keeps argparse exit codes intact, and shows the field's best constants
discipline with forced-scenario e2e tests. B's extra-parameter deviation
from the required signature is disqualifying because avoidable; C re-types
literals — the exact rot pattern the tips warn against.

**Progression** *(reviewer-authored; reporting feature added 2026-06-12,
recorded retroactively in `run.json` for this run):* Built on the task-001
engine UNCHANGED — the gate proved `game.py`, `words.py`, and their 80
tests byte-identical to base. New: the project becomes a playable game.
`ui.py` (pure rendering) adds the SPEC §9 display in fixed order, a public
progress-driven `growth_stage()` reusing the engine predicates, emoji and
whole-game pure-ASCII modes, §18 label+count accessibility, and win/loss
screens revealing the word. `main.py` (sole I/O module) adds the loop:
argparse `--difficulty`/`--ascii` with intact exit codes, invalid input
re-prompting at zero cost, EOF/Ctrl-C goodbyes with exit 0, injectable
`input_fn`/`output_fn`; `__main__.py` enables `python3 -m word_garden`;
README.md documents play. Suite: 80 → 105 tests, now including scripted
end-to-end win AND loss games. Improved on the task-001 state without
editing it: every user-facing string now has a single source of truth
(the UI imports the engine's `MSG_*` constants and names its own), and the
engine's win-precedence and terminal-message contracts are now exercised
through full played games, not unit tests alone. Lessons visibly absorbed:
the argparse seed entry was honored by the entire field after shipping as
a bug in both prior projects' UI rounds.
