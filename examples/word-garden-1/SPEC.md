# Word Garden — TUI Game Specification

## 1. Overview

Word Garden is a small terminal-based word guessing game designed as a friendly alternative to Hangman.

The player guesses letters to reveal a hidden word. Correct guesses help the garden grow. Incorrect guesses consume water and allow weeds to spread. The player wins by revealing the whole word before the garden runs out of water.

The project is intended to be a slightly more adventurous "Hello World" program for testing AI-assisted software development. It is small enough to build quickly, but rich enough to test project structure, state management, user input, terminal UI rendering, validation, randomness, and basic game logic.

## 2. Goals

The game should demonstrate:

- Terminal user interaction
- A simple game loop
- Random word selection
- Input validation
- Persistent game state during a session
- Clear win and loss conditions
- Friendly, non-violent theming
- Clean, readable code suitable for extension

## 3. Non-Goals

The initial version does not need:

- Networking
- Multiplayer
- User accounts
- Persistent save files
- Complex animations
- External APIs
- Large dictionaries
- Advanced terminal graphics

These may be added later as extensions.

## 4. Game Theme

The player is tending a small word garden.

Each correct guess helps the plant grow. Each incorrect guess costs one unit of water and causes weeds to appear. The game ends when either the word is fully revealed or the player runs out of water.

The tone should be friendly, light, and encouraging.

## 5. Example Screen

```text
🌱 Word Garden

Word:      _ _ _ _ _ _
Guessed:   A E R
Water:    💧💧💧
Weeds:    🌿🌿

Guess a letter: _
```

## 6. Core Game Rules

### 6.1 Starting a Game

When the game starts:

1. Select a random secret word from a predefined word list.
2. Convert the word to uppercase internally.
3. Display blanks for each unguessed letter.
4. Set the starting water level.
5. Set the weed count to zero.
6. Begin the input loop.

Example starting state:

```text
Secret word: GARDEN
Displayed:   _ _ _ _ _ _
Water:       6
Weeds:       0
Guesses:     []
```

### 6.2 Guessing

The player enters one letter at a time.

Input should be:

- Trimmed of whitespace
- Converted to uppercase
- Validated as a single alphabetic character

Valid examples:

```text
a
Z
```

Invalid examples:

```text
apple
7
!
<empty input>
```

Invalid input should not consume water.

### 6.3 Correct Guess

If the guessed letter appears in the secret word:

- Add the letter to the guessed letters list.
- Reveal all matching positions in the displayed word.
- Show a positive message.

Example:

```text
Good guess! The garden grows.
```

### 6.4 Incorrect Guess

If the guessed letter does not appear in the secret word:

- Add the letter to the guessed letters list.
- Decrease water by 1.
- Increase weeds by 1.
- Show a gentle warning message.

Example:

```text
No match. A weed appears.
```

### 6.5 Repeated Guess

If the player guesses a letter they have already tried:

- Do not change water.
- Do not change weeds.
- Show a message.

Example:

```text
You already guessed A. Try another letter.
```

### 6.6 Winning

The player wins when all letters in the secret word have been revealed.

Example win screen:

```text
🌻 Bloom!

You guessed the word: GARDEN
The garden is thriving.
```

### 6.7 Losing

The player loses when water reaches zero before the word is fully revealed.

Example loss screen:

```text
🥀 The garden ran out of water.

The word was: GARDEN
Try again and grow a new garden.
```

## 7. Difficulty Levels

The initial implementation may use one default difficulty.

Recommended default:

```text
Water: 6
Word length: 4–8 letters
```

Optional difficulty levels:

| Difficulty | Water | Word Length |
|---|---:|---:|
| Easy | 8 | 4–6 letters |
| Normal | 6 | 5–8 letters |
| Hard | 4 | 7+ letters |

## 8. Word List

The first version may use a small built-in word list.

Example:

```text
GARDEN
FLOWER
PLANET
PYTHON
TERMINAL
MEADOW
ORCHARD
VINEYARD
SEEDLING
HARVEST
```

The word list should be easy to replace or extend.

For a publishable version, avoid words that are:

- Offensive
- Overly obscure
- Ambiguous
- Proper nouns, unless deliberately included
- Too short to be interesting

## 9. Display Requirements

The display should show:

- Game title
- Current plant/garden status
- Hidden word with guessed letters revealed
- Already guessed letters
- Remaining water
- Weed count
- Prompt for next guess
- Feedback from the previous turn

Example:

```text
🌱 Word Garden

Word:     G _ R _ E _
Guessed:  A E G R
Water:   💧💧💧💧
Weeds:   🌿🌿

Good guess! The garden grows.

Guess a letter:
```

## 10. Garden Visuals

The garden can be represented using simple text or emoji.

Suggested water display:

```text
💧💧💧💧💧💧
```

Suggested weed display:

```text
🌿🌿🌿
```

Suggested growth stages:

| Stage | Visual |
|---|---|
| Start | 🌱 |
| Progress | 🌿 |
| Near win | 🌷 |
| Win | 🌻 |
| Loss | 🥀 |

The exact visual design is flexible. The game should still be playable in terminals that do not render emoji correctly.

A fallback ASCII mode may use:

```text
Plant:  *
Water:  [******]
Weeds:  [---]
```

## 11. Suggested Program Structure

A clean implementation should separate:

```text
word_garden/
  main.py
  game.py
  words.py
  ui.py
  README.md
```

Suggested responsibilities:

### main.py

- Program entry point
- Starts a new game
- Runs the main loop

### game.py

- Stores game state
- Applies guesses
- Checks win/loss conditions

### words.py

- Contains the word list
- Selects random words
- May handle difficulty filtering

### ui.py

- Renders the terminal display
- Handles user-facing messages
- May support emoji and ASCII modes

## 12. Game State Model

The game state should include:

```text
secret_word
guessed_letters
remaining_water
weed_count
max_water
status_message
game_over
won
```

Example Python-style structure:

```python
@dataclass
class GameState:
    secret_word: str
    guessed_letters: set[str]
    remaining_water: int
    weed_count: int
    max_water: int
    status_message: str = ""
    game_over: bool = False
    won: bool = False
```

## 13. Core Functions

Recommended functions:

```text
new_game(difficulty) -> GameState
display_word(state) -> str
validate_guess(input_text) -> result
apply_guess(state, letter) -> GameState
is_won(state) -> bool
is_lost(state) -> bool
render(state) -> str
```

## 14. Input Validation

The game should handle:

- Empty input
- Multiple characters
- Numbers
- Symbols
- Repeated guesses
- Lowercase letters
- Leading or trailing spaces

Invalid input should not count as a guess.

Example messages:

```text
Please enter a single letter.
That is not a letter.
You already guessed that letter.
```

## 15. Example Game Flow

```text
🌱 Word Garden

Word:     _ _ _ _ _ _
Guessed:
Water:   💧💧💧💧💧💧
Weeds:

Guess a letter: a

Good guess! The garden grows.

Word:     _ A _ _ _ _
Guessed:  A
Water:   💧💧💧💧💧💧
Weeds:

Guess a letter: z

No match. A weed appears.

Word:     _ A _ _ _ _
Guessed:  A Z
Water:   💧💧💧💧💧
Weeds:   🌿
```

## 16. Testing Requirements

The game logic should be testable without running the terminal UI.

Recommended tests:

1. A correct guess reveals matching letters.
2. An incorrect guess reduces water by one.
3. An incorrect guess increases weed count by one.
4. Repeated guesses do not reduce water.
5. Invalid input is rejected.
6. Lowercase input is normalized.
7. The game detects a win.
8. The game detects a loss.
9. The displayed word masks unguessed letters.
10. The word selector returns a valid word.

## 17. Extension Ideas

Possible future features:

- Difficulty selection
- Categories such as plants, programming, wine, animals, or geography
- Hint system
- Score tracking
- Streak counter
- Daily word mode
- Configurable word list file
- ASCII-only mode
- Colour terminal output
- Sound-free animation effects
- Save/load game
- Unit tests and CI
- Web version
- AI-generated word categories
- Local leaderboard

## 18. Accessibility Considerations

The game should not rely only on colour or emoji.

Where possible:

- Use text labels as well as symbols.
- Keep prompts clear.
- Avoid flashing animations.
- Support ASCII fallback.
- Make error messages specific and helpful.

Example:

```text
Water: 4/6 💧💧💧💧
Weeds: 2 🌿🌿
```

## 19. Publishing Description

Suggested short description:

> Word Garden is a friendly terminal word-guessing game. Guess the hidden word before the garden runs out of water. It is like Hangman, but with plants instead of gallows.

Suggested README intro:

> Word Garden is a small TUI game designed as a more cheerful alternative to Hangman. It is intended as a slightly more adventurous "Hello World" project for testing AI-assisted software development. The game includes input validation, state management, a simple loop, win/loss conditions, and a friendly terminal interface.

## 20. Acceptance Criteria

A complete first version should:

- Start from the command line.
- Pick a random word.
- Display masked letters.
- Accept one-letter guesses.
- Reject invalid input.
- Track guessed letters.
- Reveal correct guesses.
- Penalize incorrect guesses.
- Show remaining water.
- Show weed count.
- Detect win condition.
- Detect loss condition.
- Offer a clear final message.
- Exit cleanly.

## 21. Example Command

```bash
python3 -m word_garden
```

Optional future commands:

```bash
python3 -m word_garden --difficulty easy
python3 -m word_garden --ascii
python3 -m word_garden --category vineyard
```

## 22. Design Principle

The game should stay small, readable, and pleasant.

It should be more interesting than "Hello World", but not so complex that it stops being useful as a quick AI development test.
