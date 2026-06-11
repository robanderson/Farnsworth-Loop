# Blind Sketch — task-001 (written before opening any diff)

## Layout
`word_garden/{__init__.py,game.py,words.py}` + `tests/{__init__.py,test_game.py,test_words.py}`. Stdlib only.

## words.py
- `WORDS`: the 10 SPEC §8 words, uppercased, as a list (module-level constant). Keep order; easy to extend.
- Difficulty table as a dict: `{"easy": (8, 4, 6), "normal": (6, 5, 8), "hard": (4, 7, None)}` → (water, min_len, max_len). `7+` = no upper bound.
- `water_for(difficulty="normal") -> int`: look up table, `ValueError` on unknown key.
- `select_word(difficulty="normal", rng=None) -> str`: validate difficulty (ValueError), filter WORDS by length window, choose with `(rng or random).choice(filtered)`. Inject `random.Random` for determinism. Guard: if filtered empty, that's a data/spec problem — but with given list each difficulty should have candidates (verify mentally: hard 7+ → PLANET(6? no, 6), TERMINAL(8), ORCHARD(7), VINEYARD(8), SEEDLING(8), HARVEST(7) — yes non-empty).

## game.py
- `GameState` dataclass with EXACT field names/order from §12: `secret_word, guessed_letters, remaining_water, weed_count, max_water, status_message="", game_over=False, won=False`. `guessed_letters: set[str]`.
- `new_game(difficulty="normal", rng=None)`: word=select_word(...).upper(); water=water_for(diff); empty set; weed_count=0; max_water=water; flags False; neutral/empty status.
- `validate_guess(input_text) -> tuple[str|None, str]`: strip; if empty → (None, "Please enter a single letter."); if len>1 → (None, "Please enter a single letter."); if not alpha → (None, "That is not a letter."); else (char.upper(), ""). NO state access. Order matters: empty/multi-char check before alpha so "ab" gives length message and "7" gives not-a-letter.
- `apply_guess(state, letter) -> GameState`: 
  - if game_over → no-op, message "The game is already over." Return state (decide mutate-in-place vs copy; SPEC implies returning GameState; I'd mutate the dataclass and return it for simplicity, but immutability via replace is cleaner — either acceptable if consistent).
  - if letter in guessed_letters → message "You already guessed {L}. Try another letter.", no water/weed change.
  - else add letter; if in secret_word → message "Good guess! The garden grows."; else remaining_water-=1, weed_count+=1, message "No match. A weed appears."
  - after applying, recompute win/loss: if all secret letters in guessed → won=True, game_over=True (overwrite message with bloom text). elif remaining_water<=0 → game_over=True (loss text). Win check BEFORE loss when last water on a correct guess (correct guess can't drop water, so win-on-last-water = wrong guess that empties water — that's a loss not win; but "win on last water" means revealing final letter while water==1 stays a win since correct guess costs nothing). Important: check win first regardless.
- `display_word(state)`: `" ".join(c if c in guessed_letters else "_" for c in secret_word)`.
- `is_won`: all letters of secret in guessed. `is_lost`: remaining_water<=0 and not won.

## Edge cases to nail
- Repeated WRONG guess: still no second penalty (guarded by `in guessed_letters` first).
- Guess after game_over: no mutation.
- Win-on-last-water: correct final guess with water==1 → won, not lost.
- display masks non-guessed letters only.

## Test plan
All 10 §16 cases with POSITIVE assertions: wrong guess asserts water==before-1 AND weeds==before+1 AND letter in guessed. Use injected `random.Random(seed)` for determinism. Test validate for empty/multi/number/symbol/lowercase-normalization. Test win sets won&game_over, loss sets game_over&not won. Test display masking explicitly. Test select_word for all three difficulties returns word within length window; unknown difficulty raises ValueError.
