import tempfile
import unittest
from pathlib import Path

from tradingagents.app.analysis_request import build_default_request
from tradingagents.telegram_bot.draft import DraftSession
from tradingagents.telegram_bot.service import TelegramControlService
from tradingagents.telegram_bot.store import TelegramStateStore


class TelegramServiceTests(unittest.TestCase):
    def test_begin_analyze_uses_last_successful_when_no_draft_exists(self):
        request = build_default_request("BTCUSDT", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_last_successful(request)
            service = TelegramControlService(store)

            response = service.begin_analyze("2026-04-09")

            self.assertEqual(response["mode"], "draft")
            self.assertIn("BTCUSDT", response["text"])

    def test_begin_analyze_returns_switch_prompt_when_job_is_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_active_job({"status": "running", "ticker": "NVDA"})
            service = TelegramControlService(store)

            response = service.begin_analyze("2026-04-09")

            self.assertEqual(response["mode"], "confirm_switch")
            self.assertIn("Cancel current and switch", response["text"])

    def test_apply_text_input_updates_ticker_and_clears_waiting_flag(self):
        request = build_default_request("SPY", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_draft_session(DraftSession(request=request, awaiting_field="ticker"))
            service = TelegramControlService(store)

            session = service.apply_text_input("BTCUSDT")

            self.assertEqual(session.request.ticker, "BTCUSDT")
            self.assertIsNone(session.awaiting_field)

    def test_apply_provider_choice_resets_models_to_provider_defaults(self):
        request = build_default_request("SPY", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_draft_session(DraftSession(request=request))
            service = TelegramControlService(store)

            session = service.apply_provider_choice("anthropic")

            self.assertEqual(session.request.llm_provider, "anthropic")
            self.assertEqual(session.request.quick_model, "claude-sonnet-4-6")
            self.assertEqual(session.request.deep_model, "claude-opus-4-6")

    def test_apply_choice_updates_research_depth(self):
        request = build_default_request("SPY", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_draft_session(DraftSession(request=request))
            service = TelegramControlService(store)

            session = service.apply_choice("research_depth", "5")

            self.assertEqual(session.request.research_depth, 5)


if __name__ == "__main__":
    unittest.main()
