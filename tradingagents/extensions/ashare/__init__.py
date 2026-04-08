from tradingagents.extensions.market_ext.registry import get_extension, register_extension

from .market import detect_market, get_exchange_for_a_share
from .normalize import normalize_ticker
from .policy import get_provider_chain, get_unsupported_message, is_method_supported
from .registry import get_registry, register_provider
from .routing import (
    detect_market_from_ticker,
    is_ashare_market,
    is_hk_market,
    is_us_market,
    route_extension,
    route_symbol,
)
from .types import Market
from . import providers  # noqa: F401


def _matches_ashare_extension(ticker: str) -> bool:
    return detect_market(ticker) == Market.A_SHARE


def ensure_registered() -> None:
    if get_extension("ashare") is not None:
        return

    register_extension(
        name="ashare",
        match_ticker=_matches_ashare_extension,
        detect_market=detect_market,
        route_extension=route_extension,
    )


ensure_registered()
