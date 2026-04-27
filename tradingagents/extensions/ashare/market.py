"""Market detection for A-share extension.

Rules (applied in order):
1. If already has .HK suffix -> HK
2. If already has .SS or .SZ suffix -> A_SHARE
3. If 6 digits:
   - 000xxx / 001xxx / 002xxx / 003xxx -> A_SHARE (SZSE)
   - 600xxx / 601xxx / 603xxx / 605xxx / 688xxx -> A_SHARE (SSE)
   - 300xxx / 301xxx -> A_SHARE (ChiNext)
   - 430xxx / 830xxx / 870xxx -> A_SHARE (Beijing/BGEM)
4. If 5 digits starting 7/8/9 -> HK
5. If ends with .OB -> US (OTC)
6. Otherwise -> US (assumed NYSE/NASDAQ)
"""

import re
from typing import Optional

from .types import Market


_INDEX_CANONICAL = "000001.SS"
_INDEX_DISPLAY_NAME = "上证指数"
_INDEX_ALIASES = {
    "上证指数": _INDEX_CANONICAL,
    "沪指": _INDEX_CANONICAL,
    "上证综指": _INDEX_CANONICAL,
    "SSE COMPOSITE": _INDEX_CANONICAL,
    "SSE COMPOSITE INDEX": _INDEX_CANONICAL,
    "SHANGHAI COMPOSITE": _INDEX_CANONICAL,
    "SHANGHAI COMPOSITE INDEX": _INDEX_CANONICAL,
    "000001.SS": _INDEX_CANONICAL,
    "000001.SH": _INDEX_CANONICAL,
}
_INDEX_ALIASES_UPPER = {key.upper(): value for key, value in _INDEX_ALIASES.items()}


# A-share code ranges by exchange
# SSE (Shanghai Stock Exchange): 600-605, 688 (STAR)
# SZSE (Shenzhen Stock Exchange): 000, 001, 002, 003, 300 (ChiNext), 301
# Beijing: 430, 830, 870
_A_SHARE_SSE_PATTERNS = [
    re.compile(r"^60[0-5]\d{3}$"),   # 600xxx-605xxx
    re.compile(r"^688\d{3}$"),        # 688xxx (STAR Market)
    re.compile(r"^601\d{3}$"),        # 601xxx
    re.compile(r"^603\d{3}$"),        # 603xxx
    re.compile(r"^605\d{3}$"),        # 605xxx
]
_A_SHARE_SZSE_PATTERNS = [
    re.compile(r"^00[0-3]\d{3}$"),    # 000xxx-003xxx
    re.compile(r"^30[01]\d{3}$"),    # 300xxx, 301xxx (ChiNext)
]
_A_SHARE_BJ_PATTERNS = [
    re.compile(r"^43[0-2]\d{3}$"),   # 430xxx (Beijing)
    re.compile(r"^83[0-2]\d{3}$"),   # 830xxx (Beijing)
    re.compile(r"^87[0-1]\d{3}$"),   # 870xxx (Beijing)
]
_HK_PATTERNS = [
    re.compile(r"^\d{5}$"),           # 5 digits: 07000, 00902, etc.
]
_HK_SUFFIX = re.compile(r"\.HK$", re.IGNORECASE)


def normalize_index_ticker(ticker: str) -> Optional[str]:
    """Return the canonical ticker for a supported index alias."""
    if not ticker:
        return None

    raw = ticker.strip()
    if not raw:
        return None

    return _INDEX_ALIASES.get(raw) or _INDEX_ALIASES_UPPER.get(raw.upper())


def get_index_display_name(ticker: str) -> Optional[str]:
    """Return the human-friendly index name for a supported index ticker."""
    if normalize_index_ticker(ticker) == _INDEX_CANONICAL:
        return _INDEX_DISPLAY_NAME
    return None


def detect_market(ticker: str) -> Market:
    """Detect market from a ticker string.

    Args:
        ticker: Raw ticker input (may already have exchange suffix)

    Returns:
        Detected Market enum value
    """
    if not ticker:
        return Market.UNKNOWN

    t = ticker.strip()
    if not t:
        return Market.UNKNOWN
    upper = t.upper()

    if normalize_index_ticker(t):
        return Market.INDEX

    # Already has explicit suffix
    if _HK_SUFFIX.search(t):
        return Market.HK
    if upper.endswith(".SS"):
        return Market.A_SHARE
    if upper.endswith(".SH"):
        return Market.A_SHARE
    if upper.endswith(".SZ"):
        return Market.A_SHARE
    if upper.endswith(".BJ"):
        return Market.A_SHARE

    # 6-digit A-share codes
    if re.match(r"^\d{6}$", t):
        for p in _A_SHARE_SSE_PATTERNS:
            if p.match(t):
                return Market.A_SHARE
        for p in _A_SHARE_SZSE_PATTERNS:
            if p.match(t):
                return Market.A_SHARE
        for p in _A_SHARE_BJ_PATTERNS:
            if p.match(t):
                return Market.A_SHARE
        # 6-digit not matched above but could still be A-share
        # (some ranges may not be covered; default to A_SHARE for 6-digit
        #  unless clearly US pattern like 000xxx where 000 is not valid A-share)
        return Market.A_SHARE

    # 5-digit HK codes
    if re.match(r"^\d{5}$", t):
        return Market.HK

    # 4-digit codes (rare, possibly HK)
    if re.match(r"^\d{4}$", t):
        return Market.HK

    # OTC suffix
    if upper.endswith(".OB"):
        return Market.US

    # Default to US (NYSE/NASDAQ standard tickers)
    return Market.US


def get_exchange_for_a_share(ticker: str) -> Optional[str]:
    """Return SSE or SZSE suffix for A-share ticker, or None if not A-share.

    Args:
        ticker: Normalized or raw A-share ticker

    Returns:
        ".SS" for Shanghai, ".SZ" for Shenzhen, or None if unrecognized
    """
    t = ticker.strip()
    # Already has suffix
    if t.upper().endswith(".SS"):
        return ".SS"
    if t.upper().endswith(".SH"):
        return ".SS"
    if t.upper().endswith(".SZ"):
        return ".SZ"

    if len(t) != 6 or not t.isdigit():
        return None

    # SSE: 600, 601, 603, 605, 688
    if t.startswith(("600", "601", "603", "605", "688")):
        return ".SS"
    # SZSE: 000, 001, 002, 003, 300, 301
    if t.startswith(("000", "001", "002", "003", "300", "301")):
        return ".SZ"
    # Beijing: 430, 830, 870
    if t.startswith(("430", "830", "870")):
        return ".BJ"
    return None
