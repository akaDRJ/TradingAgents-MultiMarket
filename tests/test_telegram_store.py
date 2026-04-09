import tempfile
import unittest
from pathlib import Path

from tradingagents.app.analysis_request import build_default_request
from tradingagents.telegram_bot.draft import DraftSession, apply_provider_change
from tradingagents.telegram_bot.store import TelegramStateStore


class TelegramStoreTests(unittest.TestCase):
    def test_store_round_trips_last_successful_request(self):
        request = build_default_request("NVDA", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_last_successful(request)

            loaded = store.load_last_successful()

            self.assertEqual(loaded.ticker, "NVDA")
            self.assertEqual(loaded.deep_model, "gpt-5.4")

    def test_store_round_trips_draft_session_metadata(self):
        request = build_default_request("BTCUSDT", "2026-04-09")
        session = DraftSession(
            request=request,
            awaiting_field="ticker",
            summary_message_id=99,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_draft_session(session)

            loaded = store.load_draft_session()

            self.assertEqual(loaded.awaiting_field, "ticker")
            self.assertEqual(loaded.summary_message_id, 99)
            self.assertEqual(loaded.request.ticker, "BTCUSDT")

    def test_apply_provider_change_replaces_models_and_clears_incompatible_effort(self):
        request = build_default_request("NVDA", "2026-04-09")
        request = request.__class__(
            **{**request.to_payload(), "openai_reasoning_effort": "high"}
        )

        updated = apply_provider_change(request, "anthropic")

        self.assertEqual(updated.llm_provider, "anthropic")
        self.assertIsNone(updated.openai_reasoning_effort)
        self.assertIsNotNone(updated.quick_model)
        self.assertIsNotNone(updated.deep_model)


if __name__ == "__main__":
    unittest.main()
