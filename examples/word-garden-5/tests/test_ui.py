"""Tests for word_garden/ui.py — rendering logic.

Uses direct GameState construction (Code Tips #8).
Imports message constants from game.py (Code Tips #7).
"""

import unittest

from word_garden.game import (
    GameState,
    MSG_CORRECT_GUESS,
    MSG_WIN_TITLE,
    MSG_LOSS_TITLE,
    MSG_WIN_BODY_TEMPLATE,
    MSG_LOSS_BODY_TEMPLATE,
)
from word_garden.ui import render


def _state(
    secret: str = "GARDEN",
    guessed: set[str] | None = None,
    water: int = 6,
    weeds: int = 0,
    max_water: int = 6,
    status: str = "",
    game_over: bool = False,
    won: bool = False,
) -> GameState:
    return GameState(
        secret_word=secret,
        guessed_letters=guessed if guessed is not None else set(),
        remaining_water=water,
        weed_count=weeds,
        max_water=max_water,
        status_message=status,
        game_over=game_over,
        won=won,
    )


class TestRenderNormalGame(unittest.TestCase):
    def test_contains_title(self):
        output = render(_state())
        self.assertIn("Word Garden", output)

    def test_contains_masked_word(self):
        output = render(_state(secret="GARDEN", guessed=set()))
        self.assertIn("_ _ _ _ _ _", output)

    def test_contains_water_fraction(self):
        output = render(_state(water=4, max_water=6))
        self.assertIn("4/6", output)

    def test_water_symbols_correct_count(self):
        output = render(_state(water=3, max_water=6))
        # Three water drops (💧) should appear
        self.assertEqual(output.count("\U0001f4a7"), 3)

    def test_weed_count_and_symbols(self):
        output = render(_state(weeds=2))
        self.assertIn("2", output)
        self.assertEqual(output.count("\U0001f33f"), 2)

    def test_status_message_shown(self):
        output = render(_state(status=MSG_CORRECT_GUESS))
        self.assertIn(MSG_CORRECT_GUESS, output)

    def test_empty_status_message_omitted(self):
        output = render(_state(status=""))
        # Should not have a trailing blank-plus-message section
        # Just verify the specific message text is absent
        self.assertNotIn(MSG_CORRECT_GUESS, output)

    def test_guessed_letters_sorted(self):
        output = render(_state(secret="GARDEN", guessed={"G", "A", "Z"}))
        # Sorted: A G Z
        self.assertIn("A G Z", output)

    def test_revealed_letters_shown(self):
        output = render(_state(secret="GARDEN", guessed={"G", "A"}))
        self.assertIn("G A R D E N".replace("R", "_")
                      .replace("D", "_")
                      .replace("E", "_")
                      .replace("N", "_"), output)


class TestRenderWinScreen(unittest.TestCase):
    def test_win_screen_contains_win_title(self):
        state = _state(
            secret="CAT",
            guessed={"C", "A", "T"},
            game_over=True,
            won=True,
        )
        output = render(state)
        self.assertIn(MSG_WIN_TITLE, output)

    def test_win_screen_contains_word(self):
        state = _state(
            secret="CAT",
            guessed={"C", "A", "T"},
            game_over=True,
            won=True,
        )
        output = render(state)
        self.assertIn("CAT", output)

    def test_win_screen_body(self):
        state = _state(
            secret="CAT",
            guessed={"C", "A", "T"},
            game_over=True,
            won=True,
        )
        output = render(state)
        expected_body = MSG_WIN_BODY_TEMPLATE.format(word="CAT")
        self.assertIn(expected_body, output)


class TestRenderLossScreen(unittest.TestCase):
    def test_loss_screen_contains_loss_title(self):
        state = _state(
            secret="CAT",
            guessed={"Z"},
            water=0,
            game_over=True,
            won=False,
        )
        output = render(state)
        self.assertIn(MSG_LOSS_TITLE, output)

    def test_loss_screen_names_the_word(self):
        state = _state(
            secret="CAT",
            guessed={"Z"},
            water=0,
            game_over=True,
            won=False,
        )
        output = render(state)
        self.assertIn("CAT", output)

    def test_loss_screen_body(self):
        state = _state(
            secret="CAT",
            guessed={"Z"},
            water=0,
            game_over=True,
            won=False,
        )
        output = render(state)
        expected_body = MSG_LOSS_BODY_TEMPLATE.format(word="CAT")
        self.assertIn(expected_body, output)


class TestGrowthStages(unittest.TestCase):
    """Five distinct growth-stage glyphs are observable (SPEC section 10)."""

    EMOJI_STAGES = {
        "start":    "\U0001f331",  # 🌱
        "progress": "\U0001f33f",  # 🌿
        "near_win": "\U0001f337",  # 🌷
        "win":      "\U0001f33b",  # 🌻
        "loss":     "\U0001f940",  # 🥀
    }

    def _title_glyph(self, state: GameState) -> str:
        """Extract the glyph from the first line of render output."""
        return render(state).splitlines()[0].split()[0]

    def test_stage_start(self):
        state = _state(secret="GARDEN", guessed=set())
        self.assertEqual(self._title_glyph(state), self.EMOJI_STAGES["start"])

    def test_stage_progress(self):
        # One letter revealed out of 5 distinct: fraction < 2/3
        state = _state(secret="GARDEN", guessed={"G"})
        self.assertEqual(self._title_glyph(state), self.EMOJI_STAGES["progress"])

    def test_stage_near_win(self):
        # GARDEN has 6 distinct letters; reveal 4 → 4/6 ≥ 2/3
        state = _state(secret="GARDEN", guessed={"G", "A", "R", "D"})
        self.assertEqual(self._title_glyph(state), self.EMOJI_STAGES["near_win"])

    def test_stage_win(self):
        state = _state(
            secret="CAT",
            guessed={"C", "A", "T"},
            game_over=True,
            won=True,
        )
        # Win screen starts with the win glyph in MSG_WIN_TITLE
        output = render(state)
        self.assertIn(self.EMOJI_STAGES["win"], output)

    def test_stage_loss(self):
        state = _state(
            secret="CAT",
            guessed={"Z"},
            water=0,
            game_over=True,
            won=False,
        )
        output = render(state)
        self.assertIn(self.EMOJI_STAGES["loss"], output)


class TestAsciiMode(unittest.TestCase):
    """--ascii output must be entirely ASCII (no emoji)."""

    def _has_non_ascii(self, text: str) -> bool:
        return any(ord(c) > 127 for c in text)

    def test_normal_render_ascii_mode(self):
        state = _state(secret="GARDEN", guessed={"G"}, water=5, weeds=1)
        output = render(state, ascii_mode=True)
        self.assertFalse(self._has_non_ascii(output), f"Non-ASCII in: {output!r}")

    def test_win_screen_ascii_mode(self):
        state = _state(
            secret="CAT",
            guessed={"C", "A", "T"},
            game_over=True,
            won=True,
        )
        output = render(state, ascii_mode=True)
        self.assertFalse(self._has_non_ascii(output), f"Non-ASCII in: {output!r}")

    def test_loss_screen_ascii_mode(self):
        state = _state(
            secret="CAT",
            guessed={"Z"},
            water=0,
            game_over=True,
            won=False,
        )
        output = render(state, ascii_mode=True)
        self.assertFalse(self._has_non_ascii(output), f"Non-ASCII in: {output!r}")
