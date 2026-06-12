# Word Garden

> Word Garden is a small TUI game designed as a more cheerful alternative to
> Hangman. It is intended as a slightly more adventurous "Hello World" project
> for testing AI-assisted software development. The game includes input
> validation, state management, a simple loop, win/loss conditions, and a
> friendly terminal interface.

You tend a little word garden by guessing letters. Each correct guess helps the
garden grow; each wrong guess costs a unit of water and lets a weed creep in.
Reveal the whole word before the water runs out and your garden blooms.

It is like Hangman, but with plants instead of gallows.

## Requirements

- Python 3.11 or newer
- Standard library only — nothing to install

## How to run

From the project root:

```bash
python3 -m word_garden
```

### Options

```bash
python3 -m word_garden --difficulty easy   # more water, shorter words
python3 -m word_garden --difficulty normal # the default
python3 -m word_garden --difficulty hard   # less water, longer words
python3 -m word_garden --ascii             # plain-ASCII display (no emoji)
```

`--difficulty` and `--ascii` can be combined, e.g.:

```bash
python3 -m word_garden --difficulty hard --ascii
```

## Difficulty levels

| Difficulty | Water | Word length |
|------------|------:|------------:|
| Easy       |     8 | 4–6 letters |
| Normal     |     6 | 5–8 letters |
| Hard       |     4 | 7+ letters  |

## Rules

- A secret word is chosen at random for your chosen difficulty.
- Enter one letter at a time at the `Guess a letter:` prompt.
- A **correct** guess reveals every matching position in the word.
- A **wrong** guess costs one unit of water and adds one weed.
- A **repeated** guess costs nothing — just try a different letter.
- Invalid input (empty, multiple characters, numbers, symbols) is rejected
  with a helpful message and does **not** use up a turn or any water.
- You **win** when the whole word is revealed.
- You **lose** when the water reaches zero before the word is complete.
- Press **Ctrl-D** or **Ctrl-C** at any time to leave with a friendly goodbye.

## Accessibility

The display never relies on emoji or colour alone. Water and weeds always carry
a text label and a numeric count alongside any symbols, and `--ascii` provides a
pure-ASCII display for terminals that do not render emoji.

## Sample screen

```text
🌱 Word Garden

Plant:  🌿 Your garden is growing.

Word:    G A R _ E _
Guessed: A E G R
Water:  4/6 💧💧💧💧
Weeds:  2 🌿🌿

Good guess! The garden grows.

Guess a letter:
```

The same turn in `--ascii` mode:

```text
Word Garden

Plant:  i Your garden is growing.

Word:    G A R _ E _
Guessed: A E G R
Water:  4/6 ****
Weeds:  2 --

Good guess! The garden grows.

Guess a letter:
```

## Project layout

```text
word_garden/
  __init__.py   # public engine API
  __main__.py   # python3 -m word_garden entry point
  words.py      # word list + difficulty-aware selection (engine)
  game.py       # game state and rules (engine)
  ui.py         # pure rendering (no I/O)
  main.py       # the only I/O module: argument parsing and the game loop
tests/          # unit tests for the engine and the UI
```

## Tests

```bash
python3 -m unittest discover -s tests
```

Have fun, and grow a lovely garden!
