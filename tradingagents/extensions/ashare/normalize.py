"""Ticker normalization for A-share extension.

Provides a unified normalization interface that:
- Accepts raw user input (6-digit A-share, HK codes, US tickers)
- Returns a normalized form with exchange suffix for internal routing
- Preserves existing suffixes when already present
"""

import re
from typing import Optional

from .market import detect_market, get_exchange_for_a_share, normalize_index_ticker
from .types import Market


def normalize_ticker(ticker: str) -> tuple[str, Market]:
    """Normalize a ticker string to internal form with explicit exchange suffix.

    Args:
        ticker: Raw user-provided ticker (e.g. "600519", "0700.HK", "AAPL")

    Returns:
        Tuple of (normalized_ticker, detected_market)

    Examples:
        normalize_ticker("600519")      -> ("600519.SS", Market.A_SHARE)
        normalize_ticker("000001")      -> ("000001.SZ", Market.A_SHARE)
        normalize_ticker("0700.HK")     -> ("0700.HK", Market.HK)
        normalize_ticker("AAPL")        -> ("AAPL", Market.US)
        normalize_ticker("aapl")        -> ("AAPL", Market.US)
    """
    if not ticker:
        return "", Market.UNKNOWN

    raw = ticker.strip()
    canonical_index = normalize_index_ticker(raw)
    if canonical_index is not None:
        return canonical_index, Market.INDEX

    market = detect_market(raw)

    if market == Market.A_SHARE:
        # Already has suffix
        upper = raw.upper()
        if upper.endswith(".SH"):
            return upper[:-3] + ".SS", market
        if upper.endswith((".SS", ".SZ", ".BJ")):
            return upper, market
        # Try to determine exchange
        suffix = get_exchange_for_a_share(raw)
        if suffix:
            return raw.upper() + suffix, market
        # Fallback: guess based on leading digits
        if raw.startswith(("600", "601", "603", "605", "688")):
            return raw.upper() + ".SS", market
        return raw.upper() + ".SZ", market

    if market == Market.HK:
        # Normalize: remove existing .HK, pad to 5 digits if needed
        clean = re.sub(r"\.HK$", "", raw, flags=re.IGNORECASE).strip()
        clean = clean.zfill(5)  # Pad 700 -> 00700
        return clean.upper() + ".HK", market

    if market == Market.US:
        # Uppercase, strip any accidental suffixes not expected
        # Preserve explicit exchange-qualified inputs like CNC.TO.
        upper = raw.upper()
        if upper.endswith(".OB"):
            return upper, market
        if "." in upper:
            return upper, market
        return upper, market

    return raw, market
