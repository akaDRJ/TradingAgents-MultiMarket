import unittest
from unittest.mock import patch

from cli.models import AnalystType
from cli.runner_bridge import build_request_from_selections, run_cli_analysis


class CliRunnerBridgeTests(unittest.TestCase):
    def test_build_request_from_selections_maps_cli_values(self):
        request = build_request_from_selections(
            {
                "ticker": "BTCUSDT",
                "analysis_date": "2026-04-09",
                "analysts": [AnalystType.MARKET, AnalystType.NEWS],
                "research_depth": 5,
                "llm_provider": "openai",
                "backend_url": "https://api.openai.com/v1",
                "shallow_thinker": "gpt-5.4-mini",
                "deep_thinker": "gpt-5.4",
                "google_thinking_level": None,
                "openai_reasoning_effort": "medium",
                "anthropic_effort": None,
                "output_language": "Chinese",
            }
        )

        self.assertEqual(request.ticker, "BTCUSDT")
        self.assertEqual(request.analysts, ("market", "news"))
        self.assertEqual(request.openai_reasoning_effort, "medium")
        self.assertEqual(request.output_language, "Chinese")

    @patch("cli.runner_bridge.run_analysis_request")
    def test_run_cli_analysis_hands_request_to_shared_runner(self, mock_run_analysis_request):
        mock_run_analysis_request.return_value = object()
        selections = {
            "ticker": "NVDA",
            "analysis_date": "2026-04-09",
            "analysts": [AnalystType.MARKET],
            "research_depth": 1,
            "llm_provider": "openai",
            "backend_url": "https://api.openai.com/v1",
            "shallow_thinker": "gpt-5.4-mini",
            "deep_thinker": "gpt-5.4",
            "google_thinking_level": None,
            "openai_reasoning_effort": None,
            "anthropic_effort": None,
            "output_language": "English",
        }

        run_cli_analysis(selections)

        self.assertTrue(mock_run_analysis_request.called)


if __name__ == "__main__":
    unittest.main()
