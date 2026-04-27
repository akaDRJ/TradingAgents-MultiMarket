import unittest

import pytest

from cli.utils import normalize_ticker_symbol
from tradingagents.agents.utils.agent_utils import build_instrument_context


@pytest.mark.unit
class TickerSymbolHandlingTests(unittest.TestCase):
    def test_normalize_ticker_symbol_preserves_exchange_suffix(self):
        self.assertEqual(normalize_ticker_symbol(" cnc.to "), "CNC.TO")

    def test_normalize_ticker_symbol_maps_shanghai_composite_aliases(self):
        self.assertEqual(normalize_ticker_symbol(" 上证指数 "), "000001.SS")
        self.assertEqual(normalize_ticker_symbol("沪指"), "000001.SS")
        self.assertEqual(normalize_ticker_symbol("上证综指"), "000001.SS")
        self.assertEqual(normalize_ticker_symbol("000001.SH"), "000001.SS")

    def test_build_instrument_context_mentions_exact_symbol(self):
        context = build_instrument_context("7203.T")
        self.assertIn("7203.T", context)
        self.assertIn("exchange suffix", context)

    def test_build_instrument_context_marks_index_instruments(self):
        context = build_instrument_context("000001.SS")
        self.assertIn("000001.SS", context)
        self.assertIn("index", context.lower())
        self.assertIn("not a single operating company", context.lower())


if __name__ == "__main__":
    unittest.main()
