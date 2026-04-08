from __future__ import annotations

from datetime import UTC, datetime, timedelta

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

    def _window_params(self, start_date: str | None, end_date: str | None) -> dict[str, int]:
        params: dict[str, int] = {}
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=UTC) if start_date else None
        end_dt = (
            datetime.fromisoformat(end_date).replace(tzinfo=UTC) + timedelta(days=1) - timedelta(milliseconds=1)
            if end_date
            else None
        )
        if start_dt is not None:
            params["startTime"] = int(start_dt.timestamp() * 1000)
        if end_dt is not None:
            params["endTime"] = int(end_dt.timestamp() * 1000)

        if start_dt is not None and end_dt is not None:
            span_days = max(int(((end_dt + timedelta(milliseconds=1)) - start_dt).days), 1)
            params["limit"] = min(span_days, 1000)
        elif params:
            params["limit"] = 1000

        return params

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        self._ensure_symbol(ticker)
        params = {"symbol": ticker, "interval": "1d"}
        params.update(self._window_params(start_date, end_date))
        if "limit" not in params:
            params["limit"] = 365
        rows = self._get("/api/v3/klines", params)
        data = []
        for row in rows:
            row_date = datetime.fromtimestamp(row[0] / 1000, UTC).strftime("%Y-%m-%d")
            if start_date and row_date < start_date:
                continue
            if end_date and row_date > end_date:
                continue
            data.append(
                {
                    "date": row_date,
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
            )
        return {"ticker": ticker, "data": data, "provider": self.name, "source": "binance_spot"}
