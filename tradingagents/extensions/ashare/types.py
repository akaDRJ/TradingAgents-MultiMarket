"""Market and provider type definitions for A-share extension."""

from typing import Literal

from tradingagents.extensions.market_ext.types import Market


A_SHARE = Market.A_SHARE
HK = Market.HK
US = Market.US
UNKNOWN = Market.UNKNOWN

MarketLiteral = Literal["a_share", "hk", "us", "unknown"]
TickerNormalized = str
TickerRaw = str
