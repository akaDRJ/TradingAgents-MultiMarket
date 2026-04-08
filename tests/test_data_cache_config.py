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

    def test_trading_graph_uses_configured_data_cache_dir_in_source(self):
        source = Path("tradingagents/graph/trading_graph.py").read_text()
        self.assertIn('self.config["data_cache_dir"]', source)


if __name__ == "__main__":
    unittest.main()
