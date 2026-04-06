"""Tests for A-share fundamentals bridge via AKShare."""

import unittest
from unittest.mock import patch

import pandas as pd

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.extensions.ashare.providers.akshare import AKShareProvider


class AShareFundamentalsBridgeTests(unittest.TestCase):
    @patch.object(AKShareProvider, "_check_available", return_value=True)
    def test_get_fundamentals_formats_summary(self, _available):
        provider = AKShareProvider()
        df = pd.DataFrame([
            {"指标": "归母净利润", "20241231": 100.0},
            {"指标": "销售毛利率", "20241231": 0.91},
            {"指标": "资产负债率", "20241231": 0.12},
        ])
        with patch("akshare.stock_financial_abstract", return_value=df):
            out = provider.get_fundamentals("600519.SS", "2024-12-31")
        self.assertIn("# Company Fundamentals for 600519.SS", out)
        self.assertIn("归母净利润: 100.0", out)
        self.assertIn("销售毛利率: 0.91", out)

    @patch.object(AKShareProvider, "_check_available", return_value=True)
    def test_get_balance_sheet_formats_csv_like_upstream(self, _available):
        provider = AKShareProvider()
        df = pd.DataFrame([
            {"REPORT_DATE": "2024-09-30 00:00:00", "REPORT_TYPE": "三季报", "SECURITY_CODE": "600519", "TOTAL_ASSETS": 123.0},
            {"REPORT_DATE": "2023-12-31 00:00:00", "REPORT_TYPE": "年报", "SECURITY_CODE": "600519", "TOTAL_ASSETS": 100.0},
        ])
        with patch("akshare.stock_balance_sheet_by_report_em", return_value=df):
            out = provider.get_balance_sheet("600519.SS", "annual", "2024-12-31")
        self.assertIn("# Balance Sheet data for 600519.SS (annual)", out)
        self.assertIn("TOTAL_ASSETS", out)
        self.assertIn("100.0", out)
        self.assertNotIn("123.0", out)

    def test_route_to_vendor_reaches_fundamentals_extension_path(self):
        with patch("tradingagents.extensions.ashare.routing.route_extension", return_value="FUND_OK") as mock_route:
            out = route_to_vendor("get_fundamentals", "600519", "2024-12-31")
        self.assertEqual(out, "FUND_OK")
        mock_route.assert_called_once_with("get_fundamentals", "600519", "2024-12-31")


if __name__ == "__main__":
    unittest.main()
