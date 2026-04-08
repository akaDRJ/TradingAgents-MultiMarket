from __future__ import annotations

import importlib
from typing import Any, Optional

from .registry import list_extensions
from .types import ExtensionRegistration, Market


def _normalize_ticker(ticker: str | None) -> str:
    if not ticker:
        return ""
    return str(ticker).strip()


def _ensure_builtin_extensions_loaded() -> None:
    """Load built-in market extensions before resolving matches.

    This keeps extension resolution reliable even if no caller imported
    extension packages explicitly beforehand.
    """
    ashare_module = importlib.import_module("tradingagents.extensions.ashare")
    ensure_registered = getattr(ashare_module, "ensure_registered", None)
    if callable(ensure_registered):
        ensure_registered()


def resolve_extension(ticker: str) -> Optional[ExtensionRegistration]:
    _ensure_builtin_extensions_loaded()

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

    result = extension.route_extension(method, *args, **kwargs)
    if result is None:
        raise ValueError(
            f"Matched extension '{extension.name}' must return a non-None result from route_extension()."
        )
    return result
