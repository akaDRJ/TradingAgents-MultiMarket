"""Tests for A-share provider registration and graceful failure behavior."""

import unittest

from tradingagents.extensions import ashare
from tradingagents.extensions.ashare.registry import get_registry
from tradingagents.extensions.ashare.routing import route_extension


class ProviderRegistrationTests(unittest.TestCase):
    def test_providers_auto_register_get_stock_data(self):
        registry = get_registry()
        providers = set(registry.list_providers())

        self.assertTrue({"tushare", "akshare", "baostock"}.issubset(providers))
        for provider in ["tushare", "akshare", "baostock"]:
            self.assertIn("get_stock_data", registry.list_methods(provider))

    def test_route_extension_reaches_provider_path_with_normalized_ticker(self):
        result = route_extension("get_stock_data", "600519", "2024-01-01", "2024-01-31")

        if isinstance(result, dict):
            self.assertEqual(result.get("ticker"), "600519.SS")
        else:
            self.assertIsInstance(result, str)
            self.assertIn("600519.SS", result)

    def test_ashare_package_exports_providers_module(self):
        self.assertTrue(hasattr(ashare, "providers"))


if __name__ == "__main__":
    unittest.main()
