import unittest

from tradingagents.app.analysis_request import AnalysisRequest, build_default_request


class AnalysisRequestTests(unittest.TestCase):
    def test_build_default_request_uses_repo_defaults(self):
        request = build_default_request(ticker="NVDA", analysis_date="2026-04-09")

        self.assertEqual(request.llm_provider, "openai")
        self.assertEqual(request.quick_model, "gpt-5.4-mini")
        self.assertEqual(request.deep_model, "gpt-5.4")
        self.assertEqual(
            request.analysts,
            ("market", "social", "news", "fundamentals"),
        )
        self.assertEqual(request.output_language, "English")

    def test_validate_rejects_future_dates(self):
        request = build_default_request(ticker="NVDA", analysis_date="2999-01-01")

        with self.assertRaisesRegex(ValueError, "future"):
            request.validate()

    def test_to_config_maps_depth_models_and_reasoning_effort(self):
        request = AnalysisRequest(
            ticker="BTCUSDT",
            analysis_date="2026-04-09",
            analysts=("market", "news"),
            output_language="Chinese",
            research_depth=3,
            llm_provider="openai",
            backend_url="https://api.openai.com/v1",
            quick_model="gpt-5.4-mini",
            deep_model="gpt-5.4",
            openai_reasoning_effort="high",
        )

        config = request.to_config()

        self.assertEqual(config["max_debate_rounds"], 3)
        self.assertEqual(config["max_risk_discuss_rounds"], 3)
        self.assertEqual(config["quick_think_llm"], "gpt-5.4-mini")
        self.assertEqual(config["deep_think_llm"], "gpt-5.4")
        self.assertEqual(config["output_language"], "Chinese")
        self.assertEqual(config["openai_reasoning_effort"], "high")


if __name__ == "__main__":
    unittest.main()
