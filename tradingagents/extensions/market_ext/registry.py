from __future__ import annotations

from typing import Dict, Iterable, Optional

from .module import ExtensionModule
from .types import ExtensionRegistration


_EXTENSIONS: Dict[str, ExtensionRegistration] = {}


def register_module(module: ExtensionModule) -> None:
    if not module.enabled:
        _EXTENSIONS.pop(module.name, None)
        return

    _EXTENSIONS[module.name] = ExtensionRegistration(
        name=module.name,
        match_ticker=module.match_ticker,
        detect_market=module.detect_market,
        supports_method=module.supports_method,
        route_extension=module.route_extension,
        build_instrument_context=module.build_instrument_context,
        build_market_instruction=module.build_market_instruction,
        build_analyst_report=module.build_analyst_report,
        priority=module.priority,
    )


def register_extension(
    name: str,
    match_ticker,
    detect_market,
    route_extension,
    supports_method=None,
    build_instrument_context=None,
    build_market_instruction=None,
    build_analyst_report=None,
    priority=100,
) -> None:
    register_module(ExtensionModule(
        name=name,
        match_ticker=match_ticker,
        detect_market=detect_market,
        supports_method=supports_method or (lambda method: True),
        route_extension=route_extension,
        build_instrument_context=build_instrument_context or (lambda ticker: None),
        build_market_instruction=build_market_instruction or (lambda ticker, analyst_kind: ""),
        build_analyst_report=build_analyst_report or (
            lambda ticker, analyst_kind, current_date: None
        ),
        priority=priority,
    ))


def get_extension(name: str) -> Optional[ExtensionRegistration]:
    return _EXTENSIONS.get(name)


def list_extensions() -> Iterable[ExtensionRegistration]:
    return sorted(_EXTENSIONS.values(), key=lambda extension: extension.priority)


def reset_extensions_for_test() -> None:
    _EXTENSIONS.clear()
