"""AKShare provider for A-share market data.

Requires: pip install akshare
"""

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from .base import BaseProvider
from ..news.akshare_news import format_stock_news


class AKShareProvider(BaseProvider):
    """AKShare-based A-share data provider.

    Fetches OHLCV data via AKShare (free, no API key required).
    Uses a fallback chain because the Eastmoney-backed endpoint can be unstable
    on some hosts:
    1. Eastmoney `stock_zh_a_hist`
    2. Sina `stock_zh_a_daily`
    3. Tencent `stock_zh_a_hist_tx`
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

    def _parse_ticker(self, ticker: str) -> tuple[str, str]:
        parts = ticker.rsplit(".", 1)
        if len(parts) != 2:
            self._error(ticker, f"Invalid ticker format: {ticker}")
        return parts[0], parts[1].upper()

    def _to_prefixed_symbol(self, code: str, exchange: str) -> str:
        exchange_map = {
            "SS": "sh",
            "SZ": "sz",
            "BJ": "bj",
        }
        prefix = exchange_map.get(exchange)
        if prefix is None:
            self._error(code, f"Unsupported exchange suffix: {exchange}")
        return f"{prefix}{code}"

    def _to_em_symbol(self, code: str, exchange: str) -> str:
        exchange_map = {
            "SS": "SH",
            "SZ": "SZ",
            "BJ": "BJ",
        }
        prefix = exchange_map.get(exchange)
        if prefix is None:
            self._error(code, f"Unsupported exchange suffix: {exchange}")
        return f"{prefix}{code}"

    def _normalize_frame(self, df, source: str, ticker: str) -> Dict[str, Any]:
        if df is None or (hasattr(df, "empty") and df.empty):
            return {
                "ticker": ticker,
                "data": [],
                "provider": self.name,
                "source": source,
            }

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
            "source": source,
        }

    def _format_statement(self, ticker: str, title: str, df: pd.DataFrame, freq: str, curr_date: Optional[str] = None) -> str:
        if df is None or df.empty:
            return f"No {title.lower()} data found for symbol '{ticker}'"

        out = df.copy()
        if curr_date and "REPORT_DATE" in out.columns:
            cutoff = pd.Timestamp(curr_date)
            report_dates = pd.to_datetime(out["REPORT_DATE"], errors="coerce")
            out = out[report_dates <= cutoff]

        if freq and freq.lower() == "annual" and "REPORT_TYPE" in out.columns:
            annual_mask = out["REPORT_TYPE"].astype(str).str.contains("年报", na=False)
            annual_rows = out[annual_mask]
            if not annual_rows.empty:
                out = annual_rows

        if out.empty:
            return f"No {title.lower()} data found for symbol '{ticker}'"

        csv_string = out.to_csv(index=False)
        header = f"# {title} data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + csv_string

    def _format_fundamentals_summary(self, ticker: str, df: pd.DataFrame, curr_date: Optional[str] = None) -> str:
        if df is None or df.empty:
            return f"No fundamentals data found for symbol '{ticker}'"

        period_cols = [c for c in df.columns if str(c).isdigit() and len(str(c)) == 8]
        if not period_cols:
            return f"No fundamentals data found for symbol '{ticker}'"

        if curr_date:
            cutoff = curr_date.replace('-', '')
            usable_cols = [c for c in period_cols if str(c) <= cutoff.replace('-', '')]
            if usable_cols:
                period_cols = usable_cols

        latest_col = sorted(period_cols)[-1]
        metric_map = dict(zip(df.get("指标", []), df.get(latest_col, [])))
        interesting = [
            "归母净利润", "扣非净利润", "每股净资产", "每股未分配利润", "每股资本公积金",
            "净资产收益率", "每股经营性现金流", "销售毛利率", "销售净利率", "资产负债率",
            "流动比率", "速动比率", "基本每股收益", "每股收益-扣除", "营业总收入",
        ]
        lines = []
        for metric in interesting:
            value = metric_map.get(metric)
            if value is not None and not (isinstance(value, float) and pd.isna(value)):
                lines.append(f"{metric}: {value}")

        if not lines:
            sample_rows = df[[c for c in ["指标", latest_col] if c in df.columns]].head(15)
            lines = [f"{row['指标']}: {row[latest_col]}" for _, row in sample_rows.iterrows()]

        header = f"# Company Fundamentals for {ticker.upper()}\n"
        header += f"# Source period: {latest_col}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + "\n".join(lines)

    def get_stock_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch OHLCV bar data via AKShare fallback chain."""
        if not self._available:
            self._error(
                ticker,
                "AKShare not available: install with 'pip install akshare'. "
                "No API key required."
            )

        import akshare as ak

        code, exchange = self._parse_ticker(ticker)
        prefixed = self._to_prefixed_symbol(code, exchange)
        start_compact = (start_date or "").replace("-", "")
        end_compact = (end_date or "").replace("-", "")
        adjust = kwargs.get("adjust", "qfq")

        last_error: Exception | None = None

        # 1) Eastmoney-backed endpoint
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                start_date=start_compact,
                end_date=end_compact,
                adjust=adjust,
            )
            return self._normalize_frame(df, "eastmoney", ticker)
        except Exception as exc:
            last_error = exc

        # 2) Sina fallback
        try:
            df = ak.stock_zh_a_daily(
                symbol=prefixed,
                start_date=start_compact,
                end_date=end_compact,
                adjust=adjust,
            )
            return self._normalize_frame(df, "sina", ticker)
        except Exception as exc:
            last_error = exc

        # 3) Tencent fallback
        try:
            df = ak.stock_zh_a_hist_tx(
                symbol=prefixed,
                start_date=start_compact,
                end_date=end_compact,
                adjust=adjust,
            )
            return self._normalize_frame(df, "tencent", ticker)
        except Exception as exc:
            last_error = exc

        self._error(ticker, f"AKShare fallback chain failed: {last_error}")

    def get_fundamentals(
        self,
        ticker: str,
        curr_date: Optional[str] = None,
        **kwargs,
    ) -> str:
        if not self._available:
            self._error(ticker, "AKShare not available: install with 'pip install akshare'.")

        import akshare as ak

        code, _exchange = self._parse_ticker(ticker)
        try:
            df = ak.stock_financial_abstract(symbol=code)
            return self._format_fundamentals_summary(ticker, df, curr_date)
        except Exception as exc:
            self._error(ticker, f"AKShare fundamentals failed: {exc}")

    def get_balance_sheet(
        self,
        ticker: str,
        freq: str = "quarterly",
        curr_date: Optional[str] = None,
        **kwargs,
    ) -> str:
        if not self._available:
            self._error(ticker, "AKShare not available: install with 'pip install akshare'.")

        import akshare as ak

        code, exchange = self._parse_ticker(ticker)
        try:
            df = ak.stock_balance_sheet_by_report_em(symbol=self._to_em_symbol(code, exchange))
            return self._format_statement(ticker, "Balance Sheet", df, freq, curr_date)
        except Exception as exc:
            self._error(ticker, f"AKShare balance sheet failed: {exc}")

    def get_cashflow(
        self,
        ticker: str,
        freq: str = "quarterly",
        curr_date: Optional[str] = None,
        **kwargs,
    ) -> str:
        if not self._available:
            self._error(ticker, "AKShare not available: install with 'pip install akshare'.")

        import akshare as ak

        code, exchange = self._parse_ticker(ticker)
        try:
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=self._to_em_symbol(code, exchange))
            return self._format_statement(ticker, "Cash Flow", df, freq, curr_date)
        except Exception as exc:
            self._error(ticker, f"AKShare cash flow failed: {exc}")

    def get_income_statement(
        self,
        ticker: str,
        freq: str = "quarterly",
        curr_date: Optional[str] = None,
        **kwargs,
    ) -> str:
        if not self._available:
            self._error(ticker, "AKShare not available: install with 'pip install akshare'.")

        import akshare as ak

        code, exchange = self._parse_ticker(ticker)
        try:
            df = ak.stock_profit_sheet_by_report_em(symbol=self._to_em_symbol(code, exchange))
            return self._format_statement(ticker, "Income Statement", df, freq, curr_date)
        except Exception as exc:
            self._error(ticker, f"AKShare income statement failed: {exc}")

    def get_news(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        **kwargs,
    ) -> str:
        if not self._available:
            self._error(ticker, "AKShare not available: install with 'pip install akshare'.")

        import akshare as ak

        code, _exchange = self._parse_ticker(ticker)
        try:
            df = ak.stock_news_em(symbol=code)
            return format_stock_news(df, ticker, start_date, end_date)
        except Exception as exc:
            self._error(ticker, f"AKShare stock news failed: {exc}")


_provider_instance: Optional[AKShareProvider] = None


def get_provider() -> AKShareProvider:
    """Return the singleton AKShare provider instance."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = AKShareProvider()
    return _provider_instance
