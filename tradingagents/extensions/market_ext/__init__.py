from .dispatcher import (
    build_analyst_report_for_ticker,
    build_instrument_context_for_ticker,
    build_market_instruction_for_ticker,
    detect_market_for_ticker,
    resolve_extension,
    route_market_extension,
)
from .loader import configured_module_names, load_extension_modules
from .module import ExtensionModule
from .registry import (
    get_extension,
    list_extensions,
    register_extension,
    register_module,
    reset_extensions_for_test,
)
from .types import ExtensionRegistration, Market

__all__ = [
    "ExtensionRegistration",
    "ExtensionModule",
    "Market",
    "build_analyst_report_for_ticker",
    "build_instrument_context_for_ticker",
    "build_market_instruction_for_ticker",
    "configured_module_names",
    "detect_market_for_ticker",
    "get_extension",
    "list_extensions",
    "load_extension_modules",
    "register_extension",
    "register_module",
    "reset_extensions_for_test",
    "resolve_extension",
    "route_market_extension",
]


def _bootstrap_builtin_extensions() -> None:
    load_extension_modules(strict=False)


_bootstrap_builtin_extensions()
