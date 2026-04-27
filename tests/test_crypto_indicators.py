"""Tests for crypto indicator OHLCV windowing."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from tradingagents.dataflows.stockstats_utils import load_ohlcv
from tradingagents.extensions.market_ext.types import Market


class CryptoIndicatorWindowTests(unittest.TestCase):
    def test_load_ohlcv_uses_five_year_extension_history_ending_at_curr_date(self):
        fake_extension = SimpleNamespace(detect_market=lambda ticker: Market.CRYPTO)
        fake_result = {
            "ticker": "KASUSDT",
            "data": [
                {
                    "date": "2021-03-10",
                    "open": 1.0,
                    "high": 1.1,
                    "low": 0.9,
                    "close": 1.05,
                    "volume": 100.0,
                },
                {
                    "date": "2026-03-10",
                    "open": 2.0,
                    "high": 2.1,
                    "low": 1.9,
                    "close": 2.05,
                    "volume": 120.0,
                },
            ],
            "provider": "coingecko",
            "source": "coingecko",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "tradingagents.dataflows.stockstats_utils.get_config",
                    return_value={"data_cache_dir": tmpdir},
                ),
                patch(
                    "tradingagents.dataflows.stockstats_utils.resolve_extension",
                    return_value=fake_extension,
                ),
                patch(
                    "tradingagents.dataflows.stockstats_utils.route_market_extension",
                    return_value=fake_result,
                ) as mock_route,
            ):
                df = load_ohlcv("KASUSDT", "2026-03-10")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(
            mock_route.call_args.args,
            ("get_stock_data", "KASUSDT", "2021-03-10", "2026-03-10"),
        )
        self.assertEqual(df.iloc[0]["Date"].strftime("%Y-%m-%d"), "2021-03-10")
        self.assertEqual(df.iloc[-1]["Close"], 2.05)

    def test_load_ohlcv_caches_extension_data_between_indicator_calls(self):
        fake_extension = SimpleNamespace(detect_market=lambda ticker: Market.CRYPTO)
        fake_result = {
            "ticker": "KASUSDT",
            "data": [
                {
                    "date": "2025-10-10",
                    "open": 1.0,
                    "high": 1.1,
                    "low": 0.9,
                    "close": 1.05,
                    "volume": 100.0,
                },
                {
                    "date": "2026-03-10",
                    "open": 2.0,
                    "high": 2.1,
                    "low": 1.9,
                    "close": 2.05,
                    "volume": 120.0,
                },
            ],
            "provider": "coingecko",
            "source": "coingecko",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "tradingagents.dataflows.stockstats_utils.get_config",
                    return_value={"data_cache_dir": tmpdir},
                ),
                patch(
                    "tradingagents.dataflows.stockstats_utils.resolve_extension",
                    return_value=fake_extension,
                ),
                patch(
                    "tradingagents.dataflows.stockstats_utils.route_market_extension",
                    return_value=fake_result,
                ) as mock_route,
            ):
                first = load_ohlcv("KASUSDT", "2026-03-10")
                second = load_ohlcv("KASUSDT", "2026-03-10")

                cache_files = list(Path(tmpdir).glob("KASUSDT-*-data-*.csv"))

        self.assertEqual(mock_route.call_count, 1)
        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 2)
        self.assertEqual(len(cache_files), 1)


if __name__ == "__main__":
    unittest.main()
