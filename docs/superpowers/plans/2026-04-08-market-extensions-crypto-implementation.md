# Unified Market Extensions And Crypto Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Docker-safe crypto spot analysis to `TradingAgents-AShare` by introducing a shared market-extension dispatcher that supports both the existing A-share extension and a new crypto extension without rewriting the upstream graph or analyst topology.

**Architecture:** Keep the upstream graph and abstract tool names unchanged, and generalize the current A-share-only seam in `tradingagents/dataflows/interface.py` into a shared market-extension dispatcher. Reuse the existing extension style for `ashare`, add `crypto` as a sibling extension, route market and indicator data through Binance Spot public endpoints with CoinGecko fallback, and keep `social` optional and best-effort via public news/web-derived sources.

**Tech Stack:** Python 3.10+, `requests`, `pandas`, existing `stockstats` integration, `unittest`, Binance Spot public REST endpoints, CoinGecko public REST endpoints, existing `uv` workflow.

---

### Task 1: Add Shared Market Extension Core

**Files:**
- Create: `tradingagents/extensions/market_ext/__init__.py`
- Create: `tradingagents/extensions/market_ext/types.py`
- Create: `tradingagents/extensions/market_ext/registry.py`
- Create: `tradingagents/extensions/market_ext/dispatcher.py`
- Test: `tests/test_market_extension_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for shared market-extension dispatch."""

import unittest

from tradingagents.extensions.market_ext import (
    Market,
    register_extension,
    reset_extensions_for_test,
    resolve_extension,
    route_market_extension,
)


class SharedMarketExtensionDispatchTests(unittest.TestCase):
    def setUp(self):
        reset_extensions_for_test()

    def test_resolve_extension_returns_registered_match(self):
        register_extension(
            name="crypto",
            match_ticker=lambda ticker: ticker.upper().startswith("BTC"),
            detect_market=lambda ticker: Market.CRYPTO,
            route_extension=lambda method, *args, **kwargs: {"method": method, "args": args, "kwargs": kwargs},
        )

        extension = resolve_extension("BTCUSDT")

        self.assertIsNotNone(extension)
        self.assertEqual(extension.name, "crypto")
        self.assertEqual(extension.detect_market("BTCUSDT"), Market.CRYPTO)

    def test_route_market_extension_passes_method_and_args_to_extension(self):
        seen = []

        def fake_route(method, *args, **kwargs):
            seen.append((method, args, kwargs))
            return {"ok": True, "ticker": args[0], "method": method}

        register_extension(
            name="crypto",
            match_ticker=lambda ticker: ticker.upper().startswith("BTC"),
            detect_market=lambda ticker: Market.CRYPTO,
            route_extension=fake_route,
        )

        result = route_market_extension("get_stock_data", "BTCUSDT", "2024-01-01", "2024-01-31")

        self.assertEqual(result["ticker"], "BTCUSDT")
        self.assertEqual(result["method"], "get_stock_data")
        self.assertEqual(seen[0][1], ("BTCUSDT", "2024-01-01", "2024-01-31"))

    def test_route_market_extension_returns_none_for_non_matching_ticker(self):
        register_extension(
            name="crypto",
            match_ticker=lambda ticker: ticker.upper().startswith("BTC"),
            detect_market=lambda ticker: Market.CRYPTO,
            route_extension=lambda method, *args, **kwargs: "SHOULD_NOT_BE_USED",
        )

        result = route_market_extension("get_stock_data", "AAPL", "2024-01-01", "2024-01-31")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_market_extension_dispatch -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'tradingagents.extensions.market_ext'`

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/extensions/market_ext/types.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class Market(Enum):
    A_SHARE = "a_share"
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
    route_extension: Callable[..., Any]
```

```python
# tradingagents/extensions/market_ext/registry.py
from __future__ import annotations

from typing import Dict, Iterable, Optional

from .types import ExtensionRegistration


_EXTENSIONS: Dict[str, ExtensionRegistration] = {}


def register_extension(
    name: str,
    match_ticker,
    detect_market,
    route_extension,
) -> None:
    _EXTENSIONS[name] = ExtensionRegistration(
        name=name,
        match_ticker=match_ticker,
        detect_market=detect_market,
        route_extension=route_extension,
    )


def get_extension(name: str) -> Optional[ExtensionRegistration]:
    return _EXTENSIONS.get(name)


def list_extensions() -> Iterable[ExtensionRegistration]:
    return _EXTENSIONS.values()


def reset_extensions_for_test() -> None:
    _EXTENSIONS.clear()
```

```python
# tradingagents/extensions/market_ext/dispatcher.py
from __future__ import annotations

from typing import Any, Optional

from .registry import list_extensions
from .types import ExtensionRegistration, Market


def resolve_extension(ticker: str) -> Optional[ExtensionRegistration]:
    if not ticker:
        return None

    raw = str(ticker).strip()
    if not raw:
        return None

    for extension in list_extensions():
        if extension.match_ticker(raw):
            return extension
    return None


def detect_market_for_ticker(ticker: str) -> Market:
    extension = resolve_extension(ticker)
    if extension is None:
        return Market.UNKNOWN
    return extension.detect_market(ticker)


def route_market_extension(method: str, *args, **kwargs) -> Any | None:
    ticker = None
    if args:
        ticker = str(args[0])
    else:
        ticker = kwargs.get("ticker") or kwargs.get("symbol")

    extension = resolve_extension(ticker or "")
    if extension is None:
        return None

    return extension.route_extension(method, *args, **kwargs)
```

```python
# tradingagents/extensions/market_ext/__init__.py
from .dispatcher import detect_market_for_ticker, resolve_extension, route_market_extension
from .registry import get_extension, list_extensions, register_extension, reset_extensions_for_test
from .types import ExtensionRegistration, Market

__all__ = [
    "ExtensionRegistration",
    "Market",
    "detect_market_for_ticker",
    "get_extension",
    "list_extensions",
    "register_extension",
    "reset_extensions_for_test",
    "resolve_extension",
    "route_market_extension",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_market_extension_dispatch -v`

Expected:

```text
test_resolve_extension_returns_registered_match ... ok
test_route_market_extension_passes_method_and_args_to_extension ... ok
test_route_market_extension_returns_none_for_non_matching_ticker ... ok
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_market_extension_dispatch.py \
  tradingagents/extensions/market_ext/__init__.py \
  tradingagents/extensions/market_ext/types.py \
  tradingagents/extensions/market_ext/registry.py \
  tradingagents/extensions/market_ext/dispatcher.py
git commit -m "feat: add shared market extension dispatcher"
```

### Task 2: Route A-share Through The Shared Dispatcher

**Files:**
- Modify: `tradingagents/extensions/ashare/types.py`
- Modify: `tradingagents/extensions/ashare/__init__.py`
- Modify: `tradingagents/dataflows/interface.py`
- Modify: `tradingagents/dataflows/stockstats_utils.py`
- Test: `tests/test_ashare_interface.py`
- Test: `tests/test_ashare_routing.py`
- Test: `tests/test_ashare_indicators.py`
- Test: `tests/test_ashare_shared_dispatcher.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for A-share registration with the shared market-extension dispatcher."""

import unittest

from tradingagents.extensions.market_ext import resolve_extension, route_market_extension


class AShareSharedDispatcherTests(unittest.TestCase):
    def test_six_digit_a_share_resolves_to_ashare_extension(self):
        extension = resolve_extension("600519")
        self.assertIsNotNone(extension)
        self.assertEqual(extension.name, "ashare")

    def test_shared_dispatcher_routes_a_share_stock_data_to_existing_router(self):
        result = route_market_extension("get_stock_data", "600519", "2024-01-01", "2024-01-31")

        if isinstance(result, dict):
            self.assertEqual(result.get("ticker"), "600519.SS")
        else:
            self.assertIsInstance(result, str)
            self.assertIn("600519.SS", result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_ashare_interface tests.test_ashare_routing tests.test_ashare_indicators tests.test_ashare_shared_dispatcher -v`

Expected: FAIL because the shared dispatcher does not yet import or register the A-share extension.

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/extensions/ashare/types.py
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
```

```python
# tradingagents/extensions/ashare/__init__.py
from tradingagents.extensions.market_ext import register_extension

from .market import detect_market, get_exchange_for_a_share
from .normalize import normalize_ticker
from .policy import get_provider_chain, is_method_supported, get_unsupported_message
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
    return detect_market(ticker) in {Market.A_SHARE, Market.HK}


register_extension(
    name="ashare",
    match_ticker=_matches_ashare_extension,
    detect_market=detect_market,
    route_extension=route_extension,
)
```

```python
# tradingagents/dataflows/interface.py (replacement blocks)
from tradingagents.extensions.market_ext import route_market_extension, resolve_extension


def _route_market_extension_if_available(method: str, *args, **kwargs):
    ticker = _get_ticker_from_args(args, kwargs)
    if not ticker:
        return None

    extension = resolve_extension(str(ticker))
    if extension is None:
        return None

    if method == "get_indicators":
        return get_stock_stats_indicators_window(*args, **kwargs)

    return route_market_extension(method, *args, **kwargs)


def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to the market extension layer first, then upstream vendors."""
    extension_result = _route_market_extension_if_available(method, *args, **kwargs)
    if extension_result is not None:
        return extension_result

    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)
    primary_vendors = [v.strip() for v in vendor_config.split(",")]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    all_available_vendors = list(VENDOR_METHODS[method].keys())
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except AlphaVantageRateLimitError:
            continue

    raise RuntimeError(f"No available vendor for '{method}'")
```

```python
# tradingagents/dataflows/stockstats_utils.py (replacement blocks)
from tradingagents.extensions.market_ext import resolve_extension, route_market_extension


def _load_extension_ohlcv(symbol: str, start_str: str, end_str: str) -> pd.DataFrame:
    result = route_market_extension("get_stock_data", symbol, start_str, end_str)
    if not isinstance(result, dict):
        raise RuntimeError(f"Extension OHLCV route failed for {symbol}: {result}")

    records = result.get("data") or []
    if not records:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    df = pd.DataFrame(records)
    rename_map = {
        "date": "Date",
        "trade_date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "vol": "Volume",
    }
    df = df.rename(columns=rename_map)
    for col in ["Date", "Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            df[col] = None
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]]


def load_ohlcv(symbol: str, curr_date: str) -> pd.DataFrame:
    config = get_config()
    curr_date_dt = pd.to_datetime(curr_date)

    today_date = pd.Timestamp.today()
    start_date = today_date - pd.DateOffset(years=5)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = today_date.strftime("%Y-%m-%d")

    if resolve_extension(symbol) is not None:
        data = _load_extension_ohlcv(symbol, start_str, end_str)
    else:
        os.makedirs(config["data_cache_dir"], exist_ok=True)
        data_file = os.path.join(
            config["data_cache_dir"],
            f"{symbol}-YFin-data-{start_str}-{end_str}.csv",
        )

        if os.path.exists(data_file):
            data = pd.read_csv(data_file, on_bad_lines="skip")
        else:
            data = yf_retry(
                lambda: yf.download(
                    symbol,
                    start=start_str,
                    end=end_str,
                    multi_level_index=False,
                    progress=False,
                    auto_adjust=True,
                )
            )
            data = data.reset_index()
            data.to_csv(data_file, index=False)

    data = _clean_dataframe(data)
    data = data[data["Date"] <= curr_date_dt]
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
uv run python -m unittest \
  tests.test_ashare_interface \
  tests.test_ashare_routing \
  tests.test_ashare_indicators \
  tests.test_ashare_providers \
  tests.test_ashare_shared_dispatcher \
  -v
```

Expected: all A-share interface and routing tests PASS, proving the shared dispatcher did not regress existing extension behavior.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ashare_interface.py \
  tests/test_ashare_routing.py \
  tests/test_ashare_indicators.py \
  tests/test_ashare_shared_dispatcher.py \
  tradingagents/extensions/ashare/types.py \
  tradingagents/extensions/ashare/__init__.py \
  tradingagents/dataflows/interface.py \
  tradingagents/dataflows/stockstats_utils.py
git commit -m "refactor: route ashare through shared extension seam"
```

### Task 3: Build Crypto Detection, Normalization, And Provider Registration

**Files:**
- Create: `tradingagents/extensions/crypto/__init__.py`
- Create: `tradingagents/extensions/crypto/normalize.py`
- Create: `tradingagents/extensions/crypto/policy.py`
- Create: `tradingagents/extensions/crypto/registry.py`
- Create: `tradingagents/extensions/crypto/routing.py`
- Create: `tradingagents/extensions/crypto/providers/__init__.py`
- Create: `tradingagents/extensions/crypto/providers/base.py`
- Create: `tradingagents/extensions/crypto/providers/binance_spot.py`
- Create: `tradingagents/extensions/crypto/providers/coingecko.py`
- Test: `tests/test_crypto_market_detection.py`
- Test: `tests/test_crypto_normalization.py`
- Test: `tests/test_crypto_binance_provider.py`
- Test: `tests/test_crypto_coingecko_provider.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for crypto market detection."""

import unittest

from tradingagents.extensions.crypto.normalize import detect_market
from tradingagents.extensions.market_ext.types import Market


class CryptoMarketDetectionTests(unittest.TestCase):
    def test_known_bare_symbols_are_crypto(self):
        self.assertEqual(detect_market("BTC"), Market.CRYPTO)
        self.assertEqual(detect_market("ETH"), Market.CRYPTO)

    def test_pair_inputs_are_crypto(self):
        self.assertEqual(detect_market("BTCUSDT"), Market.CRYPTO)
        self.assertEqual(detect_market("ETH-USD"), Market.CRYPTO)

    def test_equity_tickers_do_not_accidentally_route_to_crypto(self):
        self.assertEqual(detect_market("AAPL"), Market.UNKNOWN)
        self.assertEqual(detect_market("600519"), Market.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
```

```python
"""Tests for crypto ticker normalization."""

import unittest

from tradingagents.extensions.crypto.normalize import normalize_ticker


class CryptoNormalizationTests(unittest.TestCase):
    def test_bare_symbol_defaults_to_usdt_pair(self):
        instrument = normalize_ticker("btc")
        self.assertEqual(instrument.base_symbol, "BTC")
        self.assertEqual(instrument.quote_symbol, "USDT")
        self.assertEqual(instrument.trading_pair, "BTCUSDT")

    def test_hyphenated_usd_pair_preserves_quote_symbol(self):
        instrument = normalize_ticker("ETH-USD")
        self.assertEqual(instrument.base_symbol, "ETH")
        self.assertEqual(instrument.quote_symbol, "USD")
        self.assertEqual(instrument.trading_pair, "ETHUSD")


if __name__ == "__main__":
    unittest.main()
```

```python
"""Tests for Binance spot crypto provider."""

import unittest
from unittest.mock import Mock, patch

from tradingagents.extensions.crypto.providers.binance_spot import BinanceSpotProvider


class BinanceSpotProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.binance_spot.requests.Session.get")
    def test_get_stock_data_formats_klines_into_extension_shape(self, mock_get):
        exchange_info = Mock()
        exchange_info.raise_for_status.return_value = None
        exchange_info.json.return_value = {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING"}]}

        klines = Mock()
        klines.raise_for_status.return_value = None
        klines.json.return_value = [
            [1704067200000, "42000.0", "42500.0", "41800.0", "42300.0", "100.0", 1704153599999, "0", 0, "0", "0", "0"]
        ]

        mock_get.side_effect = [exchange_info, klines]

        provider = BinanceSpotProvider()
        result = provider.get_stock_data("BTCUSDT", "2024-01-01", "2024-01-02")

        self.assertEqual(result["ticker"], "BTCUSDT")
        self.assertEqual(result["provider"], "binance_spot")
        self.assertEqual(result["data"][0]["close"], 42300.0)


if __name__ == "__main__":
    unittest.main()
```

```python
"""Tests for CoinGecko crypto provider."""

import unittest
from unittest.mock import Mock, patch

from tradingagents.extensions.crypto.providers.coingecko import CoinGeckoProvider


class CoinGeckoProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.coingecko.requests.Session.get")
    def test_get_fundamentals_returns_market_cap_and_supply_context(self, mock_get):
        coin_lookup = Mock()
        coin_lookup.raise_for_status.return_value = None
        coin_lookup.json.return_value = [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}]

        coin_detail = Mock()
        coin_detail.raise_for_status.return_value = None
        coin_detail.json.return_value = {
            "name": "Bitcoin",
            "symbol": "btc",
            "market_cap_rank": 1,
            "market_data": {
                "current_price": {"usd": 70000},
                "market_cap": {"usd": 1300000000000},
                "total_volume": {"usd": 25000000000},
                "circulating_supply": 19600000,
                "total_supply": 21000000,
            },
        }

        mock_get.side_effect = [coin_lookup, coin_detail]

        provider = CoinGeckoProvider()
        result = provider.get_fundamentals("BTCUSDT", curr_date="2024-01-01")

        self.assertIn("Bitcoin", result)
        self.assertIn("Market Cap", result)
        self.assertIn("Circulating Supply", result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run python -m unittest \
  tests.test_crypto_market_detection \
  tests.test_crypto_normalization \
  tests.test_crypto_binance_provider \
  tests.test_crypto_coingecko_provider \
  -v
```

Expected: FAIL with missing `tradingagents.extensions.crypto` modules.

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/extensions/crypto/normalize.py
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
            return CryptoInstrument(raw_input=raw, base_symbol=base, quote_symbol=quote, trading_pair=f"{base}{quote}")

    return CryptoInstrument(raw_input=raw, base_symbol=raw, quote_symbol="USDT", trading_pair=f"{raw}USDT")
```

```python
# tradingagents/extensions/crypto/policy.py
from tradingagents.extensions.market_ext.types import Market


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


def get_provider_chain(method, market):
    return MARKET_POLICY.get(market, {}).get(method)


def is_method_supported(method, market):
    chain = get_provider_chain(method, market)
    return chain is not None and len(chain) > 0


def get_unsupported_message(method, market):
    return f"Method '{method}' is not supported for {market.value} markets."
```

```python
# tradingagents/extensions/crypto/registry.py
from tradingagents.extensions.ashare.registry import ProviderRegistry


_global_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    return _global_registry


def register_provider(provider: str, method: str, func) -> None:
    _global_registry.register(provider, method, func)
```

```python
# tradingagents/extensions/crypto/routing.py
from __future__ import annotations

from tradingagents.extensions.market_ext.types import Market

from .normalize import detect_market, normalize_ticker
from .policy import get_provider_chain, get_unsupported_message, is_method_supported
from .registry import get_registry


def route_extension(method: str, *args, **kwargs):
    if not args:
        return None

    instrument = normalize_ticker(str(args[0]))
    market = detect_market(str(args[0]))

    if market != Market.CRYPTO:
        return None

    if not is_method_supported(method, market):
        return get_unsupported_message(method, market)

    for provider in get_provider_chain(method, market):
        impl = get_registry().get(provider, method)
        if impl is None:
            continue
        try:
            return impl(instrument.trading_pair, *args[1:], **kwargs)
        except Exception:
            continue

    return f"Error: All providers failed for '{method}' on '{instrument.trading_pair}'"
```

```python
# tradingagents/extensions/crypto/providers/binance_spot.py
from __future__ import annotations

from datetime import datetime

import requests


class BinanceSpotProvider:
    name = "binance_spot"
    base_url = "https://api.binance.com"

    def __init__(self):
        self.session = requests.Session()

    def _get(self, path: str, params: dict | None = None):
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def _ensure_symbol(self, symbol: str) -> None:
        payload = self._get("/api/v3/exchangeInfo", {"symbol": symbol})
        symbols = payload.get("symbols", [])
        if not symbols or symbols[0].get("status") != "TRADING":
            raise RuntimeError(f"Binance spot symbol unavailable: {symbol}")

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        self._ensure_symbol(ticker)
        rows = self._get("/api/v3/klines", {"symbol": ticker, "interval": "1d", "limit": 365})
        data = []
        for row in rows:
            data.append(
                {
                    "date": datetime.utcfromtimestamp(row[0] / 1000).strftime("%Y-%m-%d"),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
            )
        return {"ticker": ticker, "data": data, "provider": self.name, "source": "binance_spot"}
```

```python
# tradingagents/extensions/crypto/providers/coingecko.py
from __future__ import annotations

import os
from datetime import datetime

import requests


class CoinGeckoProvider:
    name = "coingecko"
    base_url = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.session = requests.Session()
        api_key = os.getenv("COINGECKO_API_KEY")
        if api_key:
            self.session.headers.update({"x-cg-demo-api-key": api_key})

    def _get(self, path: str, params: dict | None = None):
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def _coin_id(self, ticker: str) -> str:
        base_symbol = ticker.replace("USDT", "").replace("USDC", "").replace("USD", "").lower()
        candidates = self._get("/search", {"query": base_symbol}).get("coins", [])
        if not candidates:
            raise RuntimeError(f"CoinGecko coin not found for {ticker}")
        return candidates[0]["id"]

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        coin_id = self._coin_id(ticker)
        payload = self._get(f"/coins/{coin_id}/market_chart", {"vs_currency": "usd", "days": 365, "interval": "daily"})
        prices = payload.get("prices", [])
        volumes = payload.get("total_volumes", [])
        data = []
        for index, row in enumerate(prices):
            volume = volumes[index][1] if index < len(volumes) else 0.0
            data.append(
                {
                    "date": datetime.utcfromtimestamp(row[0] / 1000).strftime("%Y-%m-%d"),
                    "open": float(row[1]),
                    "high": float(row[1]),
                    "low": float(row[1]),
                    "close": float(row[1]),
                    "volume": float(volume),
                }
            )
        return {"ticker": ticker, "data": data, "provider": self.name, "source": "coingecko"}

    def get_fundamentals(self, ticker: str, curr_date: str | None = None, **kwargs):
        coin_id = self._coin_id(ticker)
        payload = self._get(f"/coins/{coin_id}")
        market_data = payload.get("market_data", {})
        return (
            f"## {payload.get('name', ticker)} Fundamentals\\n\\n"
            f"- Market Cap: {market_data.get('market_cap', {}).get('usd', 'N/A')}\\n"
            f"- 24h Volume: {market_data.get('total_volume', {}).get('usd', 'N/A')}\\n"
            f"- Circulating Supply: {market_data.get('circulating_supply', 'N/A')}\\n"
            f"- Total Supply: {market_data.get('total_supply', 'N/A')}\\n"
        )
```

```python
# tradingagents/extensions/crypto/providers/base.py
class ProviderError(Exception):
    pass
```

```python
# tradingagents/extensions/crypto/providers/__init__.py
from tradingagents.extensions.crypto.registry import register_provider

from .base import ProviderError
from .binance_spot import BinanceSpotProvider
from .coingecko import CoinGeckoProvider


def _register_providers() -> None:
    binance = BinanceSpotProvider()
    coingecko = CoinGeckoProvider()

    register_provider("binance_spot", "get_stock_data", binance.get_stock_data)
    register_provider("coingecko", "get_stock_data", coingecko.get_stock_data)
    register_provider("coingecko", "get_fundamentals", coingecko.get_fundamentals)


_register_providers()
```

```python
# tradingagents/extensions/crypto/__init__.py
from tradingagents.extensions.market_ext import register_extension

from .normalize import detect_market, normalize_ticker
from .policy import get_provider_chain, get_unsupported_message, is_method_supported
from .registry import get_registry, register_provider
from .routing import route_extension
from . import providers  # noqa: F401


register_extension(
    name="crypto",
    match_ticker=lambda ticker: detect_market(ticker).value == "crypto",
    detect_market=detect_market,
    route_extension=route_extension,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
uv run python -m unittest \
  tests.test_crypto_market_detection \
  tests.test_crypto_normalization \
  tests.test_crypto_binance_provider \
  tests.test_crypto_coingecko_provider \
  -v
```

Expected: all crypto detection, normalization, and provider-shape tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_crypto_market_detection.py \
  tests/test_crypto_normalization.py \
  tests/test_crypto_binance_provider.py \
  tests/test_crypto_coingecko_provider.py \
  tradingagents/extensions/crypto/__init__.py \
  tradingagents/extensions/crypto/normalize.py \
  tradingagents/extensions/crypto/policy.py \
  tradingagents/extensions/crypto/registry.py \
  tradingagents/extensions/crypto/routing.py \
  tradingagents/extensions/crypto/providers/__init__.py \
  tradingagents/extensions/crypto/providers/base.py \
  tradingagents/extensions/crypto/providers/binance_spot.py \
  tradingagents/extensions/crypto/providers/coingecko.py
git commit -m "feat: add crypto extension normalization and providers"
```

### Task 4: Add Crypto News/Social Routing And Interface Coverage

**Files:**
- Create: `tradingagents/extensions/crypto/providers/public_news.py`
- Modify: `tradingagents/extensions/crypto/providers/__init__.py`
- Modify: `tradingagents/extensions/crypto/policy.py`
- Test: `tests/test_crypto_interface_routing.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for crypto interface routing through the shared market-extension seam."""

import unittest
from unittest.mock import patch

from tradingagents.dataflows.interface import route_to_vendor


class CryptoInterfaceRoutingTests(unittest.TestCase):
    def test_crypto_market_data_uses_extension_path_before_stock_vendors(self):
        fake_result = {
            "ticker": "BTCUSDT",
            "data": [{"date": "2024-01-01", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0}],
            "provider": "binance_spot",
            "source": "binance_spot",
        }

        with patch("tradingagents.extensions.crypto.routing.route_extension", return_value=fake_result):
            result = route_to_vendor("get_stock_data", "BTCUSDT", "2024-01-01", "2024-01-31")

        self.assertEqual(result["ticker"], "BTCUSDT")
        self.assertEqual(result["provider"], "binance_spot")

    def test_crypto_news_returns_public_web_result_not_stock_vendor_result(self):
        fake_report = "## BTCUSDT News\\n\\n- Article: Bitcoin rallies on ETF flows"

        with patch("tradingagents.extensions.crypto.routing.route_extension", return_value=fake_report):
            result = route_to_vendor("get_news", "BTCUSDT", "2024-01-01", "2024-01-31")

        self.assertIn("BTCUSDT News", result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_crypto_interface_routing -v`

Expected: FAIL because no crypto `get_news` provider is registered yet and interface coverage does not prove end-to-end crypto routing.

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/extensions/crypto/providers/public_news.py
from __future__ import annotations

from xml.etree import ElementTree

import requests


class PublicNewsProvider:
    name = "public_news"

    def _fetch_feed(self, query: str):
        url = "https://news.google.com/rss/search"
        response = requests.get(
            url,
            params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
            timeout=20,
        )
        response.raise_for_status()
        return ElementTree.fromstring(response.content)

    def get_news(self, ticker: str, start_date: str, end_date: str, **kwargs):
        root = self._fetch_feed(f"{ticker} crypto OR cryptocurrency")
        items = root.findall(".//item")[:8]
        lines = [f"## {ticker} News, from {start_date} to {end_date}:", ""]
        for item in items:
            title = item.findtext("title", default="Untitled")
            link = item.findtext("link", default="")
            pub_date = item.findtext("pubDate", default="")
            lines.append(f"### {title}")
            if pub_date:
                lines.append(f"Published: {pub_date}")
            if link:
                lines.append(f"Link: {link}")
            lines.append("")
        return "\n".join(lines)

    def get_global_news(self, curr_date: str, look_back_days: int = 7, limit: int = 5, **kwargs):
        root = self._fetch_feed("bitcoin OR ethereum OR crypto market")
        items = root.findall(".//item")[:limit]
        lines = [f"## Global Crypto News up to {curr_date}:", ""]
        for item in items:
            lines.append(f"- {item.findtext('title', default='Untitled')}")
        return "\n".join(lines)
```

```python
# tradingagents/extensions/crypto/providers/__init__.py (added registrations)
from .public_news import PublicNewsProvider


def _register_providers() -> None:
    binance = BinanceSpotProvider()
    coingecko = CoinGeckoProvider()
    public_news = PublicNewsProvider()

    register_provider("binance_spot", "get_stock_data", binance.get_stock_data)
    register_provider("coingecko", "get_stock_data", coingecko.get_stock_data)
    register_provider("coingecko", "get_fundamentals", coingecko.get_fundamentals)
    register_provider("public_news", "get_news", public_news.get_news)
    register_provider("public_news", "get_global_news", public_news.get_global_news)
```

```python
# tradingagents/extensions/crypto/policy.py (full mapping after news support)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
uv run python -m unittest \
  tests.test_crypto_interface_routing \
  tests.test_crypto_market_detection \
  tests.test_crypto_normalization \
  tests.test_crypto_binance_provider \
  tests.test_crypto_coingecko_provider \
  -v
```

Expected: PASS, proving crypto routes through the shared extension seam for market data and news before stock vendors are considered.

- [ ] **Step 5: Commit**

```bash
git add tests/test_crypto_interface_routing.py \
  tradingagents/extensions/crypto/policy.py \
  tradingagents/extensions/crypto/providers/__init__.py \
  tradingagents/extensions/crypto/providers/public_news.py
git commit -m "feat: add crypto news routing through extension seam"
```

### Task 5: Add Market-Aware Analyst Instructions And Final Regression Coverage

**Files:**
- Modify: `tradingagents/agents/utils/agent_utils.py`
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Modify: `tradingagents/agents/analysts/social_media_analyst.py`
- Test: `tests/test_market_specific_instruction.py`
- Test: `tests/test_crypto_interface_routing.py`
- Test: `tests/test_ashare_interface.py`
- Test: `tests/test_ashare_indicators.py`
- Test: `tests/test_market_extension_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for market-aware analyst prompt helper behavior."""

import unittest

from tradingagents.agents.utils.agent_utils import build_market_specific_instruction


class MarketSpecificInstructionTests(unittest.TestCase):
    def test_crypto_fundamentals_instruction_mentions_token_metrics(self):
        note = build_market_specific_instruction("BTCUSDT", "fundamentals")
        self.assertIn("token", note.lower())
        self.assertIn("supply", note.lower())

    def test_crypto_social_instruction_mentions_low_confidence(self):
        note = build_market_specific_instruction("BTCUSDT", "social")
        self.assertIn("low-confidence", note.lower())

    def test_equity_instruction_is_empty(self):
        self.assertEqual(build_market_specific_instruction("AAPL", "fundamentals"), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run python -m unittest \
  tests.test_market_specific_instruction \
  tests.test_market_extension_dispatch \
  tests.test_ashare_interface \
  tests.test_ashare_indicators \
  tests.test_crypto_interface_routing \
  -v
```

Expected: FAIL because `build_market_specific_instruction` does not exist and analyst prompts are still company-only.

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/agents/utils/agent_utils.py (new helper block)
from tradingagents.extensions.market_ext import detect_market_for_ticker, Market


def build_market_specific_instruction(ticker: str, analyst_kind: str) -> str:
    market = detect_market_for_ticker(ticker)

    if market != Market.CRYPTO:
        return ""

    if analyst_kind == "fundamentals":
        return (
            " For crypto instruments, prioritize token supply, market capitalization, liquidity, "
            "market structure, and project-level fundamentals. Balance sheet style tools may be unsupported."
        )

    if analyst_kind == "social":
        return (
            " For crypto instruments, social inputs are public-web-derived and low-confidence. "
            "Use them as weak corroborating evidence, not as a primary signal."
        )

    return ""
```

```python
# tradingagents/agents/analysts/fundamentals_analyst.py (system_message replacement block)
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    build_market_specific_instruction,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_language_instruction,
)

def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        system_message = (
            "You are a researcher tasked with analyzing fundamental information over the past week about a company. "
            "Please write a comprehensive report of the company's fundamental information such as financial documents, "
            "company profile, basic company financials, and company financial history to gain a full view of the company's "
            "fundamental information to inform traders. Make sure to include as much detail as possible. Provide specific, "
            "actionable insights with supporting evidence to help traders make informed decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."
            + build_market_specific_instruction(state["company_of_interest"], "fundamentals")
            + get_language_instruction()
        )
```

```python
# tradingagents/agents/analysts/social_media_analyst.py (system_message replacement block)
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    build_market_specific_instruction,
    get_language_instruction,
    get_news,
)

def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
        ]

        system_message = (
            "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. "
            "You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. "
            "Use the get_news(query, start_date, end_date) tool to search for company-specific news and social media discussions. Try to look at all sources possible from social media to sentiment to news. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + build_market_specific_instruction(state["company_of_interest"], "social")
            + get_language_instruction()
        )
```

- [ ] **Step 4: Run the focused regression suite**

Run:

```bash
uv run python -m unittest \
  tests.test_market_extension_dispatch \
  tests.test_ashare_interface \
  tests.test_ashare_routing \
  tests.test_ashare_indicators \
  tests.test_ashare_providers \
  tests.test_crypto_market_detection \
  tests.test_crypto_normalization \
  tests.test_crypto_binance_provider \
  tests.test_crypto_coingecko_provider \
  tests.test_crypto_interface_routing \
  tests.test_market_specific_instruction \
  -v
```

Expected: PASS across shared-dispatch, A-share regression, crypto provider, and analyst instruction tests.

- [ ] **Step 5: Commit**

```bash
git add tradingagents/agents/utils/agent_utils.py \
  tradingagents/agents/analysts/fundamentals_analyst.py \
  tradingagents/agents/analysts/social_media_analyst.py \
  tests/test_market_specific_instruction.py
git commit -m "feat: add market-aware crypto analyst instructions"
```
