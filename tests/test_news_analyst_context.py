"""Tests for news analyst runtime context lifecycle."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tradingagents.agents.analysts.news_analyst import create_news_analyst
from tradingagents.dataflows.config import get_config, set_config


class _DummyPrompt:
    def __init__(self, chain):
        self._chain = chain

    def partial(self, **kwargs):
        return self

    def __or__(self, _other):
        return self._chain


class _DummyLLM:
    def bind_tools(self, _tools):
        return object()


class NewsAnalystContextLifecycleTests(unittest.TestCase):
    def setUp(self):
        set_config({"active_instrument": None})

    def tearDown(self):
        set_config({"active_instrument": None})

    def test_news_analyst_clears_active_instrument_after_invoke(self):
        seen = {"active": None}

        class _Chain:
            def invoke(self, _messages):
                seen["active"] = get_config().get("active_instrument")
                return SimpleNamespace(tool_calls=[], content="report")

        with patch(
            "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate.from_messages",
            return_value=_DummyPrompt(_Chain()),
        ):
            node = create_news_analyst(_DummyLLM())
            result = node(
                {
                    "trade_date": "2024-01-10",
                    "company_of_interest": "BTCUSDT",
                    "messages": [],
                }
            )

        self.assertEqual(seen["active"], "BTCUSDT")
        self.assertIsNone(get_config().get("active_instrument"))
        self.assertEqual(result["news_report"], "report")


if __name__ == "__main__":
    unittest.main()
