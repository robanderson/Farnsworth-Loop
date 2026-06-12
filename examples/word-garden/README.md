# Word Garden

> Word Garden is a small TUI game designed as a more cheerful alternative to Hangman. It is intended as a slightly more adventurous "Hello World" project for testing AI-assisted software development. The game includes input validation, state management, a simple loop, win/loss conditions, and a friendly terminal interface.

Guess the hidden word before the garden runs out of water. It is like Hangman, but with plants instead of gallows.

## How to Run

```bash
python3 -m word_garden
```

### Options

| Flag | Description |
|------|-------------|
| `--difficulty easy` | More water (8), shorter words (4-6 letters) |
| `--difficulty normal` | Default — 6 water, words 5-8 letters |
| `--difficulty hard` | Less water (4), longer words (7+ letters) |
| `--ascii` | Pure ASCII output — no emoji, works in any terminal |

Examples:

```bash
python3 -m word_garden --difficulty easy
python3 -m word_garden --difficulty hard --ascii
```

## Rules

1. A secret word is chosen at random.
2. Guess one letter at a time.
3. A correct guess reveals all matching positions in the word.
4. A wrong guess costs one unit of water and adds a weed.
5. Guess the full word before water runs out to win.
6. Invalid input (numbers, symbols, multiple letters, empty) is rejected and does not cost water.

## Sample Screen

```text
Word Garden

[*]

Word:     G _ R _ _ _
Guessed:  A G R
Water:  3/6 ~~~
Weeds:  2 --

Good guess! The garden grows.
```

(Emoji mode shows plant emoji and colourful symbols instead of ASCII art.)

## Requirements

- Python 3.11 or newer
- No external packages — standard library only

## Running Tests

```bash
python3 -m unittest discover -s tests
```
