"""Tests for interface-level A-share routing behavior when yfinance is unavailable."""

import unittest

from tradingagents.dataflows.interface import route_to_vendor


class InterfaceRoutingTests(unittest.TestCase):
    def test_a_share_route_to_vendor_imports_and_reaches_extension_path(self):
        result = route_to_vendor("get_stock_data", "600519", "2024-01-01", "2024-01-31")

        if isinstance(result, dict):
            self.assertEqual(result.get("ticker"), "600519.SS")
        else:
            self.assertIsInstance(result, str)
            self.assertIn("600519.SS", result)


if __name__ == "__main__":
    unittest.main()
