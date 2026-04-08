"""Tests for Binance spot crypto provider."""

import unittest
from datetime import UTC, datetime
from unittest.mock import Mock, patch

from tradingagents.extensions.crypto.providers.binance_spot import BinanceSpotProvider


class BinanceSpotProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.binance_spot.requests.Session.get")
    def test_get_stock_data_formats_klines_into_extension_shape(self, mock_get):
        exchange_info = Mock()
        exchange_info.raise_for_status.return_value = None
        exchange_info.json.return_value = {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING"}]}

        klines = Mock()
        klines.raise_for_status.return_value = None
        klines.json.return_value = [
            [1704067200000, "42000.0", "42500.0", "41800.0", "42300.0", "100.0", 1704153599999, "0", 0, "0", "0", "0"]
        ]

        mock_get.side_effect = [exchange_info, klines]

        provider = BinanceSpotProvider()
        result = provider.get_stock_data("BTCUSDT", "2024-01-01", "2024-01-02")

        self.assertEqual(result["ticker"], "BTCUSDT")
        self.assertEqual(result["provider"], "binance_spot")
        self.assertEqual(result["data"][0]["close"], 42300.0)
        klines_params = mock_get.call_args_list[1].kwargs["params"]
        self.assertEqual(
            klines_params["startTime"],
            int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000),
        )
        self.assertEqual(
            klines_params["endTime"],
            int(datetime(2024, 1, 2, 23, 59, 59, 999000, tzinfo=UTC).timestamp() * 1000),
        )


if __name__ == "__main__":
    unittest.main()
