"""Tests for word_garden.ui and word_garden.main.

Covers rendering (emoji and ASCII modes), growth stages, win/loss screens,
and scripted end-to-end main() runs for win and loss paths.
"""

from __future__ import annotations

import unittest

from word_garden.game import GameState, apply_guess
from word_garden.ui import loss_screen, render, win_screen
from word_garden.main import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(
    secret: str = "GARDEN",
    water: int = 6,
    guessed: set[str] | None = None,
    game_over: bool = False,
    won: bool = False,
    status_message: str = "",
    weed_count: int = 0,
) -> GameState:
    """Construct a deterministic GameState for testing."""
    return GameState(
        secret_word=secret,
        guessed_letters=set(guessed or set()),
        remaining_water=water,
        weed_count=weed_count,
        max_water=water,
        status_message=status_message,
        game_over=game_over,
        won=won,
    )


# ---------------------------------------------------------------------------
# render() — emoji mode
# ---------------------------------------------------------------------------

class RenderEmojiTests(unittest.TestCase):

    def test_render_contains_title(self):
        state = make_state()
        output = render(state)
        self.assertIn("Word Garden", output)

    def test_render_contains_word_line(self):
        state = make_state("GARDEN", guessed={"G", "R"})
        output = render(state)
        self.assertIn("G _ R _ _ _", output)

    def test_render_contains_guessed_letters_sorted(self):
        state = make_state("GARDEN", guessed={"R", "G", "A"})
        output = render(state)
        self.assertIn("A G R", output)

    def test_render_water_label_and_count(self):
        """Accessibility: water must have text label AND numeric count."""
        state = make_state("GARDEN", water=4)
        output = render(state)
        # Label present
        self.assertIn("Water:", output)
        # Fraction present (4/6 not possible since max_water==water here)
        self.assertIn("4/4", output)

    def test_render_weed_label_and_count(self):
        """Accessibility: weeds must have text label AND numeric count."""
        state = make_state("GARDEN", water=4, weed_count=2)
        output = render(state)
        self.assertIn("Weeds:", output)
        self.assertIn("2 ", output)

    def test_render_water_symbols_emoji(self):
        """Emoji mode: water line contains emoji symbols."""
        state = make_state("GARDEN", water=3)
        output = render(state)
        self.assertIn("\U0001f4a7", output)  # 💧

    def test_render_status_message_shown(self):
        state = make_state(status_message="Good guess! The garden grows.")
        output = render(state)
        self.assertIn("Good guess! The garden grows.", output)

    def test_render_empty_status_message_not_shown(self):
        state = make_state(status_message="")
        output = render(state)
        # No trailing blank message
        lines = output.splitlines()
        self.assertNotEqual(lines[-1], "")

    def test_render_no_io_calls(self):
        """render() must return a string, not print or raise."""
        state = make_state()
        result = render(state)
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# render() — ASCII mode
# ---------------------------------------------------------------------------

class RenderAsciiTests(unittest.TestCase):

    def test_ascii_output_contains_no_non_ascii(self):
        """ascii_mode=True must produce pure ASCII (ord < 128) output."""
        state = make_state("GARDEN", water=3, weed_count=1, guessed={"G"})
        output = render(state, ascii_mode=True)
        for ch in output:
            self.assertLess(
                ord(ch), 128,
                msg=f"Non-ASCII character {ch!r} (U+{ord(ch):04X}) found in ASCII output",
            )

    def test_ascii_mode_water_label_present(self):
        state = make_state("GARDEN", water=3)
        output = render(state, ascii_mode=True)
        self.assertIn("Water:", output)

    def test_ascii_mode_weed_label_present(self):
        state = make_state("GARDEN", water=3, weed_count=2)
        output = render(state, ascii_mode=True)
        self.assertIn("Weeds:", output)

    def test_ascii_mode_water_count_present(self):
        state = make_state("GARDEN", water=5)
        output = render(state, ascii_mode=True)
        self.assertIn("5/5", output)

    def test_ascii_mode_no_emoji(self):
        state = make_state("GARDEN", water=5, weed_count=1)
        output = render(state, ascii_mode=True)
        # Explicitly check absence of common emoji
        self.assertNotIn("\U0001f4a7", output)  # 💧
        self.assertNotIn("\U0001f33f", output)  # 🌿
        self.assertNotIn("\U0001f331", output)  # 🌱

    def test_ascii_win_screen_no_non_ascii(self):
        state = make_state("GARDEN", won=True, game_over=True)
        output = win_screen(state, ascii_mode=True)
        for ch in output:
            self.assertLess(ord(ch), 128,
                            msg=f"Non-ASCII {ch!r} in ASCII win screen")

    def test_ascii_loss_screen_no_non_ascii(self):
        state = make_state("GARDEN", game_over=True, won=False)
        output = loss_screen(state, ascii_mode=True)
        for ch in output:
            self.assertLess(ord(ch), 128,
                            msg=f"Non-ASCII {ch!r} in ASCII loss screen")


# ---------------------------------------------------------------------------
# Growth stages
# ---------------------------------------------------------------------------

class GrowthStageTests(unittest.TestCase):
    """render() selects the right plant glyph at each progress point."""

    def _stage_line(self, output: str) -> str:
        """Return the line from the output that contains the stage glyph."""
        for line in output.splitlines():
            line_stripped = line.strip()
            if line_stripped in {
                "\U0001f331", "\U0001f33f", "\U0001f337", "\U0001f33b", "\U0001f940",
                "[.]", "[*]", "[+]", "[#]", "[x]",
            }:
                return line_stripped
        return ""

    def test_start_stage_emoji(self):
        state = make_state("GARDEN")  # no guesses
        output = render(state)
        self.assertIn("\U0001f331", output)  # 🌱

    def test_progress_stage_emoji(self):
        # 1 of 6 unique letters guessed in GARDEN → >0% but <75%
        state = make_state("GARDEN", guessed={"G"})
        output = render(state)
        self.assertIn("\U0001f33f", output)  # 🌿

    def test_near_win_stage_emoji(self):
        # GARDEN has 6 unique letters; 5/6 = 83% ≥ 75%
        state = make_state("GARDEN", guessed={"G", "A", "R", "D", "E"})
        output = render(state)
        self.assertIn("\U0001f337", output)  # 🌷

    def test_win_stage_emoji(self):
        state = make_state("GARDEN", guessed={"G", "A", "R", "D", "E", "N"},
                            won=True, game_over=True)
        output = render(state)
        self.assertIn("\U0001f33b", output)  # 🌻

    def test_loss_stage_emoji(self):
        state = make_state("GARDEN", water=0, game_over=True, won=False)
        output = render(state)
        self.assertIn("\U0001f940", output)  # 🥀

    def test_start_stage_ascii(self):
        state = make_state("GARDEN")
        output = render(state, ascii_mode=True)
        self.assertIn("[.]", output)

    def test_win_stage_ascii(self):
        state = make_state("GARDEN", won=True, game_over=True)
        output = render(state, ascii_mode=True)
        self.assertIn("[#]", output)

    def test_loss_stage_ascii(self):
        state = make_state("GARDEN", water=0, game_over=True, won=False)
        output = render(state, ascii_mode=True)
        self.assertIn("[x]", output)


# ---------------------------------------------------------------------------
# win_screen() and loss_screen()
# ---------------------------------------------------------------------------

class WinScreenTests(unittest.TestCase):

    def test_win_screen_contains_bloom(self):
        state = make_state("GARDEN", won=True, game_over=True)
        output = win_screen(state)
        self.assertIn("Bloom!", output)

    def test_win_screen_contains_secret_word(self):
        state = make_state("PYTHON", won=True, game_over=True)
        output = win_screen(state)
        self.assertIn("PYTHON", output)

    def test_win_screen_contains_thriving(self):
        state = make_state("GARDEN", won=True, game_over=True)
        output = win_screen(state)
        self.assertIn("thriving", output)

    def test_win_screen_emoji_glyph(self):
        state = make_state("GARDEN", won=True, game_over=True)
        output = win_screen(state)
        self.assertIn("\U0001f33b", output)  # 🌻

    def test_win_screen_ascii_no_non_ascii(self):
        state = make_state("GARDEN", won=True, game_over=True)
        output = win_screen(state, ascii_mode=True)
        for ch in output:
            self.assertLess(ord(ch), 128)

    def test_win_screen_returns_string(self):
        state = make_state("GARDEN", won=True, game_over=True)
        self.assertIsInstance(win_screen(state), str)


class LossScreenTests(unittest.TestCase):

    def test_loss_screen_contains_out_of_water(self):
        state = make_state("GARDEN", game_over=True, won=False)
        output = loss_screen(state)
        self.assertIn("ran out of water", output)

    def test_loss_screen_reveals_secret_word(self):
        state = make_state("HARVEST", game_over=True, won=False)
        output = loss_screen(state)
        self.assertIn("HARVEST", output)

    def test_loss_screen_contains_try_again(self):
        state = make_state("GARDEN", game_over=True, won=False)
        output = loss_screen(state)
        self.assertIn("Try again", output)

    def test_loss_screen_emoji_glyph(self):
        state = make_state("GARDEN", game_over=True, won=False)
        output = loss_screen(state)
        self.assertIn("\U0001f940", output)  # 🥀

    def test_loss_screen_ascii_no_non_ascii(self):
        state = make_state("GARDEN", game_over=True, won=False)
        output = loss_screen(state, ascii_mode=True)
        for ch in output:
            self.assertLess(ord(ch), 128)

    def test_loss_screen_returns_string(self):
        state = make_state("GARDEN", game_over=True, won=False)
        self.assertIsInstance(loss_screen(state), str)


# ---------------------------------------------------------------------------
# End-to-end main() tests using injected I/O
# ---------------------------------------------------------------------------

class MainWinTest(unittest.TestCase):
    """Scripted win: guess all letters of a short word before water runs out."""

    def test_win_path(self):
        """Player wins by guessing all letters of 'CAT' correctly."""
        # Force a known word by patching select_word indirectly via injected rng.
        # We drive the game with injected I/O; because the word is random we
        # instead route through the CLI and look for a win screen.
        outputs: list[str] = []

        def out(text: str = "", end: str = "\n", sep: str = " ", *args, **kwargs) -> None:
            outputs.append(str(text))

        # We need to know the word ahead of time to win.  We inject a seeded
        # game via monkeypatching new_game for this test only.
        import word_garden.main as wgm
        import word_garden.game as wgg

        original_new_game = wgm.new_game

        def patched_new_game(difficulty="normal", rng=None):
            import random as _random
            state = wgg.GameState(
                secret_word="CAT",
                guessed_letters=set(),
                remaining_water=6,
                weed_count=0,
                max_water=6,
            )
            return state

        wgm.new_game = patched_new_game
        try:
            guesses = iter(["c", "a", "t"])
            rc = main(argv=[], input_fn=lambda *a, **k: next(guesses), output_fn=out)
        finally:
            wgm.new_game = original_new_game

        self.assertEqual(rc, 0)
        combined = "\n".join(outputs)
        self.assertIn("Bloom!", combined)

    def test_loss_path(self):
        """Player loses by exhausting water with wrong guesses."""
        outputs: list[str] = []

        def out(text: str = "", *args, **kwargs) -> None:
            outputs.append(str(text))

        import word_garden.main as wgm
        import word_garden.game as wgg

        original_new_game = wgm.new_game

        def patched_new_game(difficulty="normal", rng=None):
            return wgg.GameState(
                secret_word="GARDEN",
                guessed_letters=set(),
                remaining_water=2,
                weed_count=0,
                max_water=2,
            )

        wgm.new_game = patched_new_game
        try:
            # Two wrong guesses exhaust water=2 → loss
            guesses = iter(["z", "x"])
            rc = main(argv=[], input_fn=lambda *a, **k: next(guesses), output_fn=out)
        finally:
            wgm.new_game = original_new_game

        self.assertEqual(rc, 0)
        combined = "\n".join(outputs)
        self.assertIn("ran out of water", combined)
        self.assertIn("GARDEN", combined)

    def test_eof_exits_cleanly(self):
        """EOF (Ctrl-D) on first prompt exits with code 0 and a goodbye message."""
        outputs: list[str] = []

        def out(text: str = "", *args, **kwargs) -> None:
            outputs.append(str(text))

        def eof_input(*a, **k):
            raise EOFError

        rc = main(argv=[], input_fn=eof_input, output_fn=out)
        self.assertEqual(rc, 0)
        combined = "\n".join(outputs)
        self.assertIn("Goodbye", combined)

    def test_invalid_input_does_not_consume_turn(self):
        """Invalid guess re-prompts without changing state (no water lost)."""
        outputs: list[str] = []

        def out(text: str = "", *args, **kwargs) -> None:
            outputs.append(str(text))

        import word_garden.main as wgm
        import word_garden.game as wgg

        original_new_game = wgm.new_game

        def patched_new_game(difficulty="normal", rng=None):
            return wgg.GameState(
                secret_word="HI",
                guessed_letters=set(),
                remaining_water=4,
                weed_count=0,
                max_water=4,
            )

        wgm.new_game = patched_new_game
        try:
            # "123" is invalid, then "h" and "i" win
            guesses = iter(["123", "h", "i"])
            rc = main(argv=[], input_fn=lambda *a, **k: next(guesses), output_fn=out)
        finally:
            wgm.new_game = original_new_game

        self.assertEqual(rc, 0)
        combined = "\n".join(outputs)
        # Validation error was shown
        self.assertIn("Please enter a single letter", combined)
        # Game was still won
        self.assertIn("Bloom!", combined)

    def test_ascii_mode_end_to_end(self):
        """--ascii flag produces pure-ASCII output end-to-end."""
        outputs: list[str] = []

        def out(text: str = "", *args, **kwargs) -> None:
            outputs.append(str(text))

        import word_garden.main as wgm
        import word_garden.game as wgg

        original_new_game = wgm.new_game

        def patched_new_game(difficulty="normal", rng=None):
            return wgg.GameState(
                secret_word="HI",
                guessed_letters=set(),
                remaining_water=4,
                weed_count=0,
                max_water=4,
            )

        wgm.new_game = patched_new_game
        try:
            guesses = iter(["h", "i"])
            rc = main(
                argv=["--ascii"],
                input_fn=lambda *a, **k: next(guesses),
                output_fn=out,
            )
        finally:
            wgm.new_game = original_new_game

        self.assertEqual(rc, 0)
        combined = "\n".join(outputs)
        for ch in combined:
            self.assertLess(
                ord(ch), 128,
                msg=f"Non-ASCII character {ch!r} found in ASCII mode output",
            )


if __name__ == "__main__":
    unittest.main()
