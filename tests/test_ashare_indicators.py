"""Tests for upstream-friendly A-share indicator bridging."""

import unittest
from unittest.mock import patch

import pandas as pd

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.dataflows.stockstats_utils import load_ohlcv


class AShareIndicatorBridgeTests(unittest.TestCase):
    def test_a_share_indicators_reuse_upstream_indicator_path(self):
        with patch("tradingagents.dataflows.interface.get_stock_stats_indicators_window", return_value="RSI_OK") as mock_ind:
            result = route_to_vendor("get_indicators", "600519", "rsi", "2024-01-10", 30)

        self.assertEqual(result, "RSI_OK")
        mock_ind.assert_called_once_with("600519", "rsi", "2024-01-10", 30)

    def test_load_ohlcv_converts_ashare_route_output_to_upstream_shape(self):
        fake_result = {
            "ticker": "600519.SS",
            "data": [
                {"date": "2024-01-09", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100},
                {"date": "2024-01-10", "open": 1.1, "high": 2.1, "low": 0.6, "close": 1.6, "volume": 120},
            ],
            "provider": "akshare",
            "source": "sina",
        }

        with patch("tradingagents.extensions.ashare.routing.route_extension", return_value=fake_result):
            df = load_ohlcv("600519", "2024-01-10")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), ["Date", "Open", "High", "Low", "Close", "Volume"])
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["Close"], 1.5)
        self.assertEqual(df.iloc[1]["Volume"], 120)


if __name__ == "__main__":
    unittest.main()
