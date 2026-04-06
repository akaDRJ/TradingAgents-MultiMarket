"""Tests for A-share news bridge via AKShare."""

import unittest
from unittest.mock import patch

import pandas as pd

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.extensions.ashare.providers.akshare import AKShareProvider


class AShareNewsBridgeTests(unittest.TestCase):
    @patch.object(AKShareProvider, "_check_available", return_value=True)
    def test_get_news_formats_akshare_news_like_upstream(self, _available):
        provider = AKShareProvider()
        df = pd.DataFrame([
            {
                "关键词": "600519",
                "新闻标题": "贵州茅台回购进展",
                "新闻内容": "公司公告了新的回购进展。",
                "发布时间": "2024-01-09 10:00:00",
                "文章来源": "示例来源",
                "新闻链接": "https://example.com/news/1",
            }
        ])
        with patch("akshare.stock_news_em", return_value=df):
            out = provider.get_news("600519.SS", "2024-01-01", "2024-01-10")
        self.assertIn("## 600519.SS News, from 2024-01-01 to 2024-01-10:", out)
        self.assertIn("贵州茅台回购进展", out)
        self.assertIn("示例来源", out)
        self.assertIn("https://example.com/news/1", out)

    def test_route_to_vendor_reaches_news_extension_path(self):
        with patch("tradingagents.extensions.ashare.routing.route_extension", return_value="NEWS_OK") as mock_route:
            out = route_to_vendor("get_news", "600519", "2024-01-01", "2024-01-10")
        self.assertEqual(out, "NEWS_OK")
        mock_route.assert_called_once_with("get_news", "600519", "2024-01-01", "2024-01-10")


if __name__ == "__main__":
    unittest.main()
