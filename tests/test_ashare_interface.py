"""Tests for interface-level A-share routing behavior when yfinance is unavailable."""

import unittest
from unittest.mock import patch

from tradingagents.dataflows.interface import route_to_vendor


class InterfaceRoutingTests(unittest.TestCase):
    def test_a_share_route_to_vendor_imports_and_reaches_extension_path(self):
        result = route_to_vendor("get_stock_data", "600519", "2024-01-01", "2024-01-31")

        if isinstance(result, dict):
            self.assertEqual(result.get("ticker"), "600519.SS")
        else:
            self.assertIsInstance(result, str)
            self.assertIn("600519.SS", result)

    def test_hk_ticker_falls_through_upstream_vendor_path(self):
        def fake_upstream_vendor(*args, **kwargs):
            return {"vendor": "upstream", "ticker": args[0]}

        with (
            patch("tradingagents.dataflows.interface.route_market_extension", return_value="EXTENSION_SHOULD_NOT_BE_USED") as mock_route,
            patch("tradingagents.dataflows.interface.get_vendor", return_value="alpha_vantage"),
            patch.dict(
                "tradingagents.dataflows.interface.VENDOR_METHODS",
                {"get_stock_data": {"alpha_vantage": fake_upstream_vendor}},
                clear=False,
            ),
        ):
            result = route_to_vendor("get_stock_data", "0700.HK", "2024-01-01", "2024-01-31")

        self.assertEqual(result, {"vendor": "upstream", "ticker": "0700.HK"})
        mock_route.assert_not_called()


if __name__ == "__main__":
    unittest.main()
