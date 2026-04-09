import tempfile
import unittest
from pathlib import Path

from cli.main import finalize_analysis_output


class FinalizeAnalysisOutputTests(unittest.TestCase):
    def test_noninteractive_mode_saves_default_report_without_prompts(self):
        final_state = {"final_trade_decision": "BUY"}
        selections = {"ticker": "000960", "analysis_date": "2026-04-09"}
        config = {"results_dir": "./results"}
        prompt_calls = []
        save_calls = []
        display_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            config["results_dir"] = tmpdir

            def fake_prompt(*args, **kwargs):
                prompt_calls.append((args, kwargs))
                return "N"

            def fake_save_report(state, ticker, save_path, include_subdirectories=True):
                save_calls.append((state, ticker, save_path, include_subdirectories))
                save_path.mkdir(parents=True, exist_ok=True)
                report_file = save_path / "complete_report.md"
                report_file.write_text("ok")
                return report_file

            def fake_display(final):
                display_calls.append(final)

            result = finalize_analysis_output(
                final_state,
                selections,
                config,
                noninteractive=True,
                prompt_fn=fake_prompt,
                save_report_fn=fake_save_report,
                display_report_fn=fake_display,
            )

            self.assertEqual(prompt_calls, [])
            self.assertEqual(display_calls, [])
            self.assertEqual(len(save_calls), 1)
            self.assertEqual(save_calls[0][1], "000960")
            self.assertFalse(save_calls[0][3])
            self.assertEqual(result["saved_report"].name, "complete_report.md")


if __name__ == "__main__":
    unittest.main()
