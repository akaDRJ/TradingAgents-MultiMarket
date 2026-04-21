import importlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch


class DataCacheConfigTests(unittest.TestCase):
    def test_default_config_respects_data_cache_env_override(self):
        with patch.dict(
            os.environ,
            {"TRADINGAGENTS_DATA_CACHE_DIR": "/tmp/tradingagents-cache-test"},
            clear=False,
        ):
            module = importlib.import_module("tradingagents.default_config")
            module = importlib.reload(module)
            self.assertEqual(
                module.DEFAULT_CONFIG["data_cache_dir"],
                "/tmp/tradingagents-cache-test",
            )

    def test_default_config_supports_upstream_cache_env_name(self):
        with patch.dict(
            os.environ,
            {"TRADINGAGENTS_CACHE_DIR": "/tmp/tradingagents-cache-alias"},
            clear=False,
        ):
            module = importlib.import_module("tradingagents.default_config")
            module = importlib.reload(module)
            self.assertEqual(
                module.DEFAULT_CONFIG["data_cache_dir"],
                "/tmp/tradingagents-cache-alias",
            )

    def test_trading_graph_creates_configured_cache_and_results_dirs(self):
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        config = DEFAULT_CONFIG.copy()
        config.update(
            {
                "data_cache_dir": "/tmp/tradingagents-cache-dir",
                "results_dir": "/tmp/tradingagents-results-dir",
            }
        )

        fake_client = type("FakeClient", (), {"get_llm": lambda self: object()})
        fake_graph_setup = type(
            "FakeGraphSetup",
            (),
            {
                "__init__": lambda self, *args, **kwargs: None,
                "setup_graph": lambda self, selected_analysts: object(),
            },
        )

        with patch("tradingagents.graph.trading_graph.set_config"), patch(
            "tradingagents.graph.trading_graph.os.makedirs"
        ) as mock_makedirs, patch(
            "tradingagents.graph.trading_graph.create_llm_client",
            return_value=fake_client(),
        ), patch(
            "tradingagents.graph.trading_graph.FinancialSituationMemory",
            return_value=object(),
        ), patch(
            "tradingagents.graph.trading_graph.GraphSetup",
            fake_graph_setup,
        ), patch(
            "tradingagents.graph.trading_graph.Propagator",
            return_value=object(),
        ), patch(
            "tradingagents.graph.trading_graph.Reflector",
            return_value=object(),
        ), patch(
            "tradingagents.graph.trading_graph.SignalProcessor",
            return_value=object(),
        ):
            TradingAgentsGraph(config=config)

        mock_makedirs.assert_any_call("/tmp/tradingagents-cache-dir", exist_ok=True)
        mock_makedirs.assert_any_call("/tmp/tradingagents-results-dir", exist_ok=True)


if __name__ == "__main__":
    unittest.main()
