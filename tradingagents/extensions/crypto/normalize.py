from __future__ import annotations

from dataclasses import dataclass

from tradingagents.extensions.market_ext.types import Market


KNOWN_BARE_SYMBOLS = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK"}
KNOWN_QUOTES = ("USDT", "USDC", "USD")


@dataclass(frozen=True)
class CryptoInstrument:
    raw_input: str
    base_symbol: str
    quote_symbol: str
    trading_pair: str
    market: Market = Market.CRYPTO


def detect_market(ticker: str) -> Market:
    if not ticker:
        return Market.UNKNOWN

    raw = str(ticker).strip().upper()
    if not raw:
        return Market.UNKNOWN

    compact = raw.replace("-", "")
    for quote in KNOWN_QUOTES:
        if compact.endswith(quote) and len(compact) > len(quote):
            return Market.CRYPTO

    if raw in KNOWN_BARE_SYMBOLS:
        return Market.CRYPTO

    return Market.UNKNOWN


def normalize_ticker(ticker: str) -> CryptoInstrument:
    raw = str(ticker).strip().upper()
    compact = raw.replace("-", "")

    if detect_market(raw) != Market.CRYPTO:
        raise ValueError(f"Unsupported crypto instrument: {ticker}")

    for quote in KNOWN_QUOTES:
        if compact.endswith(quote) and len(compact) > len(quote):
            base = compact[: -len(quote)]
            return CryptoInstrument(
                raw_input=raw,
                base_symbol=base,
                quote_symbol=quote,
                trading_pair=f"{base}{quote}",
            )

    return CryptoInstrument(
        raw_input=raw,
        base_symbol=raw,
        quote_symbol="USDT",
        trading_pair=f"{raw}USDT",
    )
