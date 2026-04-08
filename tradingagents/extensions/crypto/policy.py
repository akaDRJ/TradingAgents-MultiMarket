from tradingagents.extensions.market_ext.types import Market

DEFERRED_UPSTREAM_METHODS = set()


MARKET_POLICY = {
    Market.CRYPTO: {
        "get_stock_data": ["binance_spot", "coingecko"],
        "get_indicators": ["binance_spot", "coingecko"],
        "get_fundamentals": ["coingecko"],
        "get_balance_sheet": None,
        "get_cashflow": None,
        "get_income_statement": None,
        "get_news": ["public_news"],
        "get_global_news": ["public_news"],
        "get_insider_transactions": None,
    }
}


def get_provider_chain(method: str, market: Market):
    return MARKET_POLICY.get(market, {}).get(method)


def is_method_supported(method: str, market: Market) -> bool:
    chain = get_provider_chain(method, market)
    return chain is not None and len(chain) > 0


def get_unsupported_message(method: str, market: Market) -> str:
    return f"Method '{method}' is not supported for {market.value} markets."
