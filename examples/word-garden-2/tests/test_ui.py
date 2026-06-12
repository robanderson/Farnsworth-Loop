"""Tests for the pure renderer (ui.py) and the I/O loop (main.py).

ui.py must perform no I/O and produce a clean ASCII fallback; main.py is the
only module that touches stdin/stdout, exercised here with injected
input/output functions.
"""

from __future__ import annotations

import unittest

from word_garden import game, ui
from word_garden.game import GameState
from word_garden.main import GOODBYE, main


def _state(
    secret_word="GARDEN",
    guessed=(),
    remaining_water=6,
    weed_count=0,
    max_water=6,
    status_message="",
    game_over=False,
    won=False,
):
    return GameState(
        secret_word=secret_word,
        guessed_letters=set(guessed),
        remaining_water=remaining_water,
        weed_count=weed_count,
        max_water=max_water,
        status_message=status_message,
        game_over=game_over,
        won=won,
    )


def _is_ascii(text: str) -> bool:
    return all(ord(ch) < 128 for ch in text)


class RenderEmojiModeTest(unittest.TestCase):
    def test_contains_labels_and_counts(self):
        state = _state(
            guessed=("A", "Z"), remaining_water=5, weed_count=1
        )
        out = ui.render(state, ascii_mode=False)
        # Accessibility: text label AND count present for both meters.
        self.assertIn("Water:", out)
        self.assertIn("5/6", out)
        self.assertIn("Weeds:", out)
        self.assertIn("Word:", out)
        self.assertIn("Guessed:", out)
        self.assertIn("Word Garden", out)

    def test_emoji_mode_has_non_ascii_glyphs(self):
        out = ui.render(_state(), ascii_mode=False)
        self.assertFalse(_is_ascii(out))

    def test_masked_word_and_guessed_sorted(self):
        state = _state(secret_word="GARDEN", guessed=("E", "G", "R"))
        out = ui.render(state, ascii_mode=False)
        self.assertIn("G _ R _ E _", out)
        self.assertIn("E G R", out)
        # Now the four-letter sorted case.
        state = _state(secret_word="GARDEN", guessed=("E", "A", "G", "R"))
        out = ui.render(state, ascii_mode=False)
        self.assertIn("G A R _ E _", out)
        # Guessed letters appear sorted and space-separated.
        self.assertIn("A E G R", out)

    def test_status_message_shown(self):
        state = _state(status_message=game.MSG_CORRECT)
        out = ui.render(state, ascii_mode=False)
        self.assertIn(game.MSG_CORRECT, out)


class RenderAsciiModeTest(unittest.TestCase):
    def test_ascii_mode_is_pure_ascii(self):
        state = _state(
            guessed=("A", "Z"), remaining_water=5, weed_count=1,
            status_message=game.MSG_WRONG,
        )
        out = ui.render(state, ascii_mode=True)
        self.assertTrue(_is_ascii(out), "ascii_mode output must be pure ASCII")

    def test_ascii_mode_keeps_labels_and_counts(self):
        state = _state(remaining_water=4, weed_count=2, max_water=6)
        out = ui.render(state, ascii_mode=True)
        self.assertIn("Water:", out)
        self.assertIn("4/6", out)
        self.assertIn("Weeds:", out)
        self.assertIn("2", out)

    def test_ascii_win_and_loss_screens_pure_ascii(self):
        won = _state(guessed=tuple("GARDEN"), won=True, game_over=True)
        lost = _state(remaining_water=0, weed_count=6, game_over=True)
        self.assertTrue(_is_ascii(ui.win_screen(won, ascii_mode=True)))
        self.assertTrue(_is_ascii(ui.loss_screen(lost, ascii_mode=True)))


class GrowthStageTest(unittest.TestCase):
    def test_start_stage(self):
        self.assertEqual(ui.growth_stage(_state(guessed=())), "start")

    def test_progress_stage(self):
        # 2/6 revealed -> progress (below near-win threshold).
        state = _state(secret_word="GARDEN", guessed=("G", "A"))
        self.assertEqual(ui.growth_stage(state), "progress")

    def test_near_win_stage(self):
        # 5/6 revealed -> near-win.
        state = _state(secret_word="GARDEN", guessed=tuple("GARDE"))
        self.assertEqual(ui.growth_stage(state), "near-win")

    def test_win_stage(self):
        state = _state(
            secret_word="GARDEN", guessed=tuple("GARDEN"),
            won=True, game_over=True,
        )
        self.assertEqual(ui.growth_stage(state), "win")

    def test_loss_stage(self):
        state = _state(
            secret_word="GARDEN", guessed=("Z", "X"),
            remaining_water=0, weed_count=2, game_over=True,
        )
        self.assertEqual(ui.growth_stage(state), "loss")

    def test_win_beats_loss_on_zero_water(self):
        # Word fully revealed while water is 0 must read as win.
        state = _state(
            secret_word="GARDEN", guessed=tuple("GARDEN"),
            remaining_water=0, won=True, game_over=True,
        )
        self.assertEqual(ui.growth_stage(state), "win")


class WinLossScreenTest(unittest.TestCase):
    def test_win_screen_shows_word_and_message(self):
        state = _state(secret_word="GARDEN", won=True, game_over=True)
        out = ui.win_screen(state)
        self.assertIn("GARDEN", out)
        self.assertIn("Bloom!", out)
        self.assertIn("thriving", out)

    def test_loss_screen_reveals_word(self):
        state = _state(secret_word="VINEYARD", game_over=True)
        out = ui.loss_screen(state)
        self.assertIn("VINEYARD", out)
        self.assertIn("ran out of water", out)


class NoIoInUiTest(unittest.TestCase):
    def test_ui_source_has_no_print_or_input(self):
        import inspect

        source = inspect.getsource(ui)
        self.assertNotIn("print(", source)
        self.assertNotIn("input(", source)


class ScriptedInput:
    """A callable that returns queued inputs, then raises EOFError."""

    def __init__(self, inputs):
        self._inputs = list(inputs)

    def __call__(self, prompt=""):
        if not self._inputs:
            raise EOFError
        return self._inputs.pop(0)


class MainLoopTest(unittest.TestCase):
    def _run(self, inputs, argv):
        outputs = []
        code = main(
            argv=argv,
            input_fn=ScriptedInput(inputs),
            output_fn=lambda *a: outputs.append(
                " ".join(str(x) for x in a)
            ),
        )
        return code, "\n".join(outputs)

    def test_end_to_end_win(self):
        # GARDEN is a normal-difficulty word; force it by patching new_game.
        original = game.new_game
        try:
            game_state = GameState(
                secret_word="GARDEN",
                guessed_letters=set(),
                remaining_water=6,
                weed_count=0,
                max_water=6,
            )
            game.new_game = lambda *a, **k: game_state
            code, out = self._run(
                list("GARDEN"), argv=["--difficulty", "normal"]
            )
        finally:
            game.new_game = original
        self.assertEqual(code, 0)
        self.assertIn("Bloom!", out)
        self.assertIn("You guessed the word: GARDEN", out)

    def test_end_to_end_loss(self):
        original = game.new_game
        try:
            game_state = GameState(
                secret_word="GARDEN",
                guessed_letters=set(),
                remaining_water=4,
                weed_count=0,
                max_water=4,
            )
            game.new_game = lambda *a, **k: game_state
            code, out = self._run(
                list("ZXQWJ"), argv=["--difficulty", "hard", "--ascii"]
            )
        finally:
            game.new_game = original
        self.assertEqual(code, 0)
        self.assertIn("ran out of water", out)
        self.assertIn("The word was: GARDEN", out)
        self.assertTrue(_is_ascii(out), "ascii run must be pure ASCII")

    def test_invalid_input_does_not_consume_water(self):
        original = game.new_game
        try:
            game_state = GameState(
                secret_word="GARDEN",
                guessed_letters=set(),
                remaining_water=6,
                weed_count=0,
                max_water=6,
            )
            game.new_game = lambda *a, **k: game_state
            # "apple", "7", "!" are invalid; then play to win.
            code, out = self._run(
                ["apple", "7", "!", ""] + list("GARDEN"),
                argv=[],
            )
        finally:
            game.new_game = original
        self.assertEqual(code, 0)
        # Water never decreased: still full and a win.
        self.assertEqual(game_state.remaining_water, 6)
        self.assertIn("Please enter a single letter.", out)
        self.assertIn("That is not a letter.", out)
        self.assertIn("Bloom!", out)

    def test_eof_exits_cleanly(self):
        code, out = self._run([], argv=[])
        self.assertEqual(code, 0)
        self.assertIn(GOODBYE, out)

    def test_keyboard_interrupt_exits_cleanly(self):
        def interrupt(prompt=""):
            raise KeyboardInterrupt

        outputs = []
        code = main(
            argv=[],
            input_fn=interrupt,
            output_fn=lambda *a: outputs.append(" ".join(str(x) for x in a)),
        )
        self.assertEqual(code, 0)
        self.assertIn(GOODBYE, "\n".join(outputs))


if __name__ == "__main__":
    unittest.main()
