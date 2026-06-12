"""Command-line entry point and game loop for Word Garden.

This is the *only* module that touches the terminal. All input and output
flow through the injectable ``input_fn`` / ``output_fn`` parameters of
:func:`main` (defaulting to the builtins), so the loop runs hermetically
under test. Rendering is delegated to :mod:`word_garden.ui`; game logic to
:mod:`word_garden.game`.
"""

from __future__ import annotations

import argparse
from typing import Callable

from word_garden import game, ui

GOODBYE = "Thanks for tending the garden. Goodbye!"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="word_garden",
        description="Word Garden — a friendly terminal word-guessing game.",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "normal", "hard"],
        default="normal",
        help="Difficulty level (changes water and the word pool).",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Use the plain-ASCII display instead of emoji.",
    )
    return parser


def _final_screen(state: game.GameState, ascii_mode: bool) -> str:
    """Pick the win or loss screen for a finished game."""
    if state.won:
        return ui.win_screen(state, ascii_mode=ascii_mode)
    return ui.loss_screen(state, ascii_mode=ascii_mode)


def _play(
    state: game.GameState,
    ascii_mode: bool,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    """Run the interactive loop until the game is over.

    Invalid input shows its validation message and re-prompts WITHOUT
    consuming a turn (no ``apply_guess`` call), per SPEC 6.2 / 14.
    """
    while not state.game_over:
        output_fn(ui.render(state, ascii_mode=ascii_mode))
        output_fn("")
        raw = input_fn(ui.PROMPT)

        letter, message = game.validate_guess(raw)
        if letter is None:
            output_fn(message)
            output_fn("")
            continue

        state = game.apply_guess(state, letter)

    output_fn(_final_screen(state, ascii_mode=ascii_mode))


def main(
    argv: list[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Parse arguments, play one game, and return a process exit code.

    EOF (Ctrl-D) and KeyboardInterrupt (Ctrl-C) end the session with a
    friendly goodbye and a clean exit code 0 — never a traceback.
    """
    args = _build_parser().parse_args(argv)
    state = game.new_game(difficulty=args.difficulty)

    try:
        _play(state, args.ascii, input_fn, output_fn)
    except (EOFError, KeyboardInterrupt):
        output_fn("")
        output_fn(GOODBYE)

    return 0
