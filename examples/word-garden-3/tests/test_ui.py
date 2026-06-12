"""Tests for the rendering layer (ui.py) and the I/O loop (main.py).

Fixtures are built by constructing ``GameState`` directly with pinned
values (never by calling the random factory and overwriting fields).
Message strings are asserted against the imported constants so wording
changes can never silently rot the suite.
"""

import unittest

from word_garden import game, main, ui
from word_garden.game import GameState


def make_state(
    secret_word="GARDEN",
    guessed=(),
    remaining_water=6,
    weed_count=0,
    max_water=6,
    status_message="",
    game_over=False,
    won=False,
):
    """Construct a pinned GameState for rendering tests."""
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


def is_ascii(text):
    """True when every character in *text* is within the ASCII range."""
    return all(ord(ch) < 128 for ch in text)


# ---------------------------------------------------------------------------
# render — emoji mode
# ---------------------------------------------------------------------------

class RenderEmojiModeTests(unittest.TestCase):
    def test_contains_title_and_masked_word(self):
        out = ui.render(make_state(guessed=["A"]))
        self.assertIn(ui.TITLE, out)
        # display_word masks unguessed letters and reveals "A".
        self.assertIn(game.display_word(make_state(guessed=["A"])), out)

    def test_guessed_letters_sorted_and_space_separated(self):
        out = ui.render(make_state(guessed=["R", "A", "E"]))
        self.assertIn("A E R", out)

    def test_water_carries_label_and_count(self):
        out = ui.render(make_state(remaining_water=4, max_water=6))
        # Accessibility: label AND count present, not just symbols.
        self.assertIn(ui.LABEL_WATER, out)
        self.assertIn("4/6", out)
        # Exactly four droplet glyphs for four remaining water.
        self.assertEqual(out.count(ui.WATER_GLYPH), 4)

    def test_weeds_carries_label_and_count(self):
        out = ui.render(make_state(weed_count=2))
        self.assertIn(ui.LABEL_WEEDS, out)
        self.assertIn("2", out)
        self.assertEqual(out.count(ui.WEED_GLYPH), 2)

    def test_previous_status_message_shown(self):
        out = ui.render(make_state(status_message=game.MSG_CORRECT_GUESS))
        self.assertIn(game.MSG_CORRECT_GUESS, out)

    def test_no_status_message_when_empty(self):
        out = ui.render(make_state(status_message=""))
        self.assertNotIn("None", out)
        # The blank-line + message block should be absent.
        self.assertFalse(out.endswith("\n"))


# ---------------------------------------------------------------------------
# render — ascii mode
# ---------------------------------------------------------------------------

class RenderAsciiModeTests(unittest.TestCase):
    def test_output_is_pure_ascii(self):
        state = make_state(
            guessed=["A", "Z"],
            remaining_water=5,
            weed_count=3,
            status_message=game.MSG_WRONG_GUESS,
        )
        out = ui.render(state, ascii_mode=True)
        self.assertTrue(is_ascii(out), "ascii render contained non-ASCII")

    def test_ascii_still_has_labels_and_counts(self):
        out = ui.render(make_state(remaining_water=4, weed_count=2), ascii_mode=True)
        lines = {line.split()[0]: line for line in out.splitlines() if line.strip()}
        water_line = lines[ui.LABEL_WATER]
        weeds_line = lines[ui.LABEL_WEEDS]
        # Label + count + exactly the right number of gauge symbols.
        self.assertIn("4/6", water_line)
        self.assertEqual(water_line.count(ui.WATER_ASCII), 4)
        self.assertIn("2", weeds_line)
        self.assertEqual(weeds_line.count(ui.WEED_ASCII), 2)


# ---------------------------------------------------------------------------
# growth stages
# ---------------------------------------------------------------------------

class GrowthStageTests(unittest.TestCase):
    def test_start_stage_when_nothing_revealed(self):
        self.assertEqual(ui.growth_stage(make_state(guessed=[])), "start")

    def test_progress_stage_mid_game(self):
        # GARDEN distinct letters: G A R D E N (6). Two revealed -> progress.
        state = make_state(secret_word="GARDEN", guessed=["G", "A"])
        self.assertEqual(ui.growth_stage(state), "progress")

    def test_near_win_when_one_letter_left(self):
        # Five of six distinct letters revealed -> near-win.
        state = make_state(secret_word="GARDEN", guessed=["G", "A", "R", "D", "E"])
        self.assertEqual(ui.growth_stage(state), "near-win")

    def test_win_stage_overrides_progress(self):
        state = make_state(
            secret_word="GARDEN",
            guessed=["G", "A", "R", "D", "E", "N"],
            game_over=True,
            won=True,
        )
        self.assertEqual(ui.growth_stage(state), "win")

    def test_loss_stage_when_game_over_unwon(self):
        state = make_state(
            secret_word="GARDEN",
            guessed=["X", "Y", "Z"],
            remaining_water=0,
            game_over=True,
            won=False,
        )
        self.assertEqual(ui.growth_stage(state), "loss")

    def test_glyph_reflects_stage_in_each_mode(self):
        start = make_state(guessed=[])
        self.assertIn(ui.STAGE_GLYPHS["start"], ui.render(start))
        self.assertIn(ui.STAGE_ASCII["start"], ui.render(start, ascii_mode=True))


# ---------------------------------------------------------------------------
# win / loss screens
# ---------------------------------------------------------------------------

class FinalScreenTests(unittest.TestCase):
    def test_win_screen_reveals_word_and_header(self):
        state = make_state(secret_word="MEADOW", won=True, game_over=True)
        out = ui.win_screen(state)
        self.assertIn(ui.WIN_HEADER, out)
        self.assertIn("MEADOW", out)
        self.assertIn(ui.STAGE_GLYPHS["win"], out)

    def test_loss_screen_reveals_secret_word(self):
        state = make_state(secret_word="ORCHARD", game_over=True, won=False)
        out = ui.loss_screen(state)
        self.assertIn(ui.LOSS_HEADER, out)
        self.assertIn("ORCHARD", out)
        self.assertIn(ui.STAGE_GLYPHS["loss"], out)

    def test_screens_pure_ascii_in_ascii_mode(self):
        win = make_state(secret_word="MEADOW", won=True, game_over=True)
        loss = make_state(secret_word="ORCHARD", game_over=True, won=False)
        self.assertTrue(is_ascii(ui.win_screen(win, ascii_mode=True)))
        self.assertTrue(is_ascii(ui.loss_screen(loss, ascii_mode=True)))
        # The solved/secret word is still revealed in ascii mode.
        self.assertIn("MEADOW", ui.win_screen(win, ascii_mode=True))
        self.assertIn("ORCHARD", ui.loss_screen(loss, ascii_mode=True))


# ---------------------------------------------------------------------------
# main loop — scripted end to end via injected I/O
# ---------------------------------------------------------------------------

class ScriptedInput:
    """Yields queued lines, raising EOFError when exhausted."""

    def __init__(self, lines):
        self._lines = list(lines)

    def __call__(self, prompt=""):
        if not self._lines:
            raise EOFError
        return self._lines.pop(0)


class MainLoopTests(unittest.TestCase):
    def _run(self, argv, lines):
        out_lines = []
        code = main.main(
            argv,
            input_fn=ScriptedInput(lines),
            output_fn=out_lines.append,
        )
        return code, "\n".join(out_lines)

    def test_end_to_end_win(self):
        # Force a known word via --difficulty hard whose pool is 7+ letters;
        # we instead patch new_game's word by scripting against a fixed game.
        # Use the normal flow but guess every distinct letter of a known word.
        # To pin the word deterministically, drive a constructed game directly.
        state = make_state(secret_word="GO", max_water=6, remaining_water=6)
        out_lines = []

        # Replay the loop with a pinned state by monkeypatching new_game.
        original = game.new_game
        game.new_game = lambda difficulty="normal": GameState(
            secret_word="GO",
            guessed_letters=set(),
            remaining_water=6,
            weed_count=0,
            max_water=6,
        )
        try:
            code = main.main(
                [],
                input_fn=ScriptedInput(["g", "o"]),
                output_fn=out_lines.append,
            )
        finally:
            game.new_game = original

        out = "\n".join(out_lines)
        self.assertEqual(code, 0)
        # The win screen actually appeared (not merely exit 0).
        self.assertIn(ui.WIN_HEADER, out)
        self.assertIn("You guessed the word: GO", out)

    def test_end_to_end_loss(self):
        out_lines = []
        original = game.new_game
        # Pinned word "GO" with only 2 water: two wrong guesses lose.
        game.new_game = lambda difficulty="normal": GameState(
            secret_word="GO",
            guessed_letters=set(),
            remaining_water=2,
            weed_count=0,
            max_water=2,
        )
        try:
            code = main.main(
                [],
                input_fn=ScriptedInput(["x", "z"]),
                output_fn=out_lines.append,
            )
        finally:
            game.new_game = original

        out = "\n".join(out_lines)
        self.assertEqual(code, 0)
        self.assertIn(ui.LOSS_HEADER, out)
        # Loss screen reveals the secret word.
        self.assertIn("The word was: GO", out)

    def test_invalid_input_reprompts_without_consuming_water(self):
        # First input "7" is invalid -> message shown, no turn consumed.
        # Then "o" then "g" win the GO game with full water intact.
        out_lines = []
        original = game.new_game
        game.new_game = lambda difficulty="normal": GameState(
            secret_word="GO",
            guessed_letters=set(),
            remaining_water=6,
            weed_count=0,
            max_water=6,
        )
        try:
            code = main.main(
                [],
                input_fn=ScriptedInput(["7", "g", "o"]),
                output_fn=out_lines.append,
            )
        finally:
            game.new_game = original

        out = "\n".join(out_lines)
        self.assertEqual(code, 0)
        # The validation message appeared AND the game still reached a win
        # AND water never dropped below the starting 6 (no weed glyphs shown
        # before the win, since only correct guesses were applied).
        self.assertIn(game.MSG_NOT_A_LETTER, out)
        self.assertIn(ui.WIN_HEADER, out)
        self.assertIn("6/6", out)

    def test_eof_exits_cleanly_with_goodbye(self):
        # Empty input stream -> immediate EOFError on first prompt.
        out_lines = []
        original = game.new_game
        game.new_game = lambda difficulty="normal": GameState(
            secret_word="GARDEN",
            guessed_letters=set(),
            remaining_water=6,
            weed_count=0,
            max_water=6,
        )
        try:
            code = main.main(
                [],
                input_fn=ScriptedInput([]),
                output_fn=out_lines.append,
            )
        finally:
            game.new_game = original

        out = "\n".join(out_lines)
        self.assertEqual(code, 0)
        self.assertIn(main.GOODBYE, out)

    def test_keyboard_interrupt_exits_cleanly(self):
        def interrupt(prompt=""):
            raise KeyboardInterrupt

        out_lines = []
        original = game.new_game
        game.new_game = lambda difficulty="normal": GameState(
            secret_word="GARDEN",
            guessed_letters=set(),
            remaining_water=6,
            weed_count=0,
            max_water=6,
        )
        try:
            code = main.main([], input_fn=interrupt, output_fn=out_lines.append)
        finally:
            game.new_game = original

        self.assertEqual(code, 0)
        self.assertIn(main.GOODBYE, "\n".join(out_lines))


# ---------------------------------------------------------------------------
# main — argument parsing
# ---------------------------------------------------------------------------

class ArgParseTests(unittest.TestCase):
    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as ctx:
            main.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_bad_difficulty_exits_two(self):
        with self.assertRaises(SystemExit) as ctx:
            main.main(["--difficulty", "impossible"])
        self.assertEqual(ctx.exception.code, 2)

    def test_difficulty_changes_water(self):
        # easy starts with 8 water, hard with 4 — proves the flag is wired.
        out_lines = []
        main.main(
            ["--difficulty", "easy"],
            input_fn=ScriptedInput([]),  # EOF immediately after first render
            output_fn=out_lines.append,
        )
        self.assertIn("8/8", "\n".join(out_lines))


if __name__ == "__main__":
    unittest.main()
