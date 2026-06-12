# Word Garden 🌱

> Word Garden is a small TUI game designed as a more cheerful alternative to
> Hangman. It is intended as a slightly more adventurous "Hello World" project
> for testing AI-assisted software development. The game includes input
> validation, state management, a simple loop, win/loss conditions, and a
> friendly terminal interface.

Guess the hidden word before the garden runs out of water. Each correct guess
helps the garden grow; each wrong guess costs a drop of water and lets a weed
appear. Reveal the whole word to make the garden bloom — it's like Hangman,
but with plants instead of gallows.

## Requirements

- Python 3.11 or newer (standard library only — nothing to install).

## How to run

```bash
python3 -m word_garden
```

Options:

```bash
python3 -m word_garden --difficulty easy    # easy | normal | hard (default: normal)
python3 -m word_garden --ascii              # pure-ASCII display for terminals without emoji
```

`--difficulty` changes both the starting water and the pool of words:

| Difficulty | Water | Word length |
|---|---:|---:|
| easy   | 8 | 4–6 letters |
| normal | 6 | 5–8 letters |
| hard   | 4 | 7+ letters  |

## How to play

1. The game picks a secret word and shows one blank per letter.
2. Type a single letter and press Enter at the `Guess a letter:` prompt.
3. A correct guess reveals every matching position in the word.
4. A wrong guess costs one unit of water and adds one weed.
5. Repeated or invalid input (empty, multiple characters, digits, symbols)
   is rejected with a friendly message and does **not** cost a turn.
6. You win when the whole word is revealed; you lose if water reaches zero
   first. Press Ctrl-D or Ctrl-C at any time to leave the garden cleanly.

## Sample screen

```text
🌱 Word Garden

Garden:  🌿  The garden is growing.
Word:    G _ R _ E _
Guessed: A E G R
Water:   4/6 💧💧💧💧
Weeds:   2 🌿🌿

Good guess! The garden grows.

Guess a letter:
```

The same turn in `--ascii` mode:

```text
Word Garden

Garden:  **  The garden is growing.
Word:    G _ R _ E _
Guessed: A E G R
Water:   4/6 [****  ]
Weeds:   2 [--]

Good guess! The garden grows.

Guess a letter:
```

## Project layout

```text
word_garden/
  __main__.py   # python3 -m word_garden entry point
  main.py       # argument parsing and the game loop (the only I/O module)
  game.py       # game state, guesses, win/loss logic
  words.py      # word list and difficulty filtering
  ui.py         # pure rendering (returns strings; no printing)
tests/          # unittest suite (engine + UI)
```

## Running the tests

```bash
python3 -m unittest discover -s tests
```
