import unittest

from tradingagents.app.analysis_request import build_default_request
from tradingagents.telegram_bot.keyboards import (
    build_choice_keyboard,
    build_main_menu_keyboard,
)
from tradingagents.telegram_bot.presentation import build_draft_summary, build_status_text


class TelegramPresentationTests(unittest.TestCase):
    def test_build_draft_summary_lists_full_cli_option_set(self):
        request = build_default_request("BTCUSDT", "2026-04-09")

        summary = build_draft_summary(request)

        self.assertIn("Ticker", summary)
        self.assertIn("Analysis Date", summary)
        self.assertIn("Output Language", summary)
        self.assertIn("LLM Provider", summary)
        self.assertIn("Quick Model", summary)
        self.assertIn("Deep Model", summary)

    def test_build_status_text_shows_running_job_fields(self):
        status = build_status_text(
            {
                "status": "running",
                "ticker": "BTCUSDT",
                "analysis_date": "2026-04-09",
                "research_depth": 5,
                "llm_provider": "openai",
                "quick_model": "gpt-5.4-mini",
                "deep_model": "gpt-5.4",
                "current_stage": "Research Team",
            }
        )

        self.assertIn("running", status)
        self.assertIn("BTCUSDT", status)
        self.assertIn("Research Team", status)

    def test_build_main_menu_keyboard_has_start_and_cancel_controls(self):
        keyboard = build_main_menu_keyboard()
        labels = [button.text for row in keyboard.inline_keyboard for button in row]

        self.assertIn("Start Analysis", labels)
        self.assertIn("Restore Last Successful", labels)
        self.assertIn("Reset To Defaults", labels)

    def test_build_choice_keyboard_includes_callback_prefix(self):
        keyboard = build_choice_keyboard(
            "pick:provider",
            [("OpenAI", "openai"), ("Anthropic", "anthropic")],
        )
        callbacks = [
            button.callback_data for row in keyboard.inline_keyboard for button in row
        ]

        self.assertIn("pick:provider:openai", callbacks)
        self.assertIn("pick:provider:anthropic", callbacks)


if __name__ == "__main__":
    unittest.main()
