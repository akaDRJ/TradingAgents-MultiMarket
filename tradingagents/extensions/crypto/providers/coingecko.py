from __future__ import annotations

import os
from datetime import UTC, datetime

import requests


class CoinGeckoProvider:
    name = "coingecko"
    base_url = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.session = requests.Session()
        api_key = os.getenv("COINGECKO_API_KEY")
        if api_key:
            self.session.headers.update({"x-cg-demo-api-key": api_key})

    def _get(self, path: str, params: dict | None = None):
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def _coin_id(self, ticker: str) -> str:
        base_symbol = ticker.replace("USDT", "").replace("USDC", "").replace("USD", "").lower()
        candidates = self._get("/search", {"query": base_symbol}).get("coins", [])
        if not candidates:
            raise RuntimeError(f"CoinGecko coin not found for {ticker}")
        return candidates[0]["id"]

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        coin_id = self._coin_id(ticker)
        payload = self._get(f"/coins/{coin_id}/market_chart", {"vs_currency": "usd", "days": 365, "interval": "daily"})
        prices = payload.get("prices", [])
        volumes = payload.get("total_volumes", [])
        data = []
        for index, row in enumerate(prices):
            volume = volumes[index][1] if index < len(volumes) else 0.0
            data.append(
                {
                    "date": datetime.fromtimestamp(row[0] / 1000, UTC).strftime("%Y-%m-%d"),
                    "open": float(row[1]),
                    "high": float(row[1]),
                    "low": float(row[1]),
                    "close": float(row[1]),
                    "volume": float(volume),
                }
            )
        return {"ticker": ticker, "data": data, "provider": self.name, "source": "coingecko"}

    def get_fundamentals(self, ticker: str, curr_date: str | None = None, **kwargs):
        coin_id = self._coin_id(ticker)
        payload = self._get(f"/coins/{coin_id}")
        market_data = payload.get("market_data", {})
        return (
            f"## {payload.get('name', ticker)} Fundamentals\n\n"
            f"- Market Cap: {market_data.get('market_cap', {}).get('usd', 'N/A')}\n"
            f"- 24h Volume: {market_data.get('total_volume', {}).get('usd', 'N/A')}\n"
            f"- Circulating Supply: {market_data.get('circulating_supply', 'N/A')}\n"
            f"- Total Supply: {market_data.get('total_supply', 'N/A')}\n"
        )
