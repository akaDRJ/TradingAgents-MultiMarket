"""Tests for A-share registration with the shared market-extension dispatcher."""

import unittest

from tradingagents.extensions.market_ext import (
    reset_extensions_for_test,
    resolve_extension,
    route_market_extension,
)


class AShareSharedDispatcherTests(unittest.TestCase):
    def test_resolve_extension_bootstraps_ashare_after_registry_reset(self):
        reset_extensions_for_test()

        extension = resolve_extension("600519")

        self.assertIsNotNone(extension)
        self.assertEqual(extension.name, "ashare")

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
