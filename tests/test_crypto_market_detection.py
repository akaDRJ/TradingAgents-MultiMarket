"""Tests for crypto market detection."""

import unittest
from unittest.mock import patch

import tradingagents.dataflows.interface as interface
from tradingagents.extensions import ashare, crypto
from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.extensions.market_ext import get_extension, reset_extensions_for_test, resolve_extension
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


class CryptoNewsRoutingTests(unittest.TestCase):
    def setUp(self):
        reset_extensions_for_test()
        ashare.ensure_registered()
        crypto.ensure_registered()

    def tearDown(self):
        reset_extensions_for_test()
        ashare.ensure_registered()
        crypto.ensure_registered()

    def test_crypto_unsupported_method_returns_extension_message(self):
        extension = resolve_extension("BTCUSDT")
        self.assertIsNotNone(extension)
        self.assertEqual(extension.name, "crypto")

        with (
            patch.dict(
                interface.VENDOR_METHODS["get_insider_transactions"],
                {"alpha_vantage": lambda *args, **kwargs: "UPSTREAM_INSIDER_RESULT"},
                clear=True,
            ),
            patch("tradingagents.dataflows.interface.get_vendor", return_value="alpha_vantage"),
        ):
            out = route_to_vendor("get_insider_transactions", "BTCUSDT")

        self.assertIn("not supported", out)
        self.assertIn("crypto", out)

    def test_route_to_vendor_routes_crypto_news_through_extension_seam(self):
        extension = resolve_extension("BTCUSDT")
        self.assertIsNotNone(extension)
        self.assertEqual(extension.name, "crypto")
        self.assertIsNotNone(get_extension("crypto"))

        with (
            patch("tradingagents.dataflows.interface.route_market_extension", return_value="EXTENSION_NEWS") as mock_route,
            patch(
                "tradingagents.dataflows.interface.get_vendor",
                side_effect=AssertionError("crypto news should not fall back to stock vendors"),
            ),
        ):
            out = route_to_vendor("get_news", "BTCUSDT", "2024-01-01", "2024-01-10")

        mock_route.assert_called_once_with("get_news", "BTCUSDT", "2024-01-01", "2024-01-10")
        self.assertEqual(out, "EXTENSION_NEWS")


if __name__ == "__main__":
    unittest.main()
