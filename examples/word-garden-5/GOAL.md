# Word Garden — Goal Brief

This file is the loop's termination contract (PRD Section 2.4). The loop
cycles — one task per iteration, each derived from the gap between the
merged state and this goal — until BOTH halves of done pass. Nothing in
this file pre-plans the task list; iteration count is emergent.

## Objective

A complete, playable Word Garden: the friendly terminal word-guessing
game specified in `SPEC.md`, launchable as `python3 -m word_garden`,
meeting every acceptance criterion in SPEC section 20.

## Done — mechanical half

The `goal.done` checks in `farnsworth.json`, run by `farnsworth done`
against the merged state from the repo root:

1. `acceptance` — `python3 -m unittest discover -s tests` exits 0.
2. `compiles` — `python3 -m compileall -q word_garden` exits 0.
3. `plays-eof` — `printf '' | python3 -m word_garden` exits 0 (immediate
   EOF gets a friendly goodbye, never a traceback).
4. `plays-ascii` — `printf '' | python3 -m word_garden --ascii` exits 0.
5. `help` — `python3 -m word_garden --help` exits 0.
6. `usage-error` — `python3 -m word_garden --bogus` exits 2.

## Done — semantic half

The reviewer attests, in its final review, that the merged state meets
SPEC section 20 in full, and specifically that:

- All ten SPEC section 16 test cases are covered by the suite, with
  positive assertions.
- The game plays a full session: random word, masked display, one-letter
  guesses, validation per section 14, guessed-letter tracking, water and
  weed accounting per sections 6.3–6.5, win/loss detection per 6.6–6.7
  with the spec's end screens, clean exit.
- Section 18 accessibility holds: text labels and numeric counts
  alongside any symbols; `--ascii` makes the entire output ASCII.
- Section 10's five growth stages are observable and distinct.
- Difficulty selection works per the section 7 table
  (`--difficulty easy|normal|hard`, default normal).
- No criterion is met only by accident of the word list (forced-scenario
  tests pin words for win/loss paths).

## Exits

DONE when both halves pass. ESCALATED if a change request blocks all
remaining work. STOPPED at the orchestrator's budget. STALLED after 3
consecutive iterations without measurable progress on the done checks.
