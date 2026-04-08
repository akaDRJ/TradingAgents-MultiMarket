from __future__ import annotations

from tradingagents.extensions.market_ext.types import Market

from .normalize import detect_market, normalize_ticker
from .policy import get_provider_chain, get_unsupported_message, is_method_supported
from .registry import get_registry


def route_extension(method: str, *args, **kwargs):
    if not args:
        return None

    instrument = normalize_ticker(str(args[0]))
    market = detect_market(str(args[0]))

    if market != Market.CRYPTO:
        return None

    if not is_method_supported(method, market):
        return get_unsupported_message(method, market)

    for provider in get_provider_chain(method, market):
        impl = get_registry().get(provider, method)
        if impl is None:
            continue
        try:
            return impl(instrument.trading_pair, *args[1:], **kwargs)
        except Exception:
            continue

    return f"Error: All providers failed for '{method}' on '{instrument.trading_pair}'"
