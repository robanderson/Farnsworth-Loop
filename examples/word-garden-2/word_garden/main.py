"""Terminal entry point and game loop for Word Garden.

This is the **only** module that performs I/O. It reads guesses, drives the
pure engine (:mod:`word_garden.game`) and the pure renderer
(:mod:`word_garden.ui`), and prints the result. For testability, :func:`main`
takes injectable ``input_fn`` / ``output_fn`` callables and uses them
exclusively; the defaults are the builtins :func:`input` and :func:`print`.

See SPEC.md sections 5, 9, 15, 20 and 21.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

from word_garden import game, ui

PROMPT = "Guess a letter: "
GOODBYE = "Thanks for tending the garden. Goodbye!"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="word_garden",
        description=(
            "Word Garden — a friendly terminal word-guessing game. "
            "Guess the hidden word before the garden runs out of water."
        ),
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "normal", "hard"],
        default="normal",
        help="Difficulty: water and word-length band (default: normal).",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Use the plain-ASCII display instead of emoji.",
    )
    return parser


def main(
    argv: list[str] | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Run a full game and return a process exit code.

    Parses ``argv`` (``--difficulty`` and ``--ascii``), runs the guess loop —
    rendering the state, prompting, validating (invalid input re-prompts
    without consuming a turn), and applying valid guesses — until the game is
    over, then shows the win or loss screen. EOF (Ctrl-D) and
    ``KeyboardInterrupt`` (Ctrl-C) exit cleanly with a friendly message and
    code 0; no traceback ever reaches the user.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    ascii_mode = args.ascii

    state = game.new_game(args.difficulty)

    try:
        while not state.game_over:
            output_fn(ui.render(state, ascii_mode=ascii_mode))
            output_fn("")
            raw = input_fn(PROMPT)
            letter, message = game.validate_guess(raw)
            if letter is None:
                # Invalid input: show the message, re-prompt, no turn consumed.
                output_fn(message)
                output_fn("")
                continue
            game.apply_guess(state, letter)
            output_fn("")

        if state.won:
            output_fn(ui.win_screen(state, ascii_mode=ascii_mode))
        else:
            output_fn(ui.loss_screen(state, ascii_mode=ascii_mode))
        return 0
    except (EOFError, KeyboardInterrupt):
        output_fn("")
        output_fn(GOODBYE)
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
