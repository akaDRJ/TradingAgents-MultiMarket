from typing import Annotated


def _missing_backend_factory(backend: str, import_error: Exception):
    """Return a callable that raises a clear backend-missing error when used."""

    def _missing_backend(*args, **kwargs):
        raise RuntimeError(
            f"{backend} backend unavailable: {import_error}. "
            f"Install the missing dependency to use this vendor path."
        ) from import_error

    return _missing_backend


# Import from vendor-specific modules
try:
    from .y_finance import (
        get_YFin_data_online,
        get_stock_stats_indicators_window,
        get_fundamentals as get_yfinance_fundamentals,
        get_balance_sheet as get_yfinance_balance_sheet,
        get_cashflow as get_yfinance_cashflow,
        get_income_statement as get_yfinance_income_statement,
        get_insider_transactions as get_yfinance_insider_transactions,
    )
except ImportError as _yfinance_import_error:
    get_YFin_data_online = _missing_backend_factory("yfinance", _yfinance_import_error)
    get_stock_stats_indicators_window = _missing_backend_factory("yfinance", _yfinance_import_error)
    get_yfinance_fundamentals = _missing_backend_factory("yfinance", _yfinance_import_error)
    get_yfinance_balance_sheet = _missing_backend_factory("yfinance", _yfinance_import_error)
    get_yfinance_cashflow = _missing_backend_factory("yfinance", _yfinance_import_error)
    get_yfinance_income_statement = _missing_backend_factory("yfinance", _yfinance_import_error)
    get_yfinance_insider_transactions = _missing_backend_factory("yfinance", _yfinance_import_error)

try:
    from .yfinance_news import get_news_yfinance, get_global_news_yfinance
except ImportError as _yfinance_news_import_error:
    get_news_yfinance = _missing_backend_factory("yfinance news", _yfinance_news_import_error)
    get_global_news_yfinance = _missing_backend_factory("yfinance news", _yfinance_news_import_error)

from .alpha_vantage import (
    get_stock as get_alpha_vantage_stock,
    get_indicator as get_alpha_vantage_indicator,
    get_fundamentals as get_alpha_vantage_fundamentals,
    get_balance_sheet as get_alpha_vantage_balance_sheet,
    get_cashflow as get_alpha_vantage_cashflow,
    get_income_statement as get_alpha_vantage_income_statement,
    get_insider_transactions as get_alpha_vantage_insider_transactions,
    get_news as get_alpha_vantage_news,
    get_global_news as get_alpha_vantage_global_news,
)
from .alpha_vantage_common import AlphaVantageRateLimitError

# Configuration and routing logic
from .config import get_config

# Market extension (lazy import to avoid circular deps)
_ashare_ext = None


def _get_ashare_ext():
    global _ashare_ext
    if _ashare_ext is None:
        try:
            from tradingagents.extensions.ashare import routing as ext
            _ashare_ext = ext
        except ImportError:
            _ashare_ext = None
    return _ashare_ext

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": [
            "get_stock_data"
        ]
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": [
            "get_indicators"
        ]
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement"
        ]
    },
    "news_data": {
        "description": "News and insider data",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_transactions",
        ]
    }
}

VENDOR_LIST = [
    "yfinance",
    "alpha_vantage",
]

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_alpha_vantage_fundamentals,
        "yfinance": get_yfinance_fundamentals,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
        "yfinance": get_yfinance_cashflow,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
        "yfinance": get_yfinance_income_statement,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "yfinance": get_news_yfinance,
    },
    "get_global_news": {
        "yfinance": get_global_news_yfinance,
        "alpha_vantage": get_alpha_vantage_global_news,
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
    },
}

def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")

def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")

def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with fallback support.

    For A-share tickers, routes through the market-aware extension layer.
    For US/HK tickers, uses the existing vendor chain.
    """
    # Check if this looks like an A-share ticker (6-digit codes, .SS/.SZ suffix)
    ticker = _get_ticker_from_args(args, kwargs)
    if ticker and _is_ashare_ticker(ticker):
        ext = _get_ashare_ext()
        if ext is not None:
            result = ext.route_extension(method, *args, **kwargs)
            if result is not None:
                return result
            # Fall through to default routing if extension returns None

    # Default upstream routing for US/HK
    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)
    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    # Build fallback chain: primary vendors first, then remaining available vendors
    all_available_vendors = list(VENDOR_METHODS[method].keys())
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except AlphaVantageRateLimitError:
            continue  # Only rate limits trigger fallback

    raise RuntimeError(f"No available vendor for '{method}'")


def _get_ticker_from_args(args, kwargs) -> str | None:
    """Extract ticker symbol from positional/keyword args."""
    if args:
        return str(args[0])
    return kwargs.get("symbol") or kwargs.get("ticker")


def _is_ashare_ticker(ticker: str) -> bool:
    """Quick check if ticker looks like an A-share code.

    Checks:
    - 6-digit pure number (A-share codes)
    - Already has .SS or .SZ suffix
    """
    if not ticker:
        return False
    t = ticker.strip()
    # Already has exchange suffix
    if t.upper().endswith((".SS", ".SZ", ".BJ")):
        return True
    # 6-digit code
    if len(t) == 6 and t.isdigit():
        return True
    return False