"""BaoStock provider for A-share market data.

Requires: pip install baostock
"""

from typing import Any, Dict, Optional

from .base import BaseProvider, ProviderError


class BaoStockProvider(BaseProvider):
    """BaoStock-based A-share data provider.

    Fetches OHLCV data via BaoStock (free, no API key required).
    BaoStock covers China A-shares, HK, and US markets.
    """

    name = "baostock"

    def __init__(self) -> None:
        self._available: bool = self._check_available()
        self._bs: Any = None

    def _check_available(self) -> bool:
        """Check if baostock is installed and importable."""
        try:
            import baostock as bs  # noqa: F401
            return True
        except ImportError:
            return False

    def _ensure_login(self) -> None:
        """Ensure baostock session is logged in. Raises ProviderError on failure."""
        if not self._available:
            self._error(
                "",  # ticker filled in by caller
                "BaoStock not available: install with 'pip install baostock'. "
                "No API key required."
            )
        try:
            import baostock as bs
        except ImportError:
            self._error(
                "",
                "BaoStock import failed."
            )

        # Try to get current login state by querying system date
        rs = bs.query_history_k_data_plus(
            "sh.600000",
            "date,code,open,high,low,close,volume",
            start_date="2024-01-01",
            end_date="2024-01-02",
            frequency="d",
        )
        # Non-zero error code means not logged in
        if rs.error_code != "0":
            login_rs = bs.login()
            if login_rs.error_code != "0":
                self._error(
                    "",
                    f"BaoStock login failed: {login_rs.error_msg}"
                )
        self._bs = bs

    def get_stock_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch OHLCV bar data via BaoStock.

        Args:
            ticker: Normalized ticker e.g. "600519.SS" or "000001.SZ"
            start_date: YYYY-MM-DD start date
            end_date: YYYY-MM-DD end date
            **kwargs: Extra args (limit, freq, adjust, etc.)

        Returns:
            Dict with ticker, data list, provider name.
        Raises:
            ProviderError: If BaoStock is unavailable or fails.
        """
        # Parse ticker and exchange from suffix
        parts = ticker.rsplit(".", 1)
        if len(parts) != 2:
            self._error(ticker, f"Invalid ticker format: {ticker}")

        code, exchange = parts

        # Map exchange suffix to BaoStock codes
        # sh.600000 for SSE, sz.000001 for SZSE, bj.430001 for Beijing
        exchange_map = {
            "SS": "sh",   # Shanghai
            "SZ": "sz",   # Shenzhen
            "BJ": "bj",   # Beijing
        }
        bs_market = exchange_map.get(exchange.upper())
        if bs_market is None:
            self._error(ticker, f"Unsupported exchange suffix: {exchange}")

        bs_code = f"{bs_market}.{code}"

        self._ensure_login()

        frequency = kwargs.get("freq", "d")  # d=daily, w=weekly, m=monthly
        adjust = kwargs.get("adjust", "qfq")

        # BaoStock adjust parameter: 1 for qfq, 2 for hfq, 3 for none
        adjust_map = {"qfq": "1", "hfq": "2", "none": "3"}
        bs_adjust = adjust_map.get(adjust.lower(), "1")

        import baostock as bs

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount,pctChg",
            start_date=start_date or "",
            end_date=end_date or "",
            frequency=frequency,
            adjust=bs_adjust,
        )

        if rs.error_code != "0":
            self._error(ticker, f"BaoStock query error: {rs.error_msg}")

        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        return {
            "ticker": ticker,
            "data": data_list,
            "provider": self.name,
        }


# Singleton instance
_provider_instance: Optional[BaoStockProvider] = None


def get_provider() -> BaoStockProvider:
    """Return the singleton BaoStock provider instance."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = BaoStockProvider()
    return _provider_instance
