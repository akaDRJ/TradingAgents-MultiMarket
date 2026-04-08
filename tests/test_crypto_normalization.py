"""Tests for crypto ticker normalization."""

import unittest

from tradingagents.extensions.crypto.normalize import normalize_ticker


class CryptoNormalizationTests(unittest.TestCase):
    def test_bare_symbol_defaults_to_usdt_pair(self):
        instrument = normalize_ticker("btc")
        self.assertEqual(instrument.base_symbol, "BTC")
        self.assertEqual(instrument.quote_symbol, "USDT")
        self.assertEqual(instrument.trading_pair, "BTCUSDT")

    def test_hyphenated_usd_pair_preserves_quote_symbol(self):
        instrument = normalize_ticker("ETH-USD")
        self.assertEqual(instrument.base_symbol, "ETH")
        self.assertEqual(instrument.quote_symbol, "USD")
        self.assertEqual(instrument.trading_pair, "ETHUSD")


if __name__ == "__main__":
    unittest.main()
