import unittest
from unittest import mock

from word_garden.game import GameState
from word_garden import main as main_module
from word_garden.main import GOODBYE, PROMPT, main
from word_garden.ui import (
    GROWTH_STAGES,
    LOSS_BODY,
    LOSS_HEADER,
    LOSS_REVEAL_TEMPLATE,
    STAGE_LOSS,
    STAGE_NEAR_WIN,
    STAGE_PROGRESS,
    STAGE_START,
    STAGE_WIN,
    WATER_EMOJI,
    WEED_EMOJI,
    WIN_BODY,
    WIN_HEADER,
    WIN_REVEAL_TEMPLATE,
    growth_stage,
    loss_screen,
    render,
    win_screen,
)


def _make_state(**kwargs) -> GameState:
    """Build a GameState directly with pinned values (no randomness)."""
    defaults = dict(
        secret_word="GARDEN",
        guessed_letters=set(),
        remaining_water=6,
        weed_count=0,
        max_water=6,
    )
    defaults.update(kwargs)
    return GameState(**defaults)


# ---------------------------------------------------------------------------
# render — emoji mode
# ---------------------------------------------------------------------------

class TestRenderEmoji(unittest.TestCase):
    def test_contains_title_and_word_and_guesses(self):
        state = _make_state(secret_word="GARDEN", guessed_letters={"G", "R"})
        out = render(state, ascii_mode=False)
        self.assertIn("Word Garden", out)
        self.assertIn("G _ R _ _ _", out)
        # Guessed letters sorted and space-separated.
        self.assertIn("Guessed:", out)
        self.assertIn("G R", out)

    def test_water_has_label_count_and_symbols(self):
        state = _make_state(remaining_water=4, max_water=6)
        out = render(state, ascii_mode=False)
        self.assertIn("Water:", out)
        self.assertIn("4/6", out)
        self.assertIn(WATER_EMOJI * 4, out)

    def test_weeds_has_label_count_and_symbols(self):
        state = _make_state(weed_count=2)
        out = render(state, ascii_mode=False)
        self.assertIn("Weeds:", out)
        self.assertIn("2", out)
        self.assertIn(WEED_EMOJI * 2, out)

    def test_status_message_shown_when_present(self):
        state = _make_state(status_message="No match. A weed appears.")
        out = render(state, ascii_mode=False)
        self.assertIn("No match. A weed appears.", out)

    def test_empty_status_message_not_rendered_as_blank_feedback(self):
        # A fresh game has no feedback line; the last line is the weeds row.
        state = _make_state()
        out = render(state, ascii_mode=False)
        self.assertTrue(out.rstrip().endswith(render(state).splitlines()[-1]))
        self.assertNotIn("None", out)


# ---------------------------------------------------------------------------
# render — ASCII mode (must be pure ASCII)
# ---------------------------------------------------------------------------

class TestRenderAscii(unittest.TestCase):
    def test_output_is_pure_ascii(self):
        state = _make_state(
            secret_word="GARDEN",
            guessed_letters={"G", "A", "Z"},
            remaining_water=5,
            weed_count=1,
            status_message="No match. A weed appears.",
        )
        out = render(state, ascii_mode=True)
        self.assertTrue(out.isascii(), f"non-ASCII characters found: {out!r}")

    def test_ascii_has_labels_count_and_no_emoji(self):
        state = _make_state(remaining_water=4, max_water=6, weed_count=2)
        out = render(state, ascii_mode=True)
        self.assertIn("Water:", out)
        self.assertIn("4/6", out)
        self.assertIn("Weeds:", out)
        self.assertNotIn(WATER_EMOJI, out)
        self.assertNotIn(WEED_EMOJI, out)

    def test_ascii_win_loss_screens_pure_ascii(self):
        won = _make_state(
            guessed_letters=set("GARDEN"), game_over=True, won=True
        )
        lost = _make_state(remaining_water=0, weed_count=6, game_over=True)
        self.assertTrue(win_screen(won, ascii_mode=True).isascii())
        self.assertTrue(loss_screen(lost, ascii_mode=True).isascii())


# ---------------------------------------------------------------------------
# growth stages (SPEC §10): start / progress / near-win / win / loss
# ---------------------------------------------------------------------------

class TestGrowthStages(unittest.TestCase):
    def test_start_when_nothing_revealed(self):
        state = _make_state(secret_word="GARDEN", guessed_letters=set())
        self.assertEqual(growth_stage(state), STAGE_START)
        self.assertIn(GROWTH_STAGES[STAGE_START]["emoji"], render(state))

    def test_progress_when_some_revealed(self):
        state = _make_state(secret_word="GARDEN", guessed_letters={"G", "A"})
        self.assertEqual(growth_stage(state), STAGE_PROGRESS)
        self.assertIn(GROWTH_STAGES[STAGE_PROGRESS]["emoji"], render(state))

    def test_near_win_when_one_letter_left(self):
        # GARDEN with all but N revealed → exactly one secret letter remains.
        state = _make_state(secret_word="GARDEN", guessed_letters={"G", "A", "R", "D", "E"})
        self.assertEqual(growth_stage(state), STAGE_NEAR_WIN)
        self.assertIn(GROWTH_STAGES[STAGE_NEAR_WIN]["emoji"], render(state))

    def test_win_stage_when_won(self):
        state = _make_state(guessed_letters=set("GARDEN"), game_over=True, won=True)
        self.assertEqual(growth_stage(state), STAGE_WIN)

    def test_loss_stage_when_lost(self):
        state = _make_state(remaining_water=0, weed_count=6, game_over=True, won=False)
        self.assertEqual(growth_stage(state), STAGE_LOSS)

    def test_wrong_guesses_alone_do_not_count_as_progress(self):
        # Only wrong letters guessed → no secret letter revealed → still start.
        state = _make_state(secret_word="GARDEN", guessed_letters={"Z", "Q"})
        self.assertEqual(growth_stage(state), STAGE_START)


# ---------------------------------------------------------------------------
# win / loss screens (SPEC §6.6 / §6.7)
# ---------------------------------------------------------------------------

class TestEndScreens(unittest.TestCase):
    def test_win_screen_names_word_and_message(self):
        state = _make_state(secret_word="GARDEN", guessed_letters=set("GARDEN"),
                            game_over=True, won=True)
        out = win_screen(state, ascii_mode=False)
        self.assertIn(WIN_HEADER, out)
        self.assertIn(WIN_REVEAL_TEMPLATE.format(word="GARDEN"), out)
        self.assertIn(WIN_BODY, out)
        self.assertIn("GARDEN", out)

    def test_loss_screen_reveals_secret_word(self):
        state = _make_state(secret_word="PLANET", remaining_water=0, weed_count=4,
                            game_over=True, won=False)
        out = loss_screen(state, ascii_mode=False)
        self.assertIn(LOSS_HEADER, out)
        self.assertIn(LOSS_REVEAL_TEMPLATE.format(word="PLANET"), out)
        self.assertIn(LOSS_BODY, out)
        self.assertIn("PLANET", out)


# ---------------------------------------------------------------------------
# end-to-end main() runs with injected I/O
# ---------------------------------------------------------------------------

class _Recorder:
    """Collects output_fn calls; serves scripted input_fn responses."""

    def __init__(self, inputs):
        self._inputs = iter(inputs)
        self.outputs: list[str] = []

    def input_fn(self, prompt=""):
        return next(self._inputs)

    def output_fn(self, text=""):
        self.outputs.append(str(text))

    @property
    def text(self) -> str:
        return "\n".join(self.outputs)


class TestMainEndToEnd(unittest.TestCase):
    def test_full_win_shows_win_screen(self):
        rec = _Recorder(list("GARDEN"))
        with mock.patch("word_garden.words.select_word", return_value="GARDEN"):
            code = main(["--difficulty", "normal"],
                        input_fn=rec.input_fn, output_fn=rec.output_fn)
        self.assertEqual(code, 0)
        self.assertIn(WIN_HEADER, rec.text)
        self.assertIn(WIN_REVEAL_TEMPLATE.format(word="GARDEN"), rec.text)

    def test_full_loss_shows_loss_screen_with_word(self):
        # Six wrong guesses (none in GARDEN) exhaust the normal water of 6.
        rec = _Recorder(list("ZQXJKW"))
        with mock.patch("word_garden.words.select_word", return_value="GARDEN"):
            code = main(["--difficulty", "normal"],
                        input_fn=rec.input_fn, output_fn=rec.output_fn)
        self.assertEqual(code, 0)
        self.assertIn(LOSS_HEADER, rec.text)
        self.assertIn(LOSS_REVEAL_TEMPLATE.format(word="GARDEN"), rec.text)

    def test_invalid_input_reprompts_without_consuming_water(self):
        # Two invalid inputs, then win. Game still won → invalids cost no turn.
        rec = _Recorder(["", "7", "!"] + list("GARDEN"))
        with mock.patch("word_garden.words.select_word", return_value="GARDEN"):
            code = main([], input_fn=rec.input_fn, output_fn=rec.output_fn)
        self.assertEqual(code, 0)
        # Validation messages surfaced.
        self.assertIn("Please enter a single letter.", rec.text)
        self.assertIn("That is not a letter.", rec.text)
        # And the game still reached the win screen.
        self.assertIn(WIN_HEADER, rec.text)

    def test_ascii_mode_run_is_pure_ascii(self):
        rec = _Recorder(list("GARDEN"))
        with mock.patch("word_garden.words.select_word", return_value="GARDEN"):
            main(["--ascii"], input_fn=rec.input_fn, output_fn=rec.output_fn)
        self.assertTrue(rec.text.isascii(), f"non-ASCII in output: {rec.text!r}")

    def test_difficulty_easy_sets_water_to_eight(self):
        # First rendered frame should show the easy starting water of 8/8.
        rec = _Recorder(list("GARDEN"))
        with mock.patch("word_garden.words.select_word", return_value="GARDEN"):
            main(["--difficulty", "easy"],
                 input_fn=rec.input_fn, output_fn=rec.output_fn)
        self.assertIn("8/8", rec.outputs[0])

    def test_eof_exits_cleanly_with_goodbye(self):
        def eof_input(prompt=""):
            raise EOFError

        outputs = []
        with mock.patch("word_garden.words.select_word", return_value="GARDEN"):
            code = main([], input_fn=eof_input, output_fn=lambda t="": outputs.append(str(t)))
        self.assertEqual(code, 0)
        self.assertIn(GOODBYE, "\n".join(outputs))

    def test_keyboard_interrupt_exits_cleanly_with_goodbye(self):
        def interrupt_input(prompt=""):
            raise KeyboardInterrupt

        outputs = []
        with mock.patch("word_garden.words.select_word", return_value="GARDEN"):
            code = main([], input_fn=interrupt_input,
                        output_fn=lambda t="": outputs.append(str(t)))
        self.assertEqual(code, 0)
        self.assertIn(GOODBYE, "\n".join(outputs))

    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"], input_fn=lambda p="": "", output_fn=lambda t="": None)
        self.assertEqual(ctx.exception.code, 0)

    def test_bad_difficulty_exits_two(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--difficulty", "impossible"],
                 input_fn=lambda p="": "", output_fn=lambda t="": None)
        self.assertEqual(ctx.exception.code, 2)

    def test_prompt_text_is_passed_to_input(self):
        seen = []

        def capture_input(prompt=""):
            seen.append(prompt)
            return next(letters)

        letters = iter("GARDEN")
        with mock.patch("word_garden.words.select_word", return_value="GARDEN"):
            main([], input_fn=capture_input, output_fn=lambda t="": None)
        self.assertEqual(seen[0], PROMPT)


if __name__ == "__main__":
    unittest.main()
