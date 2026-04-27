"""Tests for unsupported or graceful A-share paths."""

import unittest

from tradingagents.dataflows.interface import route_to_vendor


class AShareUnsupportedPathTests(unittest.TestCase):
    def test_insider_transactions_is_explicitly_unsupported_for_ashare(self):
        out = route_to_vendor("get_insider_transactions", "600519")
        self.assertIn("not supported", out)
        self.assertIn("a_share", out)

    def test_company_fundamentals_are_explicitly_unsupported_for_index(self):
        out = route_to_vendor("get_fundamentals", "000001.SS", "2024-01-10")
        self.assertIn("not supported", out)
        self.assertIn("index", out)

    def test_global_news_currently_returns_graceful_non_crash_response(self):
        out = route_to_vendor("get_global_news", "2024-01-10", 7, 5)
        self.assertIsInstance(out, str)
        self.assertTrue(len(out) > 0)


if __name__ == "__main__":
    unittest.main()
