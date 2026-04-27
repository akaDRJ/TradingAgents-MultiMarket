"""Tests for A-share market detection."""

import unittest

from tradingagents.extensions.ashare.market import detect_market, get_exchange_for_a_share
from tradingagents.extensions.ashare.types import Market


class MarketDetectionTests(unittest.TestCase):
    """Test market detection for various ticker formats."""

    def test_known_index_aliases_are_detected_as_index(self):
        for ticker in ["上证指数", "沪指", "上证综指", "000001.SS", "000001.SH"]:
            with self.subTest(ticker=ticker):
                self.assertEqual(detect_market(ticker), Market.INDEX)

    def test_a_share_sse_codes(self):
        """SSE (Shanghai) A-share codes: 600xxx, 601xxx, 603xxx, 605xxx, 688xxx."""
        for code in ["600519", "601166", "603288", "605588", "688041"]:
            with self.subTest(code=code):
                self.assertEqual(detect_market(code), Market.A_SHARE)

    def test_a_share_szse_codes(self):
        """SZSE (Shenzhen) A-share codes: 000xxx, 001xxx, 002xxx, 003xxx, 300xxx, 301xxx."""
        for code in ["000001", "001696", "002594", "003816", "300750", "301028"]:
            with self.subTest(code=code):
                self.assertEqual(detect_market(code), Market.A_SHARE)

    def test_a_share_with_suffix(self):
        """A-share tickers with explicit .SS or .SZ suffix."""
        self.assertEqual(detect_market("600519.SS"), Market.A_SHARE)
        self.assertEqual(detect_market("600519.ss"), Market.A_SHARE)
        self.assertEqual(detect_market("000001.SZ"), Market.A_SHARE)
        self.assertEqual(detect_market("000001.sz"), Market.A_SHARE)
        self.assertEqual(detect_market("430001.BJ"), Market.A_SHARE)

    def test_hk_ticker_with_suffix(self):
        """HK tickers with .HK suffix."""
        self.assertEqual(detect_market("0700.HK"), Market.HK)
        self.assertEqual(detect_market("0700.hk"), Market.HK)
        self.assertEqual(detect_market("00700.HK"), Market.HK)

    def test_hk_ticker_5_digit(self):
        """HK tickers as 5-digit numbers."""
        self.assertEqual(detect_market("07000"), Market.HK)
        self.assertEqual(detect_market("00902"), Market.HK)

    def test_us_ticker_standard(self):
        """US tickers (NYSE/NASDAQ)."""
        for ticker in ["AAPL", "TSLA", "GOOGL", "MSFT", "aapl"]:
            with self.subTest(ticker=ticker):
                self.assertEqual(detect_market(ticker), Market.US)

    def test_us_ticker_with_dot_ob(self):
        """US OTC tickers with .OB suffix."""
        self.assertEqual(detect_market("AAPL.OB"), Market.US)

    def test_unknown_empty(self):
        """Empty ticker returns UNKNOWN."""
        self.assertEqual(detect_market(""), Market.UNKNOWN)
        self.assertEqual(detect_market("   "), Market.UNKNOWN)


class ExchangeDetectionTests(unittest.TestCase):
    """Test exchange suffix detection for A-share codes."""

    def test_sse_exchange(self):
        """Shanghai Stock Exchange codes return .SS."""
        for code in ["600519", "601166", "603288", "605588", "688041"]:
            with self.subTest(code=code):
                self.assertEqual(get_exchange_for_a_share(code), ".SS")

    def test_szse_exchange(self):
        """Shenzhen Stock Exchange codes return .SZ."""
        for code in ["000001", "002594", "300750"]:
            with self.subTest(code=code):
                self.assertEqual(get_exchange_for_a_share(code), ".SZ")

    def test_beijing_exchange(self):
        """Beijing Stock Exchange codes return .BJ."""
        for code in ["430001", "830001", "870001"]:
            with self.subTest(code=code):
                self.assertEqual(get_exchange_for_a_share(code), ".BJ")

    def test_already_has_suffix(self):
        """Tickers with existing suffix return that suffix."""
        self.assertEqual(get_exchange_for_a_share("600519.SS"), ".SS")
        self.assertEqual(get_exchange_for_a_share("600519.SH"), ".SS")
        self.assertEqual(get_exchange_for_a_share("000001.SZ"), ".SZ")

    def test_non_a_share_returns_none(self):
        """Non A-share tickers return None."""
        self.assertIsNone(get_exchange_for_a_share("AAPL"))
        self.assertIsNone(get_exchange_for_a_share("0700.HK"))


if __name__ == "__main__":
    unittest.main()
