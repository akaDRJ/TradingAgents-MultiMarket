"""Tests for crypto market detection."""

import unittest

from tradingagents.extensions import ashare, crypto
from tradingagents.extensions.market_ext import get_extension, reset_extensions_for_test
from tradingagents.extensions.crypto.normalize import detect_market
from tradingagents.extensions.market_ext.types import Market


class CryptoMarketDetectionTests(unittest.TestCase):
    def test_known_bare_symbols_are_crypto(self):
        self.assertEqual(detect_market("BTC"), Market.CRYPTO)
        self.assertEqual(detect_market("ETH"), Market.CRYPTO)

    def test_pair_inputs_are_crypto(self):
        self.assertEqual(detect_market("BTCUSDT"), Market.CRYPTO)
        self.assertEqual(detect_market("ETH-USD"), Market.CRYPTO)

    def test_equity_tickers_do_not_accidentally_route_to_crypto(self):
        self.assertEqual(detect_market("AAPL"), Market.UNKNOWN)
        self.assertEqual(detect_market("600519"), Market.UNKNOWN)


class CryptoExtensionRegistrationTests(unittest.TestCase):
    def tearDown(self):
        reset_extensions_for_test()
        ashare.ensure_registered()
        crypto.ensure_registered()

    def test_crypto_can_re_register_after_extension_reset(self):
        reset_extensions_for_test()
        self.assertIsNone(get_extension("crypto"))

        crypto.ensure_registered()

        extension = get_extension("crypto")
        self.assertIsNotNone(extension)
        self.assertEqual(extension.name, "crypto")


if __name__ == "__main__":
    unittest.main()
