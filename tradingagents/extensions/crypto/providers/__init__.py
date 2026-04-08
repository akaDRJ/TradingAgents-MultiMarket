from tradingagents.extensions.crypto.registry import register_provider

from .base import ProviderError
from .binance_spot import BinanceSpotProvider
from .coingecko import CoinGeckoProvider
from .public_news import PublicNewsProvider

__all__ = [
    "ProviderError",
    "BinanceSpotProvider",
    "CoinGeckoProvider",
    "PublicNewsProvider",
]


def _register_providers() -> None:
    binance = BinanceSpotProvider()
    coingecko = CoinGeckoProvider()
    public_news = PublicNewsProvider()

    register_provider("binance_spot", "get_stock_data", binance.get_stock_data)
    register_provider("coingecko", "get_stock_data", coingecko.get_stock_data)
    register_provider("coingecko", "get_fundamentals", coingecko.get_fundamentals)
    register_provider("public_news", "get_news", public_news.get_news)
    register_provider("public_news", "get_global_news", public_news.get_global_news)


_register_providers()
