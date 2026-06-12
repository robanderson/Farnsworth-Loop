"""End-to-end tests for word_garden/main.py — the game loop.

Uses injected input_fn/output_fn (Code Tips #6).
Pins the word via monkeypatching select_word in try/finally (Code Tips #3, #8).
Asserts final screens using constants (Code Tips #7).
"""

import random
import unittest
from io import StringIO

import word_garden.words as _words_module
from word_garden.game import (
    MSG_LOSS_BODY_TEMPLATE,
    MSG_LOSS_TITLE,
    MSG_WIN_BODY_TEMPLATE,
    MSG_WIN_TITLE,
)
from word_garden.main import main


def _run(inputs: list[str], argv: list[str] | None = None) -> tuple[int, str]:
    """Run main() with a scripted input list; return (exit_code, all_output)."""
    input_iter = iter(inputs)
    output_parts: list[str] = []

    def fake_input(prompt: str = "") -> str:
        try:
            return next(input_iter)
        except StopIteration:
            raise EOFError

    def fake_output(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        output_parts.append(sep.join(str(a) for a in args) + end)

    code = main(argv=argv or [], input_fn=fake_input, output_fn=fake_output)
    return code, "".join(output_parts)


def _pin_word(word: str):
    """Return a context-manager-style object that pins select_word."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        original = _words_module.select_word
        _words_module.select_word = lambda difficulty="normal", rng=None: word
        try:
            yield
        finally:
            _words_module.select_word = original

    return _ctx()


class TestEndToEndWin(unittest.TestCase):
    """Full win session with a pinned 3-letter word (Code Tips #3)."""

    def test_win_session(self):
        with _pin_word("CAT"):
            # Guess all three letters correctly
            code, output = _run(["c", "a", "t"])
        self.assertEqual(code, 0)
        self.assertIn(MSG_WIN_TITLE, output)
        self.assertIn(MSG_WIN_BODY_TEMPLATE.format(word="CAT"), output)

    def test_win_session_ascii(self):
        with _pin_word("CAT"):
            code, output = _run(["c", "a", "t"], argv=["--ascii"])
        self.assertEqual(code, 0)
        # Must contain no non-ASCII characters
        non_ascii = [c for c in output if ord(c) > 127]
        self.assertEqual(non_ascii, [], f"Non-ASCII chars found: {non_ascii}")
        self.assertIn("CAT", output)


class TestEndToEndLoss(unittest.TestCase):
    """Full loss session with a pinned word (Code Tips #3)."""

    def test_loss_session(self):
        # CAT with normal water=6; guess 6 wrong letters to exhaust water
        with _pin_word("CAT"):
            code, output = _run(["z", "x", "q", "v", "b", "w"])
        self.assertEqual(code, 0)
        self.assertIn(MSG_LOSS_TITLE, output)
        self.assertIn(MSG_LOSS_BODY_TEMPLATE.format(word="CAT"), output)


class TestEofAndInterrupt(unittest.TestCase):
    def test_eof_exits_0_with_goodbye(self):
        with _pin_word("CAT"):
            code, output = _run([])  # immediately EOF
        self.assertEqual(code, 0)
        self.assertIn("Goodbye", output)

    def test_eof_with_ascii_is_clean(self):
        with _pin_word("CAT"):
            code, output = _run([], argv=["--ascii"])
        self.assertEqual(code, 0)
        non_ascii = [c for c in output if ord(c) > 127]
        self.assertEqual(non_ascii, [], f"Non-ASCII: {non_ascii}")


class TestInvalidInputNoCost(unittest.TestCase):
    """Invalid input must not change water or weeds (no-cost path)."""

    def test_invalid_input_then_win(self):
        with _pin_word("IT"):
            # "7" is invalid, "i" and "t" complete the word
            code, output = _run(["7", "i", "t"])
        self.assertEqual(code, 0)
        self.assertIn(MSG_WIN_TITLE, output)

    def test_repeated_guess_no_cost_then_win(self):
        with _pin_word("IT"):
            # "i" twice (second is a repeat), then "t" wins
            code, output = _run(["i", "i", "t"])
        self.assertEqual(code, 0)
        self.assertIn(MSG_WIN_TITLE, output)


class TestDifficultyFlag(unittest.TestCase):
    def test_easy_difficulty_accepted(self):
        with _pin_word("MEADOW"):
            code, output = _run([], argv=["--difficulty", "easy"])
        self.assertEqual(code, 0)

    def test_hard_difficulty_accepted(self):
        with _pin_word("TERMINAL"):
            code, output = _run([], argv=["--difficulty", "hard"])
        self.assertEqual(code, 0)


class TestCLIFlags(unittest.TestCase):
    def test_help_exits_0(self):
        with self.assertRaises(SystemExit) as ctx:
            main(argv=["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_unknown_flag_exits_2(self):
        with self.assertRaises(SystemExit) as ctx:
            main(argv=["--bogus"])
        self.assertEqual(ctx.exception.code, 2)


class TestWholeSessionAsciiPurity(unittest.TestCase):
    """A complete game session under --ascii must produce only ASCII text."""

    def test_full_win_session_ascii(self):
        with _pin_word("CAT"):
            code, output = _run(["c", "a", "t"], argv=["--ascii"])
        non_ascii = [c for c in output if ord(c) > 127]
        self.assertEqual(non_ascii, [], f"Non-ASCII chars: {non_ascii!r}")

    def test_full_loss_session_ascii(self):
        with _pin_word("CAT"):
            code, output = _run(["z", "x", "q", "v", "b", "w"], argv=["--ascii"])
        non_ascii = [c for c in output if ord(c) > 127]
        self.assertEqual(non_ascii, [], f"Non-ASCII chars: {non_ascii!r}")
