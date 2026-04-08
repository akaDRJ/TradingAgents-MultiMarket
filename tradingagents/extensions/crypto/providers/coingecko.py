from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import requests

from tradingagents.extensions.crypto.normalize import normalize_ticker


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

    def _select_candidate(self, base_symbol: str, candidates: list[dict]) -> dict:
        normalized = base_symbol.lower()
        exact_symbol_matches = [candidate for candidate in candidates if candidate.get("symbol", "").lower() == normalized]
        if not exact_symbol_matches:
            raise RuntimeError(f"CoinGecko coin not found for {base_symbol}")

        def score(candidate: dict) -> tuple[int, int, int, int]:
            candidate_id = candidate.get("id", "").lower()
            candidate_name = candidate.get("name", "").lower()
            rank = candidate.get("market_cap_rank")
            return (
                0 if candidate_id == normalized else 1,
                0 if candidate_name == normalized else 1,
                0 if rank is not None else 1,
                rank if isinstance(rank, int) else 10**9,
            )

        return min(exact_symbol_matches, key=score)

    def _range_params(self, start_date: str | None, end_date: str | None) -> dict[str, int]:
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=UTC) if start_date else None
        end_dt = (
            datetime.fromisoformat(end_date).replace(tzinfo=UTC) + timedelta(days=1) - timedelta(seconds=1)
            if end_date
            else None
        )
        params: dict[str, int] = {}
        if start_dt is not None:
            params["from"] = int(start_dt.timestamp())
        if end_dt is not None:
            params["to"] = int(end_dt.timestamp())
        return params

    def _vs_currency(self, quote_symbol: str) -> str:
        if quote_symbol in {"USD", "USDT", "USDC"}:
            return "usd"
        return quote_symbol.lower()

    def _coin_id(self, ticker: str) -> str:
        instrument = normalize_ticker(ticker)
        candidates = self._get("/search", {"query": instrument.base_symbol.lower()}).get("coins", [])
        return self._select_candidate(instrument.base_symbol, candidates)["id"]

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        instrument = normalize_ticker(ticker)
        coin_id = self._coin_id(ticker)
        params = {"vs_currency": self._vs_currency(instrument.quote_symbol)}
        range_params = self._range_params(start_date, end_date)
        path = f"/coins/{coin_id}/market_chart"
        if range_params:
            path = f"/coins/{coin_id}/market_chart/range"
            params.update(range_params)
        else:
            params.update({"days": 365, "interval": "daily"})

        payload = self._get(path, params)
        prices = payload.get("prices", [])
        volumes = payload.get("total_volumes", [])
        data = []
        for index, row in enumerate(prices):
            volume = volumes[index][1] if index < len(volumes) else 0.0
            row_date = datetime.fromtimestamp(row[0] / 1000, UTC).strftime("%Y-%m-%d")
            if start_date and row_date < start_date:
                continue
            if end_date and row_date > end_date:
                continue
            data.append(
                {
                    "date": row_date,
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
