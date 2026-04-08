"""Tests for crypto interface routing through the shared market-extension seam."""

import unittest
from unittest.mock import patch

from tradingagents.dataflows.interface import route_to_vendor


class CryptoInterfaceRoutingTests(unittest.TestCase):
    def test_crypto_market_data_uses_extension_path_before_stock_vendors(self):
        fake_result = {
            "ticker": "BTCUSDT",
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
            "provider": "binance_spot",
            "source": "binance_spot",
        }

        with patch(
            "tradingagents.extensions.crypto.routing.route_extension",
            return_value=fake_result,
        ):
            result = route_to_vendor("get_stock_data", "BTCUSDT", "2024-01-01", "2024-01-31")

        self.assertEqual(result["ticker"], "BTCUSDT")
        self.assertEqual(result["provider"], "binance_spot")

    def test_crypto_news_returns_public_web_result_not_stock_vendor_result(self):
        fake_report = "## BTCUSDT News\n\n- Article: Bitcoin rallies on ETF flows"

        with patch(
            "tradingagents.extensions.crypto.routing.route_extension",
            return_value=fake_report,
        ):
            result = route_to_vendor("get_news", "BTCUSDT", "2024-01-01", "2024-01-31")

        self.assertIn("BTCUSDT News", result)


if __name__ == "__main__":
    unittest.main()
