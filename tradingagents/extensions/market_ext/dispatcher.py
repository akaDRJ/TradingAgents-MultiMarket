from __future__ import annotations

from typing import Any, Optional

from .registry import list_extensions
from .types import ExtensionRegistration, Market


def _normalize_ticker(ticker: str | None) -> str:
    if not ticker:
        return ""
    return str(ticker).strip()


def resolve_extension(ticker: str) -> Optional[ExtensionRegistration]:
    raw = _normalize_ticker(ticker)
    if not raw:
        return None

    for extension in list_extensions():
        if extension.match_ticker(raw):
            return extension
    return None


def detect_market_for_ticker(ticker: str) -> Market:
    raw = _normalize_ticker(ticker)
    extension = resolve_extension(raw)
    if extension is None:
        return Market.UNKNOWN
    return extension.detect_market(raw)


def route_market_extension(method: str, *args, **kwargs) -> Any | None:
    """Route to a matching extension.

    Returns None only when no extension matches the input ticker.
    """
    ticker = None
    if args:
        ticker = str(args[0])
    else:
        ticker = kwargs.get("ticker") or kwargs.get("symbol")

    extension = resolve_extension(ticker or "")
    if extension is None:
        return None

    if not extension.supports_method(method):
        return None

    result = extension.route_extension(method, *args, **kwargs)
    if result is None:
        raise ValueError(
            f"Matched extension '{extension.name}' must return a non-None result from route_extension()."
        )
    return result
