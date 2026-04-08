"""Tests for CoinGecko crypto provider."""

import unittest
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


if __name__ == "__main__":
    unittest.main()
