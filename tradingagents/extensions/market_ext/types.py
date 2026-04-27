from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class Market(Enum):
    A_SHARE = "a_share"
    INDEX = "index"
    HK = "hk"
    US = "us"
    CRYPTO = "crypto"
    UNKNOWN = "unknown"

    def __repr__(self) -> str:
        return f"<Market.{self.name}>"


@dataclass(frozen=True)
class ExtensionRegistration:
    name: str
    match_ticker: Callable[[str], bool]
    detect_market: Callable[[str], Market]
    supports_method: Callable[[str], bool]
    route_extension: Callable[..., Any]
    build_instrument_context: Callable[[str], Optional[str]]
    build_market_instruction: Callable[[str, str], str]
    build_analyst_report: Callable[[str, str, str], Optional[str]]
    priority: int = 100
