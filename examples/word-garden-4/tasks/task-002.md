# Task 002 — Word Garden UI: rendering, main loop, packaging

## Goal

Build the terminal UI and entry point on top of the adopted task-001 engine
(`word_garden/game.py`, `word_garden/words.py` on this branch — read them
first; they are a fixed contract, do NOT modify them). Deliver a playable
game per SPEC.md sections 5, 9, 10, 15, 18, 20 and a project README.

## Hard requirements

1. **Stdlib only, Python 3.11+.** New files:
   ```
   word_garden/ui.py
   word_garden/main.py
   word_garden/__main__.py
   tests/test_ui.py
   README.md
   ```
   Engine files are read-only for this task.
2. **`word_garden/ui.py` — pure rendering, no I/O:**
   - `render(state, ascii_mode=False) -> str`: the full turn display per
     SPEC.md section 9, in order: title, plant/garden status (growth stage
     per the section 10 table, driven by progress: start / progress /
     near-win / win / loss), masked word (`display_word`), guessed letters
     (sorted, space-separated), water, weeds, and the previous turn's
     `status_message`. Accessibility per section 18: water and weeds always
     carry a text label AND a count (e.g. `Water:  4/6 ` + symbols), never
     symbols alone.
   - Emoji mode uses the section 10 glyphs; `ascii_mode=True` uses the
     section 10 ASCII fallback (no non-ASCII characters anywhere in the
     output).
   - `win_screen(state, ascii_mode=False) -> str` and
     `loss_screen(state, ascii_mode=False) -> str` per sections 6.6/6.7
     (loss screen reveals the secret word).
   - No `print()`/`input()` in ui.py; everything returns strings.
3. **`word_garden/main.py` — the only I/O module:**
   - `main(argv=None) -> int`: argparse with `--difficulty
     {easy,normal,hard}` (default normal) and `--ascii`. Runs the loop:
     render state, prompt `Guess a letter: `, read input, `validate_guess`
     (invalid input shows the message and re-prompts without consuming a
     turn), `apply_guess`, repeat until `game_over`, then show the win/loss
     screen and return 0.
   - Handle EOF (Ctrl-D) and KeyboardInterrupt with a friendly goodbye and
     clean exit code 0 — never a traceback.
   - For testability, `main` accepts injectable `input_fn=input` and
     `output_fn=print` keyword arguments and uses them exclusively.
   - `word_garden/__main__.py`: `python3 -m word_garden` runs `main()`.
4. **Tests (`tests/test_ui.py`, extend as needed):** render both modes
   (emoji output contains the labels+counts; ascii output contains NO
   non-ASCII characters — assert both positively), growth stages at start /
   mid / near-win / win / loss, win and loss screens, and at least one
   scripted end-to-end `main()` run each for a win and a loss using
   injected input/output functions (assert the final screen appeared).
5. **README.md:** the SPEC section 19 intro, how to run
   (`python3 -m word_garden`, `--difficulty`, `--ascii`), rules summary,
   and a sample screen. Friendly tone.
6. **Hygiene:** honor every entry in `.code-tips.md`. Commit to your
   branch; never commit bytecode; never write `.code-tips.md`; do not
   modify `SPEC.md`, `farnsworth.json`, `tasks/`, or the engine modules.

## Acceptance criteria

- [ ] `python3 -m unittest discover -s tests` green (existing 49 engine 
      tests untouched and still passing, plus new UI tests).
- [ ] `python3 -m compileall -q word_garden` green.
- [ ] `python3 -m word_garden` plays a full game; `--ascii` output is pure
      ASCII; `--difficulty` changes water and word pool.
- [ ] Invalid input re-prompts without consuming water (SPEC 6.2/14).
- [ ] Win shows the section 6.6 screen; loss shows 6.7 with the word.
- [ ] EOF/Ctrl-C exit cleanly with a friendly message, code 0.
- [ ] ui.py has zero I/O calls; main.py is the only module touching
      stdin/stdout.
- [ ] Engine modules byte-identical to base commit.

## Out of scope

Colour output, animations, sound, save/load, hints, scores, categories,
daily mode, web version. (SPEC section 17 extensions are all later tasks.)
