"""Market-aware routing entry point for A-share extension.

This module provides the routing facade that integrates with
tradingagents/dataflows/interface.py via the extension seam.
"""

from typing import Any

from .normalize import normalize_ticker
from .policy import get_provider_chain, is_method_supported, get_unsupported_message
from .registry import get_registry
from .types import Market


def route_extension(method: str, *args, **kwargs) -> Any:
    """Route a data method call through the extension layer.

    This entry point accepts the same argument shape as
    ``dataflows/interface.py``: the first positional argument is the raw ticker.
    The extension normalizes the ticker internally, detects the market, and then
    invokes the provider chain using the normalized ticker plus remaining args.

    Args:
        method: Data method name (e.g. ``"get_stock_data"``)
        *args: Positional args where ``args[0]`` is the raw ticker symbol
        **kwargs: Keyword args for the underlying provider

    Returns:
        Provider result or unsupported/error message. Returns ``None`` when no
        ticker is available so the upstream router can fall back safely.
    """
    if not args:
        return None

    raw_ticker = str(args[0])
    remaining_args = args[1:]
    normalized_ticker, market = normalize_ticker(raw_ticker)

    if market == Market.UNKNOWN:
        return get_unsupported_message(method, market)

    if not is_method_supported(method, market):
        return get_unsupported_message(method, market)

    chain = get_provider_chain(method, market)
    if not chain:
        return get_unsupported_message(method, market)

    registry = get_registry()

    for provider in chain:
        impl = registry.get(provider, method)
        if impl is None:
            continue
        try:
            return impl(normalized_ticker, *remaining_args, **kwargs)
        except Exception:
            continue

    return f"Error: All providers failed for '{method}' on '{normalized_ticker}'"


def route_symbol(method: str, raw_ticker: str, *args, **kwargs) -> tuple[str, Market, Any]:
    """Full routing pipeline: normalize + detect + route.

    Returns:
        Tuple of ``(normalized_ticker, market, result)``.
    """
    normalized, market = normalize_ticker(raw_ticker)
    result = route_extension(method, raw_ticker, *args, **kwargs)
    return normalized, market, result


def is_ashare_market(market: Market) -> bool:
    """Return True if market is A-share."""
    return market in {Market.A_SHARE, Market.INDEX}


def is_hk_market(market: Market) -> bool:
    """Return True if market is HK."""
    return market == Market.HK


def is_us_market(market: Market) -> bool:
    """Return True if market is US."""
    return market == Market.US


def detect_market_from_ticker(ticker: str) -> Market:
    """Convenience wrapper around market detection."""
    _, market = normalize_ticker(ticker)
    return market
