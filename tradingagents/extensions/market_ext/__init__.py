import importlib

from .dispatcher import detect_market_for_ticker, resolve_extension, route_market_extension
from .registry import get_extension, list_extensions, register_extension, reset_extensions_for_test
from .types import ExtensionRegistration, Market

__all__ = [
    "ExtensionRegistration",
    "Market",
    "detect_market_for_ticker",
    "get_extension",
    "list_extensions",
    "register_extension",
    "reset_extensions_for_test",
    "resolve_extension",
    "route_market_extension",
]


def _bootstrap_builtin_extensions() -> None:
    for module_name in ("tradingagents.extensions.ashare", "tradingagents.extensions.crypto"):
        extension_module = importlib.import_module(module_name)
        ensure_registered = getattr(extension_module, "ensure_registered", None)
        if callable(ensure_registered):
            ensure_registered()


_bootstrap_builtin_extensions()
