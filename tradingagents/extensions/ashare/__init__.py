"""A-share (China) market extension for TradingAgents.

This extension layer provides:
- Market detection (A-share, HK, US)
- Ticker normalization (6-digit codes, exchange suffixes)
- Provider routing policy with fallback chains
- Data providers (Tushare, AKShare, BaoStock) for get_stock_data

Usage:
    from tradingagents.extensions.ashare import normalize_ticker, detect_market
    normalized, market = normalize_ticker("600519")

    # Providers auto-register on first import of the ashare package
    from tradingagents.extensions.ashare import route_extension
    result = route_extension("get_stock_data", "600519")
"""

from .market import detect_market, get_exchange_for_a_share
from .normalize import normalize_ticker
from .policy import (
    get_provider_chain,
    is_method_supported,
    get_unsupported_message,
)
from .registry import get_registry, register_provider
from .routing import (
    route_extension,
    route_symbol,
    is_ashare_market,
    is_hk_market,
    is_us_market,
    detect_market_from_ticker,
)
from .types import Market

# Import providers to trigger auto-registration
# Each provider registers its get_stock_data method with the global registry
from . import providers  # noqa: F401

__all__ = [
    # types
    "Market",
    # market detection
    "detect_market",
    "get_exchange_for_a_share",
    "detect_market_from_ticker",
    # normalization
    "normalize_ticker",
    # policy
    "get_provider_chain",
    "is_method_supported",
    "get_unsupported_message",
    # registry
    "get_registry",
    "register_provider",
    # routing
    "route_extension",
    "route_symbol",
    "is_ashare_market",
    "is_hk_market",
    "is_us_market",
    # providers
    "providers",
]
