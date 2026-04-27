from tradingagents.extensions.market_ext.module import ExtensionModule
from tradingagents.extensions.market_ext.registry import get_extension, register_module

from .market import detect_market, get_exchange_for_a_share, get_index_display_name
from .normalize import normalize_ticker
from .policy import get_provider_chain, get_unsupported_message, is_method_supported
from .registry import get_registry, register_provider
from .routing import (
    detect_market_from_ticker,
    is_ashare_market,
    is_hk_market,
    is_us_market,
    route_extension,
    route_symbol,
)
from .types import Market
from . import providers  # noqa: F401


def _matches_ashare_extension(ticker: str) -> bool:
    return detect_market(ticker) in {Market.A_SHARE, Market.INDEX}


def _build_instrument_context(ticker: str) -> str | None:
    index_name = get_index_display_name(ticker)
    if index_name:
        normalized_ticker, _market = normalize_ticker(ticker)
        return (
            f"The instrument to analyze is the market index `{normalized_ticker}` ({index_name}). "
            "Treat it as an index, not a single operating company. Use index-aware reasoning focused on "
            "price action, market breadth, sector leadership, liquidity, macro and policy drivers, and "
            "broad market sentiment. When relevant, also consider aliases such as 上证指数, 沪指, 上证综指, "
            "and SSE Composite."
        )
    return None


def _build_market_instruction(ticker: str, analyst_kind: str) -> str:
    if not get_index_display_name(ticker):
        return ""

    if analyst_kind == "fundamentals":
        return (
            " For equity index instruments, do not treat the index as a single company and do not rely on "
            "company financial statement tools as if they were index fundamentals. If index-specific structural "
            "or valuation proxy data is unavailable, explicitly say traditional company fundamentals do not apply "
            "and focus on composition, sector weights, market breadth, liquidity, policy regime, and capital flows."
        )

    if analyst_kind in {"social", "news"}:
        return (
            " For equity index instruments, treat sentiment and news as market-wide context rather than company-specific "
            "coverage. Focus on index aliases, A-share sentiment, sector rotation, breadth, northbound flows, and major "
            "policy or macro catalysts."
        )

    return ""


def _build_index_fundamentals_report(ticker: str, current_date: str) -> str:
    normalized_ticker, _market = normalize_ticker(ticker)
    index_name = get_index_display_name(ticker) or normalized_ticker

    return (
        f"# {index_name}结构与基本面适用性说明\n\n"
        f"分析日期：{current_date}\n\n"
        f"分析标的：{index_name}（{normalized_ticker}）\n\n"
        "## 结论\n\n"
        f"{index_name} is a market index, not a single operating company. Traditional company fundamentals such as a "
        "balance sheet, cash flow statement, income statement, or company profile do not apply directly to this instrument.\n\n"
        "## 指数模式下应替代观察的维度\n\n"
        "1. 成分股结构：关注金融、周期、消费、科技等板块权重与变化。\n"
        "2. 市场广度：关注涨跌家数、中位数收益、成交额、换手率与风格扩散。\n"
        "3. 资金与流动性：关注北向资金、两融余额、政策宽松程度与利率环境。\n"
        "4. 宏观与政策：关注财政、货币、地产、出口、地缘政治等对整体风险偏好的影响。\n"
        "5. 估值代理：如果需要基本面视角，应使用指数整体估值、股息率、风险溢价、行业盈利预期等代理指标，而不是单一公司的财报。\n\n"
        "## 对后续决策的使用方式\n\n"
        "在后续研究、交易和风控阶段，应将本标的视为市场指数，优先参考技术面、市场情绪、宏观新闻和资金面，不得把单一公司财务数据冒充为指数基本面。"
    )


def _build_analyst_report(ticker: str, analyst_kind: str, current_date: str) -> str | None:
    if analyst_kind == "fundamentals" and get_index_display_name(ticker):
        return _build_index_fundamentals_report(ticker, current_date)
    return None


def get_extension_module() -> ExtensionModule:
    return ExtensionModule(
        name="ashare",
        match_ticker=_matches_ashare_extension,
        detect_market=detect_market,
        route_extension=route_extension,
        build_instrument_context=_build_instrument_context,
        build_market_instruction=_build_market_instruction,
        build_analyst_report=_build_analyst_report,
        priority=20,
    )


def ensure_registered() -> None:
    if get_extension("ashare") is not None:
        return

    register_module(get_extension_module())


ensure_registered()
