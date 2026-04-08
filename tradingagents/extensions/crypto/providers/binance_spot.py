from __future__ import annotations

from datetime import UTC, datetime

import requests


class BinanceSpotProvider:
    name = "binance_spot"
    base_url = "https://api.binance.com"

    def __init__(self):
        self.session = requests.Session()

    def _get(self, path: str, params: dict | None = None):
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def _ensure_symbol(self, symbol: str) -> None:
        payload = self._get("/api/v3/exchangeInfo", {"symbol": symbol})
        symbols = payload.get("symbols", [])
        if not symbols or symbols[0].get("status") != "TRADING":
            raise RuntimeError(f"Binance spot symbol unavailable: {symbol}")

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        self._ensure_symbol(ticker)
        rows = self._get("/api/v3/klines", {"symbol": ticker, "interval": "1d", "limit": 365})
        data = []
        for row in rows:
            data.append(
                {
                    "date": datetime.fromtimestamp(row[0] / 1000, UTC).strftime("%Y-%m-%d"),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
            )
        return {"ticker": ticker, "data": data, "provider": self.name, "source": "binance_spot"}
