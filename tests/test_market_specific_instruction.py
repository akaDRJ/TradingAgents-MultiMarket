"""Tests for market-aware analyst prompt helper behavior."""

import unittest

from tradingagents.agents.utils.agent_utils import build_market_specific_instruction


class MarketSpecificInstructionTests(unittest.TestCase):
    def test_crypto_fundamentals_instruction_mentions_token_metrics(self):
        note = build_market_specific_instruction("BTCUSDT", "fundamentals")
        self.assertIn("token", note.lower())
        self.assertIn("supply", note.lower())

    def test_crypto_social_instruction_mentions_low_confidence(self):
        note = build_market_specific_instruction("BTCUSDT", "social")
        self.assertIn("low-confidence", note.lower())

    def test_equity_instruction_is_empty(self):
        self.assertEqual(build_market_specific_instruction("AAPL", "fundamentals"), "")


if __name__ == "__main__":
    unittest.main()
