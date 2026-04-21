import unittest

from tradingagents.app.options import PROVIDER_CHOICES, get_provider_backend_url


class ProviderOptionsTests(unittest.TestCase):
    def test_provider_choices_include_upstream_provider_expansions(self):
        providers = {provider for _, provider, _ in PROVIDER_CHOICES}

        self.assertTrue({"deepseek", "qwen", "glm", "azure"}.issubset(providers))

    def test_backend_url_lookup_handles_new_provider_endpoints(self):
        self.assertEqual(
            get_provider_backend_url("qwen"),
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.assertEqual(
            get_provider_backend_url("glm"),
            "https://open.bigmodel.cn/api/paas/v4/",
        )
        self.assertIsNone(get_provider_backend_url("azure"))


if __name__ == "__main__":
    unittest.main()
