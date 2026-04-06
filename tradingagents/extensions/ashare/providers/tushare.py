"""Tushare provider for A-share market data.

Requires: pip install tushare
"""

from typing import Any, Dict, Optional

from .base import BaseProvider, ProviderError


class TushareProvider(BaseProvider):
    """Tushare-based A-share data provider.

    Fetches OHLCV data via Tushare Pro API.
    Requires TUSHARE_TOKEN environment variable for Pro API access.
    Falls back to basic data if token not set (limited coverage).
    """

    name = "tushare"

    def __init__(self) -> None:
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Tushare client if possible."""
        try:
            import tushare as ts
        except ImportError:
            return

        import os

        token = os.environ.get("TUSHARE_TOKEN")
        if token:
            try:
                ts.set_token(token)
                self._client = ts.pro_api(token)
            except Exception:
                self._client = None
        else:
            # Fall back to non-pro API (limited/free tier)
            self._client = ts

    def get_stock_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch OHLCV bar data via Tushare.

        Args:
            ticker: Normalized ticker e.g. "600519.SS" or "000001.SZ"
            start_date: YYYY-MM-DD start date
            end_date: YYYY-MM-DD end date
            **kwargs: Extra args (limit, freq, etc.)

        Returns:
            Dict with ticker, data list, provider name.
        Raises:
            ProviderError: If Tushare is unavailable or fails.
        """
        if self._client is None:
            self._error(
                ticker,
                "Tushare not available: install 'tushare' package and "
                "set TUSHARE_TOKEN environment variable for full access, "
                "or pip install tushare for basic free tier."
            )

        # Parse ticker and exchange from suffix
        parts = ticker.rsplit(".", 1)
        if len(parts) != 2:
            self._error(ticker, f"Invalid ticker format: {ticker}")

        code, exchange = parts
        start = start_date or ""
        end = end_date or ""

        # Map exchange suffix to Tushare exchange codes
        # .SS = SSE (sh), .SZ = SZSE (sz), .BJ = BJ (bj)
        exchange_map = {
            "SS": "SH",
            "SZ": "SZ",
            "BJ": "BJ",
        }
        ts_exchange = exchange_map.get(exchange.upper())
        if ts_exchange is None:
            self._error(ticker, f"Unsupported exchange suffix: {exchange}")

        limit = kwargs.get("limit")
        freq = kwargs.get("freq", "daily")  # daily, weekly, monthly

        # Try Pro API first
        if hasattr(self._client, "daily"):
            # Non-pro API path
            df = self._client.daily(
                ts_code=f"{code}.{ts_exchange}",
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
            )
        else:
            # Pro API path
            df = self._client.query(
                "daily",
                ts_code=f"{code}.{ts_exchange}",
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
            )

        if df is None or (hasattr(df, "empty") and df.empty):
            return {
                "ticker": ticker,
                "data": [],
                "provider": self.name,
            }

        # Normalize to list of dicts
        records = df.to_dict("records") if hasattr(df, "to_dict") else []
        return {
            "ticker": ticker,
            "data": records,
            "provider": self.name,
        }


# Singleton instance
_provider_instance: Optional[TushareProvider] = None


def get_provider() -> TushareProvider:
    """Return the singleton Tushare provider instance."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = TushareProvider()
    return _provider_instance
