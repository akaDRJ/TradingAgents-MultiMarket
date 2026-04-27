"""Tests for index-specific fundamentals analyst behavior."""

import unittest

from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst


class _ExplodingLLM:
    def bind_tools(self, _tools):
        raise AssertionError("company fundamentals tools should not be bound for index instruments")


class IndexFundamentalsAnalystTests(unittest.TestCase):
    def test_index_returns_non_company_placeholder_report(self):
        node = create_fundamentals_analyst(_ExplodingLLM())
        result = node(
            {
                "trade_date": "2026-04-09",
                "company_of_interest": "上证指数",
                "messages": [],
            }
        )

        self.assertIn("000001.SS", result["fundamentals_report"])
        self.assertIn("not a single operating company", result["fundamentals_report"].lower())
        self.assertIn("index", result["fundamentals_report"].lower())
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0].tool_calls, [])


if __name__ == "__main__":
    unittest.main()
