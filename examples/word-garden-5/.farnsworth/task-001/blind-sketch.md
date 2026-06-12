# Blind Implementation Sketch — Task 001 Word Garden

Written before reading any candidate diff. Anchoring defence.

## words.py
- `WORDS = ["GARDEN","FLOWER","PLANET","PYTHON","TERMINAL","MEADOW","ORCHARD","VINEYARD","SEEDLING","HARVEST"]` (already uppercase).
- Difficulty table as a dict: easy=(8, lambda L: 4<=len<=6), normal=(6, 5<=len<=8), hard=(4, len>=7).
- `select_word(difficulty="normal", rng=None)`: validate difficulty (else ValueError), filter WORDS by length predicate, if pool empty raise ValueError (tip 5), pick via (rng or random).choice. Default uses module-level random functions, NOT a fresh seeded Random (tip 6).
- `water_for(difficulty="normal")`: returns water count; ValueError on unknown.
- Note: with the fixed 10-word list, must verify each difficulty pool is non-empty. easy 4-6: GARDEN(6),FLOWER(6),PLANET(6),PYTHON(6),MEADOW(6) -> ok. normal 5-8: many. hard 7+: TERMINAL(8),ORCHARD(7),VINEYARD(8),SEEDLING(8),HARVEST(7) -> ok.

## game.py
- `GameState` dataclass with EXACT field order/names/defaults from SPEC 12. guessed_letters is a set[str] (use field(default_factory=set) or required).
- Message constants module-level: GOOD_GUESS="Good guess! The garden grows.", NO_MATCH="No match. A weed appears.", ALREADY="You already guessed {L}. Try another letter.", win/loss screens, game-over no-op message.
- `new_game(difficulty="normal", rng=None)`: select_word, uppercase, remaining_water=max_water=water_for, weed_count=0, empty guessed set.
- `validate_guess(input_text)`: strip, upper; empty -> (None, "Please enter a single letter."); len>1 -> multiple letters msg; non-alpha single -> "That is not a letter."; returns (letter, ""). Does NOT consult state (tip 10/spec).
- `apply_guess(state, letter)`: if game_over -> no-op + message. If letter in guessed_letters -> already-guessed message, no change. Else add to guessed; if in secret_word -> good message; else water-1, weed+1, no-match message. Then recompute win/loss: if is_won -> game_over=won=True + win message overwrites; elif is_lost -> game_over=True + loss message overwrites. Return state (mutate or copy).
- `display_word(state)`: " ".join(c if c in guessed else "_").
- `is_won(state)`: all(c in guessed for c in secret_word).
- `is_lost(state)`: remaining_water<=0 AND not is_won (tip 10 — must guard, correct even on a won water-0 state).

## ui.py — pure, returns strings, no print/input.
- `render(state, ascii_mode=False)`: title with growth glyph, masked word, guessed (sorted, space-joined), water line `n/max` + symbols, weeds line `count` + symbols, then status message block if non-empty. Order per SPEC 9.
- Accessibility (SPEC 18): water shows `count/max` + symbols; weeds shows count + symbols. Text label + numeric always.
- Growth stages (SPEC 10): 5 distinct — start/progress/near-win/win/loss. Driven by fraction of distinct secret letters revealed; win/loss from flags. ascii fallback swaps emoji.
- Win screen (6.6) and loss screen (6.7) — loss names the word + "ran out of water".
- ascii_mode: every emoji swapped; whole session ASCII.

## main.py — only stdin/stdout module, via injected fns.
- `main(argv=None, input_fn=input, output_fn=print) -> int` EXACT/CLOSED signature.
- argparse: --difficulty {easy,normal,hard} default normal, --ascii. No try/except SystemExit (tip 4).
- Loop: render -> output; prompt "Guess a letter: " via input_fn; validate; if invalid output message (no cost); else apply_guess; until game_over; then print win/loss screen; return 0.
- EOFError/KeyboardInterrupt -> friendly goodbye, return 0.
- __main__.py: sys.exit(main()).

## tests/
- 10 SPEC-16 cases + e2e win AND loss with pinned word asserting final screens, no-cost paths, 5 growth stages, ascii purity whole session, EOF + interrupt exits, select_word every difficulty.
- Tests import message constants (tip 7), assert positive outcomes combined (tip 2), force scenarios (tip 3), construct states directly (tip 8), exercise predicates directly on terminal states (tip 10).

## Likely defect hotspots to probe
- is_lost on won water-0 state (tip 10).
- Terminal message overwrites turn message (tip 1).
- ascii purity across the FINAL win/loss screens too, not just the loop.
- select_word default rng correctness (not fresh-seeded).
- validate_guess not consulting state.
- Growth stages actually 5 distinct.
- Tests asserting hand-typed literals vs constants (tip 7).
- Signature exactness of main (tip 10).
