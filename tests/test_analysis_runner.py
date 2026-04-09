import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tradingagents.app.analysis_request import build_default_request
from tradingagents.app.analysis_runner import run_analysis_request


class _FakeStreamGraph:
    def stream(self, init_state, **kwargs):
        yield {
            "messages": [],
            "market_report": "Market says buy",
            "sentiment_report": "",
            "news_report": "",
            "fundamentals_report": "",
            "investment_debate_state": {
                "bull_history": "",
                "bear_history": "",
                "judge_decision": "",
            },
            "trader_investment_plan": "",
            "risk_debate_state": {
                "aggressive_history": "",
                "conservative_history": "",
                "neutral_history": "",
                "judge_decision": "BUY",
            },
            "final_trade_decision": "BUY",
            "company_of_interest": init_state["company_of_interest"],
            "trade_date": init_state["trade_date"],
        }


class _FakePropagator:
    def create_initial_state(self, company_name, trade_date):
        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "trade_date": trade_date,
        }

    def get_graph_args(self, callbacks=None):
        return {"stream_mode": "values", "config": {"callbacks": callbacks or []}}


class _FakeTradingAgentsGraph:
    def __init__(self, selected_analysts, config, debug, callbacks):
        self.selected_analysts = selected_analysts
        self.config = config
        self.debug = debug
        self.callbacks = callbacks
        self.propagator = _FakePropagator()
        self.graph = _FakeStreamGraph()

    def process_signal(self, final_trade_decision):
        return final_trade_decision


class AnalysisRunnerTests(unittest.TestCase):
    @patch("tradingagents.app.analysis_runner.TradingAgentsGraph", _FakeTradingAgentsGraph)
    def test_run_analysis_request_writes_report_and_returns_result(self):
        request = build_default_request("NVDA", "2026-04-09")
        events = []

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_analysis_request(
                request,
                results_dir=Path(tmpdir),
                event_sink=events.append,
            )

            self.assertEqual(result.decision, "BUY")
            self.assertTrue(result.report_file.exists())
            self.assertEqual(result.report_file.name, "complete_report.md")
            self.assertTrue(any(event["type"] == "job_started" for event in events))
            self.assertTrue(any(event["type"] == "stage" for event in events))
            self.assertTrue(any(event["type"] == "job_finished" for event in events))


if __name__ == "__main__":
    unittest.main()
