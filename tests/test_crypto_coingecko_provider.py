"""Tests for CoinGecko crypto provider."""

import unittest
from datetime import UTC, datetime
from unittest.mock import Mock, patch

from tradingagents.extensions.crypto.providers.coingecko import CoinGeckoProvider


class CoinGeckoProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.coingecko.requests.Session.get")
    def test_get_fundamentals_returns_market_cap_and_supply_context(self, mock_get):
        coin_lookup = Mock()
        coin_lookup.raise_for_status.return_value = None
        coin_lookup.json.return_value = {"coins": [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}]}

        coin_detail = Mock()
        coin_detail.raise_for_status.return_value = None
        coin_detail.json.return_value = {
            "name": "Bitcoin",
            "symbol": "btc",
            "market_cap_rank": 1,
            "market_data": {
                "current_price": {"usd": 70000},
                "market_cap": {"usd": 1300000000000},
                "total_volume": {"usd": 25000000000},
                "circulating_supply": 19600000,
                "total_supply": 21000000,
            },
        }

        mock_get.side_effect = [coin_lookup, coin_detail]

        provider = CoinGeckoProvider()
        result = provider.get_fundamentals("BTCUSDT", curr_date="2024-01-01")

        self.assertIn("Bitcoin", result)
        self.assertIn("Market Cap", result)
        self.assertIn("Circulating Supply", result)

    @patch("tradingagents.extensions.crypto.providers.coingecko.requests.Session.get")
    def test_get_stock_data_uses_range_endpoint_and_end_suffix_symbol_parsing(self, mock_get):
        coin_lookup = Mock()
        coin_lookup.raise_for_status.return_value = None
        coin_lookup.json.return_value = {
            "coins": [
                {"id": "busd-wrong", "symbol": "b", "name": "Broken Old Parsing Result"},
                {"id": "binance-usd", "symbol": "busd", "name": "Binance USD"},
            ]
        }

        chart = Mock()
        chart.raise_for_status.return_value = None
        chart.json.return_value = {
            "prices": [[1704067200000, 1.0], [1704153600000, 1.01]],
            "total_volumes": [[1704067200000, 1000.0], [1704153600000, 1200.0]],
        }

        mock_get.side_effect = [coin_lookup, chart]

        provider = CoinGeckoProvider()
        result = provider.get_stock_data("BUSDUSDT", "2024-01-01", "2024-01-02")

        self.assertEqual(result["ticker"], "BUSDUSDT")
        search_params = mock_get.call_args_list[0].kwargs["params"]
        self.assertEqual(search_params["query"], "busd")
        range_call = mock_get.call_args_list[1]
        self.assertTrue(range_call.args[0].endswith("/coins/binance-usd/market_chart/range"))
        self.assertEqual(
            range_call.kwargs["params"]["from"],
            int(datetime(2024, 1, 1, tzinfo=UTC).timestamp()),
        )
        self.assertEqual(
            range_call.kwargs["params"]["to"],
            int(datetime(2024, 1, 2, 23, 59, 59, tzinfo=UTC).timestamp()),
        )


if __name__ == "__main__":
    unittest.main()
