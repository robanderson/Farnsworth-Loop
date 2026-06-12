# Word Garden

Word Garden is a small TUI game designed as a more cheerful alternative to
Hangman. It is intended as a slightly more adventurous "Hello World" project
for testing AI-assisted software development. The game includes input
validation, state management, a simple loop, win/loss conditions, and a
friendly terminal interface.

Guess the hidden word before the garden runs out of water. It is like
Hangman, but with plants instead of gallows.

## Requirements

- Python 3.11 or newer. Standard library only — no third-party packages.

## How to play

From the project root:

```bash
python3 -m word_garden
```

You guess one letter at a time. A correct guess reveals every matching
position in the word and helps the garden grow. A wrong guess costs one unit
of water and lets a weed appear. Reveal the whole word before the water runs
out and the garden blooms; run dry first and it wilts.

### Options

```bash
python3 -m word_garden --difficulty easy    # easy | normal (default) | hard
python3 -m word_garden --ascii              # plain-ASCII display, no emoji
```

- `--difficulty` changes both the starting water and the pool of words:

  | Difficulty | Water | Word length |
  |------------|------:|------------:|
  | easy       |     8 | 4–6 letters |
  | normal     |     6 | 5–8 letters |
  | hard       |     4 | 7+ letters  |

- `--ascii` swaps the emoji glyphs for plain ASCII, for terminals that do not
  render emoji. Water and weeds always show a text label and a count, so the
  game stays readable in either mode.

Press Ctrl-D (EOF) or Ctrl-C at any time to leave; the garden says a friendly
goodbye and exits cleanly.

## Rules summary

- Input is trimmed, uppercased, and validated as a single letter.
- Invalid input (empty, multiple characters, digits, symbols) is rejected with
  a helpful message and does **not** consume water.
- Repeating a letter you already guessed costs nothing but reminds you.
- Correct guesses reveal letters; wrong guesses cost one water and add a weed.
- You **win** when the whole word is revealed.
- You **lose** when the water reaches zero before the word is complete; the
  secret word is then revealed.

## Sample screen

```text
🌿 Word Garden

Word:     G A R _ E _
Guessed:  A E G R
Water: 4/6 💧💧💧💧
Weeds: 2 🌿🌿

Good guess! The garden grows.

Guess a letter:
```

The same game in `--ascii` mode:

```text
* Word Garden

Word:     G A R _ E _
Guessed:  A E G R
Water: 4/6 ****
Weeds: 2 --

Good guess! The garden grows.

Guess a letter:
```

Have fun, and happy gardening!
