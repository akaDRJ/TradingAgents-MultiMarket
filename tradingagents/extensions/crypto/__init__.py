from tradingagents.extensions.market_ext.module import ExtensionModule
from tradingagents.extensions.market_ext.registry import get_extension, register_module

from . import providers  # noqa: F401
from .normalize import detect_market, normalize_ticker
from .policy import DEFERRED_UPSTREAM_METHODS, get_provider_chain, get_unsupported_message, is_method_supported
from .registry import get_registry, register_provider
from .routing import route_extension

__all__ = [
    "detect_market",
    "normalize_ticker",
    "get_provider_chain",
    "get_unsupported_message",
    "is_method_supported",
    "get_registry",
    "register_provider",
    "route_extension",
    "ensure_registered",
    "get_extension_module",
    "providers",
]


def _build_market_instruction(ticker: str, analyst_kind: str) -> str:
    if detect_market(ticker).value != "crypto":
        return ""

    if analyst_kind == "fundamentals":
        return (
            " For crypto instruments, prioritize token supply, market capitalization, liquidity, "
            "market structure, and project-level fundamentals. Balance sheet style tools may be unsupported."
        )

    if analyst_kind == "social":
        return (
            " For crypto instruments, social inputs are public-web-derived and low-confidence. "
            "Use them as weak corroborating evidence, not as a primary signal."
        )

    return ""


def get_extension_module() -> ExtensionModule:
    return ExtensionModule(
        name="crypto",
        match_ticker=lambda ticker: detect_market(ticker).value == "crypto",
        detect_market=detect_market,
        supports_method=lambda method: method not in DEFERRED_UPSTREAM_METHODS,
        route_extension=route_extension,
        build_market_instruction=_build_market_instruction,
        priority=30,
    )


def ensure_registered() -> None:
    if get_extension("crypto") is not None:
        return

    register_module(get_extension_module())


ensure_registered()
