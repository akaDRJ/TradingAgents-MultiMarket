"""AKShare provider for A-share market data.

Requires: pip install akshare
"""

from typing import Any, Dict, Optional

from .base import BaseProvider, ProviderError


class AKShareProvider(BaseProvider):
    """AKShare-based A-share data provider.

    Fetches OHLCV data via AKShare (free, no API key required).
    """

    name = "akshare"

    def __init__(self) -> None:
        self._available: bool = self._check_available()

    def _check_available(self) -> bool:
        """Check if akshare is installed and importable."""
        try:
            import akshare as ak  # noqa: F401
            return True
        except ImportError:
            return False

    def get_stock_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch OHLCV bar data via AKShare.

        Args:
            ticker: Normalized ticker e.g. "600519.SS" or "000001.SZ"
            start_date: YYYY-MM-DD start date
            end_date: YYYY-MM-DD end date
            **kwargs: Extra args (limit, freq, etc.)

        Returns:
            Dict with ticker, data list, provider name.
        Raises:
            ProviderError: If AKShare is unavailable or fails.
        """
        if not self._available:
            self._error(
                ticker,
                "AKShare not available: install with 'pip install akshare'. "
                "No API key required."
            )

        import akshare as ak

        # Parse ticker and exchange from suffix
        parts = ticker.rsplit(".", 1)
        if len(parts) != 2:
            self._error(ticker, f"Invalid ticker format: {ticker}")

        code, exchange = parts

        # Map exchange suffix to AKShare stock code format
        # AKShare uses: sh + 6-digit code for SSE, sz + 6-digit for SZSE
        exchange_map = {
            "SS": "sh",   # Shanghai
            "SZ": "sz",   # Shenzhen
            "BJ": "bj",   # Beijing
        }
        ak_market = exchange_map.get(exchange.upper())
        if ak_market is None:
            self._error(ticker, f"Unsupported exchange suffix: {exchange}")

        stock_id = f"{ak_market}{code}"

        # Use akshare stock_zh_a_hist for A-share historical data
        df = ak.stock_zh_a_hist(
            symbol=code,
            start_date=start_date or "",
            end_date=end_date or "",
            adjust=kwargs.get("adjust", "qfq"),
        )

        if df is None or (hasattr(df, "empty") and df.empty):
            return {
                "ticker": ticker,
                "data": [],
                "provider": self.name,
            }

        # AKShare returns DataFrame with columns like:
        # 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
        # Normalize to snake_case
        rename_map = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "pct_change",
            "涨跌额": "change",
            "换手率": "turnover",
        }

        if hasattr(df, "rename"):
            df = df.rename(columns=rename_map)

        records = df.to_dict("records") if hasattr(df, "to_dict") else []
        return {
            "ticker": ticker,
            "data": records,
            "provider": self.name,
        }


# Singleton instance
_provider_instance: Optional[AKShareProvider] = None


def get_provider() -> AKShareProvider:
    """Return the singleton AKShare provider instance."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = AKShareProvider()
    return _provider_instance
