"""Provider routing policy for A-share extension.

Defines which data methods route to which providers per market.
Each method has a chain of providers to try in order.
"""

from typing import Dict, List

from .types import Market


# Per-market method -> provider chain mapping
# None means the method is unsupported for that market
MARKET_POLICY: Dict[Market, Dict[str, List[str]]] = {
    Market.A_SHARE: {
        "get_stock_data": ["tushare", "akshare", "baostock"],
        "get_indicators": ["tushare", "akshare"],
        "get_fundamentals": ["tushare", "akshare"],
        "get_balance_sheet": ["tushare", "akshare"],
        "get_cashflow": ["tushare", "akshare"],
        "get_income_statement": ["tushare", "akshare"],
        "get_news": ["akshare", "google_cn"],
        "get_global_news": ["google_cn"],
        "get_insider_transactions": None,  # Unsupported for A-share
    },
    Market.INDEX: {
        "get_stock_data": ["akshare", "tushare", "baostock"],
        "get_indicators": ["akshare", "tushare"],
        "get_fundamentals": None,
        "get_balance_sheet": None,
        "get_cashflow": None,
        "get_income_statement": None,
        "get_news": None,
        "get_global_news": None,
        "get_insider_transactions": None,
    },
    Market.HK: {
        "get_stock_data": ["yfinance", "akshare"],
        "get_indicators": ["yfinance", "akshare"],
        "get_fundamentals": ["yfinance"],
        "get_balance_sheet": ["yfinance"],
        "get_cashflow": ["yfinance"],
        "get_income_statement": ["yfinance"],
        "get_news": ["yfinance", "google_cn"],
        "get_global_news": ["google_cn"],
        "get_insider_transactions": ["yfinance"],
    },
    # US continues to use existing vendors (yfinance/alpha_vantage)
    Market.US: {},
    Market.UNKNOWN: {},
}


def get_provider_chain(method: str, market: Market) -> List[str] | None:
    """Get the provider chain for a method in a given market.

    Args:
        method: Data method name (e.g. "get_stock_data")
        market: Detected market

    Returns:
        List of provider names in priority order, or None if unsupported
    """
    if market not in MARKET_POLICY:
        return None
    return MARKET_POLICY[market].get(method)


def is_method_supported(method: str, market: Market) -> bool:
    """Check if a method is supported for the given market."""
    chain = get_provider_chain(method, market)
    return chain is not None and len(chain) > 0


def get_unsupported_message(method: str, market: Market) -> str:
    """Return a user-facing message for unsupported methods."""
    return f"Method '{method}' is not supported for {market.value} markets."
