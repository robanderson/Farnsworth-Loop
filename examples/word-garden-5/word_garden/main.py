"""Entry point and game loop for Word Garden.

This is the ONLY module that touches stdin/stdout,
and only via the injected ``input_fn`` and ``output_fn`` parameters.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from word_garden import game as _game
from word_garden import ui as _ui

# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="word_garden",
        description="Word Garden — a friendly terminal word-guessing game.",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "normal", "hard"],
        default="normal",
        help="Game difficulty: easy (water=8), normal (water=6), hard (water=4). "
             "Default: normal.",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Use plain ASCII symbols instead of emoji.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(
    argv: list[str] | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[..., None] = print,
) -> int:
    """Run a complete Word Garden session and return an exit code.

    Parameters
    ----------
    argv:
        Command-line arguments (defaults to ``sys.argv[1:]``).
    input_fn:
        Callable used to read user input — injectable for tests.
    output_fn:
        Callable used to display output — injectable for tests.

    Returns
    -------
    int
        Always 0 (clean exit, including friendly EOF/interrupt handling).
        ``argparse`` raises ``SystemExit(2)`` for usage errors and
        ``SystemExit(0)`` for ``--help``; these are intentionally not caught.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    ascii_mode: bool = args.ascii
    difficulty: str = args.difficulty

    state = _game.new_game(difficulty=difficulty)

    try:
        while not state.game_over:
            output_fn(_ui.render(state, ascii_mode=ascii_mode))
            output_fn("")  # blank line before prompt

            raw = input_fn("Guess a letter: ")
            letter, error = _game.validate_guess(raw)

            if letter is None:
                # Invalid input — display the validation error without
                # changing the game state.  We update status_message so
                # the feedback shows on the next render, but we must NOT
                # mutate the dataclass; we produce a lightweight copy.
                import dataclasses as _dc
                state = _dc.replace(state, status_message=error)
                continue

            state = _game.apply_guess(state, letter)

        # --- Game over — show final screen ----------------------------
        output_fn(_ui.render(state, ascii_mode=ascii_mode))

    except (EOFError, KeyboardInterrupt):
        output_fn("\nThanks for visiting the garden. Goodbye!")

    return 0
