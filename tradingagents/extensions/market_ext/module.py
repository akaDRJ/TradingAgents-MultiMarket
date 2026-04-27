from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .types import Market


@dataclass(frozen=True)
class ExtensionModule:
    name: str
    match_ticker: Callable[[str], bool]
    detect_market: Callable[[str], Market]
    route_extension: Callable[..., Any]
    supports_method: Callable[[str], bool] = lambda method: True
    build_instrument_context: Callable[[str], Optional[str]] = lambda ticker: None
    build_market_instruction: Callable[[str, str], str] = lambda ticker, analyst_kind: ""
    build_analyst_report: Callable[[str, str, str], Optional[str]] = (
        lambda ticker, analyst_kind, current_date: None
    )
    enabled: bool = True
    priority: int = 100
