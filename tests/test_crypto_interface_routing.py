"""Tests for crypto interface routing through the shared market-extension seam."""

import unittest
from unittest.mock import patch

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.extensions import ashare, crypto
from tradingagents.extensions.market_ext import register_extension, reset_extensions_for_test
from tradingagents.extensions.market_ext.types import Market


class CryptoInterfaceRoutingTests(unittest.TestCase):
    def setUp(self):
        reset_extensions_for_test()
        self.route_calls = []

        def fake_crypto_route(method: str, *args, **kwargs):
            self.route_calls.append((method, args, kwargs))
            if method == "get_stock_data":
                return {
                    "ticker": args[0],
                    "data": [
                        {
                            "date": "2024-01-01",
                            "open": 1.0,
                            "high": 2.0,
                            "low": 0.5,
                            "close": 1.5,
                            "volume": 10.0,
                        }
                    ],
                    "provider": "fake_crypto_extension",
                    "source": "fake_crypto_extension",
                }
            if method == "get_news":
                return f"## {args[0]} News\n\n- Article: Extension seam routing works"
            return f"unsupported:{method}"

        register_extension(
            name="crypto_test",
            match_ticker=lambda ticker: str(ticker).upper().endswith("USDT"),
            detect_market=lambda ticker: Market.CRYPTO,
            supports_method=lambda method: method in {"get_stock_data", "get_news"},
            route_extension=fake_crypto_route,
        )

    def tearDown(self):
        reset_extensions_for_test()
        ashare.ensure_registered()
        crypto.ensure_registered()

    def test_crypto_market_data_uses_extension_path_before_stock_vendors(self):
        with patch(
            "tradingagents.dataflows.interface.get_vendor",
            side_effect=AssertionError("crypto stock data should not use stock vendors"),
        ):
            result = route_to_vendor("get_stock_data", "BTCUSDT", "2024-01-01", "2024-01-31")

        self.assertEqual(result["ticker"], "BTCUSDT")
        self.assertEqual(result["provider"], "fake_crypto_extension")
        self.assertEqual(
            self.route_calls,
            [("get_stock_data", ("BTCUSDT", "2024-01-01", "2024-01-31"), {})],
        )

    def test_crypto_news_uses_extension_path_before_stock_vendors(self):
        with patch(
            "tradingagents.dataflows.interface.get_vendor",
            side_effect=AssertionError("crypto news should not use stock vendors"),
        ):
            result = route_to_vendor("get_news", "BTCUSDT", "2024-01-01", "2024-01-31")

        self.assertIn("BTCUSDT News", result)
        self.assertEqual(
            self.route_calls,
            [("get_news", ("BTCUSDT", "2024-01-01", "2024-01-31"), {})],
        )


if __name__ == "__main__":
    unittest.main()
