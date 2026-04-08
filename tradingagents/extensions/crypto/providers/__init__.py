from tradingagents.extensions.crypto.registry import register_provider

from .base import ProviderError
from .binance_spot import BinanceSpotProvider
from .coingecko import CoinGeckoProvider

__all__ = [
    "ProviderError",
    "BinanceSpotProvider",
    "CoinGeckoProvider",
]


def _register_providers() -> None:
    binance = BinanceSpotProvider()
    coingecko = CoinGeckoProvider()

    register_provider("binance_spot", "get_stock_data", binance.get_stock_data)
    register_provider("coingecko", "get_stock_data", coingecko.get_stock_data)
    register_provider("coingecko", "get_fundamentals", coingecko.get_fundamentals)


_register_providers()
