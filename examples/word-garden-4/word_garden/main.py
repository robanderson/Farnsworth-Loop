"""Command-line entry point and game loop for Word Garden.

This is the ONLY module that touches stdin/stdout. All terminal interaction
goes through the injectable ``input_fn``/``output_fn`` so the loop is testable
without a real terminal.
"""

import argparse

from .game import apply_guess, new_game, validate_guess
from .ui import loss_screen, render, win_screen

PROMPT = "Guess a letter: "
GOODBYE = "Thanks for visiting the garden. Come back soon!"

_DIFFICULTIES = ["easy", "normal", "hard"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="word_garden",
        description="Word Garden — a friendly terminal word-guessing game.",
    )
    parser.add_argument(
        "--difficulty",
        choices=_DIFFICULTIES,
        default="normal",
        help="word length and starting water (default: normal).",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="use the pure-ASCII display instead of emoji.",
    )
    return parser


def main(argv=None, input_fn=input, output_fn=print) -> int:
    """Run a full game and return the process exit code (0).

    ``input_fn`` and ``output_fn`` default to the builtins but may be injected
    for testing. Note: ``parse_args`` is intentionally NOT wrapped in
    try/except — ``--help`` must exit 0 and a usage error must exit 2.
    """
    args = _build_parser().parse_args(argv)
    ascii_mode = args.ascii
    state = new_game(args.difficulty)

    try:
        while not state.game_over:
            output_fn(render(state, ascii_mode=ascii_mode))
            output_fn("")
            raw = input_fn(PROMPT)
            letter, error = validate_guess(raw)
            if letter is None:
                # Invalid input: show the message and re-prompt without
                # consuming a turn (SPEC §6.2/§14).
                output_fn(error)
                continue
            state = apply_guess(state, letter)

        screen = (
            win_screen(state, ascii_mode=ascii_mode)
            if state.won
            else loss_screen(state, ascii_mode=ascii_mode)
        )
        output_fn(screen)
        return 0
    except (EOFError, KeyboardInterrupt):
        # Ctrl-D / Ctrl-C: friendly goodbye, clean exit, never a traceback.
        output_fn("")
        output_fn(GOODBYE)
        return 0
