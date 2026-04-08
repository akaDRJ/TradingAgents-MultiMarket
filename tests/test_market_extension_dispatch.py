"""Tests for shared market-extension dispatch."""

import unittest

from tradingagents.extensions.market_ext import (
    Market,
    detect_market_for_ticker,
    get_extension,
    list_extensions,
    register_extension,
    reset_extensions_for_test,
    resolve_extension,
    route_market_extension,
)


class SharedMarketExtensionDispatchTests(unittest.TestCase):
    def setUp(self):
        reset_extensions_for_test()
        self.addCleanup(reset_extensions_for_test)

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

    def test_detect_market_for_ticker_uses_normalized_ticker(self):
        register_extension(
            name="crypto",
            match_ticker=lambda ticker: ticker.upper().startswith("BTC"),
            detect_market=lambda ticker: Market.CRYPTO if ticker == "BTCUSDT" else Market.UNKNOWN,
            route_extension=lambda method, *args, **kwargs: None,
        )

        result = detect_market_for_ticker(" BTCUSDT ")

        self.assertEqual(result, Market.CRYPTO)

    def test_route_market_extension_raises_if_matched_extension_returns_none(self):
        register_extension(
            name="crypto",
            match_ticker=lambda ticker: ticker.upper().startswith("BTC"),
            detect_market=lambda ticker: Market.CRYPTO,
            route_extension=lambda method, *args, **kwargs: None,
        )

        with self.assertRaisesRegex(ValueError, "must return a non-None result"):
            route_market_extension("get_stock_data", "BTCUSDT", "2024-01-01", "2024-01-31")

    def test_registry_get_and_list_return_registered_extensions(self):
        register_extension(
            name="crypto",
            match_ticker=lambda ticker: ticker.upper().startswith("BTC"),
            detect_market=lambda ticker: Market.CRYPTO,
            route_extension=lambda method, *args, **kwargs: {"method": method},
        )

        extension = get_extension("crypto")
        names = [item.name for item in list_extensions()]

        self.assertIsNotNone(extension)
        self.assertEqual(extension.name, "crypto")
        self.assertIn("crypto", names)


if __name__ == "__main__":
    unittest.main()
