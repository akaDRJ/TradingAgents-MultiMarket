import time
import logging

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
from stockstats import wrap
from typing import Annotated
import os

from tradingagents.extensions.market_ext import resolve_extension, route_market_extension

from .config import get_config

logger = logging.getLogger(__name__)


def yf_retry(func, max_retries=3, base_delay=2.0):
    """Execute a yfinance call with exponential backoff on rate limits.

    yfinance raises YFRateLimitError on HTTP 429 responses but does not
    retry them internally. This wrapper adds retry logic specifically
    for rate limits. Other exceptions propagate immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except YFRateLimitError:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Yahoo Finance rate limited, retrying in {delay:.0f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise


def _clean_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize a stock DataFrame for stockstats: parse dates, drop invalid rows, fill price gaps."""
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])

    price_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
    data[price_cols] = data[price_cols].apply(pd.to_numeric, errors="coerce")
    data = data.dropna(subset=["Close"])
    data[price_cols] = data[price_cols].ffill().bfill()

    return data


def _load_extension_ohlcv(symbol: str, start_str: str, end_str: str) -> pd.DataFrame:
    result = route_market_extension("get_stock_data", symbol, start_str, end_str)
    if not isinstance(result, dict):
        raise RuntimeError(f"Extension OHLCV route failed for {symbol}: {result}")

    records = result.get("data") or []
    if not records:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    df = pd.DataFrame(records)
    rename_map = {
        "date": "Date",
        "trade_date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "vol": "Volume",
    }
    df = df.rename(columns=rename_map)
    for col in ["Date", "Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            df[col] = None
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]]


def _history_window_for_symbol(symbol: str, curr_date_dt: pd.Timestamp) -> tuple[str, str]:
    end_dt = curr_date_dt.normalize()
    start_dt = end_dt - pd.DateOffset(years=5)

    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def load_ohlcv(symbol: str, curr_date: str) -> pd.DataFrame:
    """Fetch OHLCV data with caching, filtered to prevent look-ahead bias.

    Downloads 5 years of data up to today and caches per symbol for the default
    yfinance path.
    """
    config = get_config()
    curr_date_dt = pd.to_datetime(curr_date)
    start_str, end_str = _history_window_for_symbol(symbol, curr_date_dt)
    extension = resolve_extension(symbol)

    os.makedirs(config["data_cache_dir"], exist_ok=True)
    if extension is not None:
        data_file = os.path.join(
            config["data_cache_dir"],
            f"{symbol}-extension-data-{start_str}-{end_str}.csv",
        )
        if os.path.exists(data_file):
            data = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
        else:
            data = _load_extension_ohlcv(symbol, start_str, end_str)
            data.to_csv(data_file, index=False, encoding="utf-8")
    else:
        data_file = os.path.join(
            config["data_cache_dir"],
            f"{symbol}-YFin-data-{start_str}-{end_str}.csv",
        )

        if os.path.exists(data_file):
            data = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
        else:
            data = yf_retry(
                lambda: yf.download(
                    symbol,
                    start=start_str,
                    end=end_str,
                    multi_level_index=False,
                    progress=False,
                    auto_adjust=True,
                )
            )
            data = data.reset_index()
            data.to_csv(data_file, index=False, encoding="utf-8")

    data = _clean_dataframe(data)
    data = data[data["Date"] <= curr_date_dt]
    return data


def filter_financials_by_date(data: pd.DataFrame, curr_date: str) -> pd.DataFrame:
    """Drop financial statement columns (fiscal period timestamps) after curr_date.

    yfinance financial statements use fiscal period end dates as columns.
    Columns after curr_date represent future data and are removed to
    prevent look-ahead bias.
    """
    if not curr_date or data.empty:
        return data
    cutoff = pd.Timestamp(curr_date)
    mask = pd.to_datetime(data.columns, errors="coerce") <= cutoff
    return data.loc[:, mask]


class StockstatsUtils:
    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
    ):
        data = load_ohlcv(symbol, curr_date)
        df = wrap(data)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        curr_date_str = pd.to_datetime(curr_date).strftime("%Y-%m-%d")

        df[indicator]  # trigger stockstats to calculate the indicator
        matching_rows = df[df["Date"].str.startswith(curr_date_str)]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            return indicator_value
        else:
            return "N/A: Not a trading day (weekend or holiday)"
