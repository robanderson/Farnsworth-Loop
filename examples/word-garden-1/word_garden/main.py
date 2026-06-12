"""Word Garden — main game loop and CLI entry point.

This is the ONLY module that performs I/O (stdin/stdout). Everything else in
the package is pure logic or pure rendering.  See SPEC.md sections 5, 15, 20.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from .game import apply_guess, new_game, validate_guess
from .ui import loss_screen, render, win_screen

_GOODBYE = "Thanks for playing Word Garden. Goodbye!"


def main(
    argv: list[str] | None = None,
    input_fn: Callable[..., str] = input,
    output_fn: Callable[..., None] = print,
) -> int:
    """Run one full game and return an exit code (always 0).

    Parameters
    ----------
    argv:
        Argument list for argparse (defaults to sys.argv[1:]).
    input_fn:
        Replacement for ``input()``; injected during tests.
    output_fn:
        Replacement for ``print()``; injected during tests.
    """
    parser = argparse.ArgumentParser(
        prog="word_garden",
        description="Word Garden — a friendly terminal word-guessing game.",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "normal", "hard"],
        default="normal",
        help="Game difficulty (default: normal).",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        default=False,
        help="Use ASCII-only output (no emoji).",
    )
    args = parser.parse_args(argv)

    ascii_mode: bool = args.ascii
    difficulty: str = args.difficulty

    state = new_game(difficulty)

    try:
        while not state.game_over:
            output_fn(render(state, ascii_mode=ascii_mode))
            output_fn("")

            # Inner loop: re-prompt on invalid input without consuming a turn.
            while True:
                try:
                    raw = input_fn("Guess a letter: ")
                except EOFError:
                    output_fn("")
                    output_fn(_GOODBYE)
                    return 0

                letter, error = validate_guess(raw)
                if letter is None:
                    output_fn(error)
                    continue

                state = apply_guess(state, letter)
                break

        # Game is over — show the final screen.
        if state.won:
            output_fn(win_screen(state, ascii_mode=ascii_mode))
        else:
            output_fn(loss_screen(state, ascii_mode=ascii_mode))

    except KeyboardInterrupt:
        output_fn("")
        output_fn(_GOODBYE)

    return 0


if __name__ == "__main__":
    sys.exit(main())
