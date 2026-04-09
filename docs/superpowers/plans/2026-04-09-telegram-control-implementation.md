# Telegram Control Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a private Telegram control surface to `TradingAgents-MultiMarket` that exposes the full CLI option set, remembers the last successful configuration, and supports `/analyze`, `/status`, and `/cancel` on top of a shared non-interactive analysis runner.

**Architecture:** Extract a shared, event-driven analysis runner from the current CLI path so both CLI and Telegram use the same execution core and report-writing logic. Add a polling `python-telegram-bot` service that manages a single-user draft session, persists active job state to disk, spawns a worker subprocess for runs, and sends back the final report artifact. Keep provider/model rendering data in a shared option catalog so future provider additions show up in Telegram without Telegram-specific rewiring.

**Tech Stack:** Python 3.12, `unittest`, `python-telegram-bot`, existing `Typer` CLI, existing `TradingAgentsGraph`, existing report artifact layout under `results/`.

---

## File Structure

- `tradingagents/app/__init__.py`
  - Shared application-layer exports.
- `tradingagents/app/options.py`
  - Shared option catalogs for provider choices, output languages, research depth, and provider-specific settings. This is the single source of truth for both CLI and Telegram.
- `tradingagents/app/analysis_request.py`
  - Structured request dataclass, validation, JSON payload helpers, and config translation.
- `tradingagents/app/reporting.py`
  - Shared report path and artifact writing helpers currently owned by the CLI.
- `tradingagents/app/analysis_runner.py`
  - Non-interactive event-driven execution path used by CLI and Telegram.
- `cli/runner_bridge.py`
  - CLI-specific request building and event-to-UI mapping.
- `cli/utils.py`
  - Updated to read shared option catalogs instead of defining them inline.
- `cli/main.py`
  - Updated to use the shared runner through the CLI bridge.
- `cli/reporting.py`
  - Thin compatibility wrapper around shared reporting helpers.
- `tradingagents/telegram_bot/__init__.py`
  - Telegram package exports.
- `tradingagents/telegram_bot/store.py`
  - JSON persistence for last-successful config, draft session, and active job metadata.
- `tradingagents/telegram_bot/draft.py`
  - Draft mutation helpers for provider/model compatibility and reset-to-default behavior.
- `tradingagents/telegram_bot/presentation.py`
  - Summary/status text builders shared by handlers and tests.
- `tradingagents/telegram_bot/keyboards.py`
  - Inline keyboard builders for the Telegram flow.
- `tradingagents/telegram_bot/service.py`
  - Telegram-native draft editing flow, callback routing, and cancel-and-switch decisions.
- `tradingagents/telegram_bot/runtime.py`
  - Job controller for spawning, tracking, and cancelling the worker subprocess.
- `tradingagents/telegram_bot/worker.py`
  - Subprocess entrypoint that loads an `AnalysisRequest`, runs the shared runner, and writes active-job updates.
- `tradingagents/telegram_bot/main.py`
  - `python-telegram-bot` polling app, command handlers, callback routing, and text-input flow.
- `.env.example`
  - Add Telegram-specific environment variables.
- `docker-compose.yml`
  - Add `telegram-bot` service.
- `pyproject.toml`
  - Add `python-telegram-bot` dependency and Telegram entrypoint script.
- `README.md`
  - Add a brief Telegram setup and run section.
- `tests/test_analysis_request.py`
  - Shared request and validation coverage.
- `tests/test_analysis_runner.py`
  - Shared runner coverage with a fake graph.
- `tests/test_cli_runner_bridge.py`
  - CLI request-building and runner handoff coverage.
- `tests/test_report_save_path.py`
  - Keep report artifact behavior green after moving reporting helpers.
- `tests/test_telegram_store.py`
  - Persistence and draft compatibility coverage.
- `tests/test_telegram_presentation.py`
  - Summary/status formatting and keyboard-safe content coverage.
- `tests/test_telegram_service.py`
  - Full-option draft editing, awaiting-text flow, and cancel-and-switch coverage.
- `tests/test_telegram_runtime.py`
  - Worker process lifecycle, `/cancel`, and completion delivery coverage.

### Task 1: Add Shared Option Catalogs And Analysis Request Schema

**Files:**
- Create: `tradingagents/app/__init__.py`
- Create: `tradingagents/app/options.py`
- Create: `tradingagents/app/analysis_request.py`
- Test: `tests/test_analysis_request.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_analysis_request -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'tradingagents.app'`

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/app/options.py
from __future__ import annotations

from typing import Dict, List, Tuple

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.model_catalog import get_model_options

ModelChoice = Tuple[str, str]

DEFAULT_ANALYSTS = ("market", "social", "news", "fundamentals")

PROVIDER_CHOICES = (
    ("OpenAI", "openai", "https://api.openai.com/v1"),
    ("Google", "google", None),
    ("Anthropic", "anthropic", "https://api.anthropic.com/"),
    ("MiniMax", "minimax", "https://api.minimaxi.com/anthropic"),
    ("xAI", "xai", "https://api.x.ai/v1"),
    ("OpenRouter", "openrouter", "https://openrouter.ai/api/v1"),
    ("Ollama", "ollama", "http://localhost:11434/v1"),
)

RESEARCH_DEPTH_CHOICES = (
    ("Shallow", 1),
    ("Medium", 3),
    ("Deep", 5),
)

OUTPUT_LANGUAGE_CHOICES = (
    "English",
    "Chinese",
    "Japanese",
    "Korean",
    "Hindi",
    "Spanish",
    "Portuguese",
    "French",
    "German",
    "Arabic",
    "Russian",
)

PROVIDER_SETTING_CHOICES: Dict[str, List[ModelChoice]] = {
    "openai": [
        ("Medium (Default)", "medium"),
        ("High", "high"),
        ("Low", "low"),
    ],
    "anthropic": [
        ("High (recommended)", "high"),
        ("Medium", "medium"),
        ("Low", "low"),
    ],
    "google": [
        ("Enable Thinking", "high"),
        ("Minimal / Disable Thinking", "minimal"),
    ],
}


def get_provider_backend_url(provider: str) -> str | None:
    for _, value, backend_url in PROVIDER_CHOICES:
        if value == provider:
            return backend_url
    raise KeyError(provider)


def get_default_models(provider: str) -> tuple[str, str]:
    provider_lower = provider.lower()
    return (
        get_model_options(provider_lower, "quick")[0][1],
        get_model_options(provider_lower, "deep")[0][1],
    )


def get_default_request_values() -> dict:
    return {
        "llm_provider": DEFAULT_CONFIG["llm_provider"],
        "backend_url": DEFAULT_CONFIG["backend_url"],
        "quick_model": DEFAULT_CONFIG["quick_think_llm"],
        "deep_model": DEFAULT_CONFIG["deep_think_llm"],
        "output_language": DEFAULT_CONFIG["output_language"],
        "research_depth": DEFAULT_CONFIG["max_debate_rounds"],
        "analysts": DEFAULT_ANALYSTS,
    }
```

```python
# tradingagents/app/analysis_request.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime

from tradingagents.default_config import DEFAULT_CONFIG

from .options import DEFAULT_ANALYSTS, get_default_request_values


@dataclass(frozen=True)
class AnalysisRequest:
    ticker: str
    analysis_date: str
    analysts: tuple[str, ...]
    output_language: str
    research_depth: int
    llm_provider: str
    backend_url: str | None
    quick_model: str
    deep_model: str
    google_thinking_level: str | None = None
    openai_reasoning_effort: str | None = None
    anthropic_effort: str | None = None

    def validate(self, today: date | None = None) -> None:
        parsed = datetime.strptime(self.analysis_date, "%Y-%m-%d").date()
        today = today or date.today()
        if parsed > today:
            raise ValueError("analysis_date cannot be in the future")
        if not self.ticker.strip():
            raise ValueError("ticker is required")
        if not self.analysts:
            raise ValueError("at least one analyst is required")

    def to_config(self) -> dict:
        config = DEFAULT_CONFIG.copy()
        config["max_debate_rounds"] = self.research_depth
        config["max_risk_discuss_rounds"] = self.research_depth
        config["quick_think_llm"] = self.quick_model
        config["deep_think_llm"] = self.deep_model
        config["backend_url"] = self.backend_url
        config["llm_provider"] = self.llm_provider
        config["output_language"] = self.output_language
        config["google_thinking_level"] = self.google_thinking_level
        config["openai_reasoning_effort"] = self.openai_reasoning_effort
        config["anthropic_effort"] = self.anthropic_effort
        return config

    def to_payload(self) -> dict:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict) -> "AnalysisRequest":
        payload = dict(payload)
        payload["analysts"] = tuple(payload["analysts"])
        return cls(**payload)


def build_default_request(ticker: str, analysis_date: str) -> AnalysisRequest:
    defaults = get_default_request_values()
    return AnalysisRequest(
        ticker=ticker,
        analysis_date=analysis_date,
        analysts=tuple(defaults["analysts"] or DEFAULT_ANALYSTS),
        output_language=defaults["output_language"],
        research_depth=defaults["research_depth"],
        llm_provider=defaults["llm_provider"],
        backend_url=defaults["backend_url"],
        quick_model=defaults["quick_model"],
        deep_model=defaults["deep_model"],
    )
```

```python
# tradingagents/app/__init__.py
from .analysis_request import AnalysisRequest, build_default_request

__all__ = ["AnalysisRequest", "build_default_request"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_analysis_request -v`

Expected:

```text
test_build_default_request_uses_repo_defaults ... ok
test_to_config_maps_depth_models_and_reasoning_effort ... ok
test_validate_rejects_future_dates ... ok
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_analysis_request.py \
  tradingagents/app/__init__.py \
  tradingagents/app/options.py \
  tradingagents/app/analysis_request.py
git commit -m "feat: add shared analysis request schema"
```

### Task 2: Add Shared Reporting Helpers And Non-Interactive Analysis Runner

**Files:**
- Create: `tradingagents/app/reporting.py`
- Create: `tradingagents/app/analysis_runner.py`
- Modify: `cli/reporting.py`
- Modify: `tests/test_report_save_path.py`
- Test: `tests/test_analysis_runner.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_analysis_runner -v`

Expected: FAIL with `ImportError: cannot import name 'run_analysis_request'`

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/app/reporting.py
import datetime
from pathlib import Path


def build_default_report_save_path(config: dict, ticker: str, analysis_date: str) -> Path:
    return Path(config["results_dir"]) / ticker / analysis_date / "reports"


def save_report_to_disk(final_state, ticker: str, save_path: Path, include_subdirectories: bool = True):
    save_path.mkdir(parents=True, exist_ok=True)
    sections = []

    if final_state.get("market_report"):
        sections.append(f"## I. Analyst Team Reports\n\n### Market Analyst\n{final_state['market_report']}")
    if final_state.get("trader_investment_plan"):
        sections.append(f"## III. Trading Team Plan\n\n### Trader\n{final_state['trader_investment_plan']}")
    if final_state.get("risk_debate_state", {}).get("judge_decision"):
        sections.append(
            "## V. Portfolio Manager Decision\n\n### Portfolio Manager\n"
            f"{final_state['risk_debate_state']['judge_decision']}"
        )

    report_file = save_path / "complete_report.md"
    header = (
        f"# Trading Analysis Report: {ticker}\n\n"
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )
    report_file.write_text(header + "\n\n".join(sections))
    return report_file
```

```python
# tradingagents/app/analysis_runner.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from cli.stats_handler import StatsCallbackHandler
from tradingagents.graph.trading_graph import TradingAgentsGraph

from .analysis_request import AnalysisRequest
from .reporting import build_default_report_save_path, save_report_to_disk


@dataclass(frozen=True)
class AnalysisRunResult:
    final_state: dict
    decision: str
    result_dir: Path
    report_file: Path
    stats: dict


def run_analysis_request(
    request: AnalysisRequest,
    results_dir: Path | None = None,
    event_sink: Callable[[dict], None] | None = None,
) -> AnalysisRunResult:
    request.validate()
    config = request.to_config()
    if results_dir is not None:
        config["results_dir"] = str(results_dir)

    stats_handler = StatsCallbackHandler()
    graph = TradingAgentsGraph(
        list(request.analysts),
        config=config,
        debug=True,
        callbacks=[stats_handler],
    )

    init_state = graph.propagator.create_initial_state(request.ticker, request.analysis_date)
    args = graph.propagator.get_graph_args(callbacks=[stats_handler])

    if event_sink:
        event_sink({"type": "job_started", "ticker": request.ticker, "analysis_date": request.analysis_date})

    final_state = None
    for chunk in graph.graph.stream(init_state, **args):
        final_state = chunk
        if event_sink:
            event_sink(
                {
                    "type": "stage",
                    "current_stage": "Portfolio Management"
                    if chunk.get("final_trade_decision")
                    else "Analyst Team",
                }
            )

    if final_state is None:
        raise RuntimeError("analysis runner received no graph output")

    decision = graph.process_signal(final_state["final_trade_decision"])
    result_path = build_default_report_save_path(config, request.ticker, request.analysis_date)
    report_file = save_report_to_disk(final_state, request.ticker, result_path, include_subdirectories=False)

    if event_sink:
        event_sink({"type": "job_finished", "decision": decision, "report_file": str(report_file)})

    return AnalysisRunResult(
        final_state=final_state,
        decision=decision,
        result_dir=result_path.parent,
        report_file=report_file,
        stats=stats_handler.get_stats(),
    )
```

```python
# cli/reporting.py
from tradingagents.app.reporting import build_default_report_save_path, save_report_to_disk

__all__ = ["build_default_report_save_path", "save_report_to_disk"]
```

```python
# tests/test_report_save_path.py
from tradingagents.app.reporting import build_default_report_save_path, save_report_to_disk
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_analysis_runner tests.test_report_save_path -v`

Expected:

```text
test_run_analysis_request_writes_report_and_returns_result ... ok
test_default_report_save_path_uses_results_report_dir ... ok
test_save_report_to_disk_can_write_only_complete_report ... ok
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_analysis_runner.py \
  tests/test_report_save_path.py \
  tradingagents/app/reporting.py \
  tradingagents/app/analysis_runner.py \
  cli/reporting.py
git commit -m "feat: add shared analysis runner"
```

### Task 3: Refactor CLI To Use Shared Options And Shared Runner

**Files:**
- Create: `cli/runner_bridge.py`
- Modify: `cli/utils.py`
- Modify: `cli/main.py`
- Test: `tests/test_cli_runner_bridge.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_cli_runner_bridge -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'cli.runner_bridge'`

- [ ] **Step 3: Write minimal implementation**

```python
# cli/runner_bridge.py
from __future__ import annotations

from tradingagents.app.analysis_request import AnalysisRequest
from tradingagents.app.analysis_runner import run_analysis_request


def build_request_from_selections(selections: dict) -> AnalysisRequest:
    return AnalysisRequest(
        ticker=selections["ticker"],
        analysis_date=selections["analysis_date"],
        analysts=tuple(analyst.value for analyst in selections["analysts"]),
        output_language=selections.get("output_language", "English"),
        research_depth=selections["research_depth"],
        llm_provider=selections["llm_provider"].lower(),
        backend_url=selections["backend_url"],
        quick_model=selections["shallow_thinker"],
        deep_model=selections["deep_thinker"],
        google_thinking_level=selections.get("google_thinking_level"),
        openai_reasoning_effort=selections.get("openai_reasoning_effort"),
        anthropic_effort=selections.get("anthropic_effort"),
    )


def run_cli_analysis(selections: dict):
    request = build_request_from_selections(selections)
    return run_analysis_request(request)
```

```python
# cli/utils.py
from tradingagents.app.options import (
    OUTPUT_LANGUAGE_CHOICES,
    PROVIDER_CHOICES,
    PROVIDER_SETTING_CHOICES,
    RESEARCH_DEPTH_CHOICES,
)

def select_llm_provider() -> tuple[str, str | None]:
    choice = questionary.select(
        "Select your LLM Provider:",
        choices=[
            questionary.Choice(label, value=(provider, backend_url))
            for label, provider, backend_url in PROVIDER_CHOICES
        ],
    ).ask()
    if choice is None:
        console.print("\n[red]no backend selected. Exiting...[/red]")
        exit(1)
    return choice

def ask_output_language() -> str:
    choice = questionary.select(
        "Select Output Language:",
        choices=[questionary.Choice(language, language) for language in OUTPUT_LANGUAGE_CHOICES]
        + [questionary.Choice("Custom language", "custom")],
    ).ask()
    if choice == "custom":
        return questionary.text("Enter language name:").ask().strip()
    return choice
```

```python
# cli/main.py
from cli.runner_bridge import run_cli_analysis

def run_analysis():
    selections = get_user_selections()
    result = run_cli_analysis(selections)
    final_state = result.final_state
    # keep the existing post-run save/display prompts below this line
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_cli_runner_bridge -v`

Expected:

```text
test_build_request_from_selections_maps_cli_values ... ok
test_run_cli_analysis_hands_request_to_shared_runner ... ok
```

- [ ] **Step 5: Run the existing CLI-facing regression**

Run: `uv run python -m unittest tests.test_model_validation tests.test_report_save_path tests.test_cli_runner_bridge -v`

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_cli_runner_bridge.py \
  cli/runner_bridge.py \
  cli/utils.py \
  cli/main.py
git commit -m "refactor: route cli through shared runner"
```

### Task 4: Add Telegram State Persistence And Draft Compatibility Logic

**Files:**
- Create: `tradingagents/telegram_bot/__init__.py`
- Create: `tradingagents/telegram_bot/store.py`
- Create: `tradingagents/telegram_bot/draft.py`
- Test: `tests/test_telegram_store.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from tradingagents.app.analysis_request import build_default_request
from tradingagents.telegram_bot.draft import DraftSession, apply_provider_change
from tradingagents.telegram_bot.store import TelegramStateStore


class TelegramStoreTests(unittest.TestCase):
    def test_store_round_trips_last_successful_request(self):
        request = build_default_request("NVDA", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_last_successful(request)

            loaded = store.load_last_successful()

            self.assertEqual(loaded.ticker, "NVDA")
            self.assertEqual(loaded.deep_model, "gpt-5.4")

    def test_store_round_trips_draft_session_metadata(self):
        request = build_default_request("BTCUSDT", "2026-04-09")
        session = DraftSession(
            request=request,
            awaiting_field="ticker",
            summary_message_id=99,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_draft_session(session)

            loaded = store.load_draft_session()

            self.assertEqual(loaded.awaiting_field, "ticker")
            self.assertEqual(loaded.summary_message_id, 99)
            self.assertEqual(loaded.request.ticker, "BTCUSDT")

    def test_apply_provider_change_replaces_models_and_clears_incompatible_effort(self):
        request = build_default_request("NVDA", "2026-04-09")
        request = request.__class__(**{**request.to_payload(), "openai_reasoning_effort": "high"})

        updated = apply_provider_change(request, "anthropic")

        self.assertEqual(updated.llm_provider, "anthropic")
        self.assertIsNone(updated.openai_reasoning_effort)
        self.assertIsNotNone(updated.quick_model)
        self.assertIsNotNone(updated.deep_model)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_telegram_store -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'tradingagents.telegram_bot'`

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/telegram_bot/draft.py
from __future__ import annotations

from dataclasses import asdict, dataclass

from tradingagents.app.analysis_request import AnalysisRequest
from tradingagents.app.options import (
    PROVIDER_SETTING_CHOICES,
    get_default_models,
    get_provider_backend_url,
)


@dataclass(frozen=True)
class DraftSession:
    request: AnalysisRequest
    awaiting_field: str | None = None
    summary_message_id: int | None = None

    def to_payload(self) -> dict:
        payload = asdict(self)
        payload["request"] = self.request.to_payload()
        return payload

    @classmethod
    def from_payload(cls, payload: dict) -> "DraftSession":
        return cls(
            request=AnalysisRequest.from_payload(payload["request"]),
            awaiting_field=payload.get("awaiting_field"),
            summary_message_id=payload.get("summary_message_id"),
        )

    def with_request(self, request: AnalysisRequest) -> "DraftSession":
        return DraftSession(
            request=request,
            awaiting_field=self.awaiting_field,
            summary_message_id=self.summary_message_id,
        )


def apply_provider_change(request: AnalysisRequest, provider: str) -> AnalysisRequest:
    quick_model, deep_model = get_default_models(provider)
    payload = request.to_payload()
    payload.update(
        {
            "llm_provider": provider,
            "backend_url": get_provider_backend_url(provider),
            "quick_model": quick_model,
            "deep_model": deep_model,
            "google_thinking_level": None,
            "openai_reasoning_effort": None,
            "anthropic_effort": None,
        }
    )
    if provider == "google":
        payload["google_thinking_level"] = PROVIDER_SETTING_CHOICES["google"][0][1]
    elif provider == "openai":
        payload["openai_reasoning_effort"] = PROVIDER_SETTING_CHOICES["openai"][0][1]
    elif provider == "anthropic":
        payload["anthropic_effort"] = PROVIDER_SETTING_CHOICES["anthropic"][0][1]
    return AnalysisRequest.from_payload(payload)
```

```python
# tradingagents/telegram_bot/store.py
from __future__ import annotations

import json
from pathlib import Path

from tradingagents.app.analysis_request import AnalysisRequest
from tradingagents.telegram_bot.draft import DraftSession


class TelegramStateStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.root / f"{name}.json"

    def load_last_successful(self) -> AnalysisRequest | None:
        path = self._path("last_successful")
        if not path.exists():
            return None
        return AnalysisRequest.from_payload(json.loads(path.read_text()))

    def save_last_successful(self, request: AnalysisRequest) -> None:
        self._path("last_successful").write_text(json.dumps(request.to_payload(), indent=2))

    def load_draft_session(self) -> DraftSession | None:
        path = self._path("draft_session")
        if not path.exists():
            return None
        return DraftSession.from_payload(json.loads(path.read_text()))

    def save_draft_session(self, session: DraftSession) -> None:
        self._path("draft_session").write_text(json.dumps(session.to_payload(), indent=2))

    def load_active_job(self) -> dict | None:
        path = self._path("active_job")
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_active_job(self, payload: dict) -> None:
        self._path("active_job").write_text(json.dumps(payload, indent=2))

    def clear_active_job(self) -> None:
        path = self._path("active_job")
        if path.exists():
            path.unlink()
```

```python
# tradingagents/telegram_bot/__init__.py
from .draft import DraftSession
from .store import TelegramStateStore

__all__ = ["DraftSession", "TelegramStateStore"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_telegram_store -v`

Expected:

```text
test_apply_provider_change_replaces_models_and_clears_incompatible_effort ... ok
test_store_round_trips_draft_session_metadata ... ok
test_store_round_trips_last_successful_request ... ok
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_telegram_store.py \
  tradingagents/telegram_bot/__init__.py \
  tradingagents/telegram_bot/store.py \
  tradingagents/telegram_bot/draft.py
git commit -m "feat: add telegram draft persistence"
```

### Task 5: Add Telegram Summary Rendering And Inline Keyboard Builders

**Files:**
- Create: `tradingagents/telegram_bot/presentation.py`
- Create: `tradingagents/telegram_bot/keyboards.py`
- Test: `tests/test_telegram_presentation.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from tradingagents.app.analysis_request import build_default_request
from tradingagents.telegram_bot.keyboards import build_choice_keyboard, build_main_menu_keyboard
from tradingagents.telegram_bot.presentation import build_draft_summary, build_status_text


class TelegramPresentationTests(unittest.TestCase):
    def test_build_draft_summary_lists_full_cli_option_set(self):
        request = build_default_request("BTCUSDT", "2026-04-09")

        summary = build_draft_summary(request)

        self.assertIn("Ticker", summary)
        self.assertIn("Analysis Date", summary)
        self.assertIn("Output Language", summary)
        self.assertIn("LLM Provider", summary)
        self.assertIn("Quick Model", summary)
        self.assertIn("Deep Model", summary)

    def test_build_status_text_shows_running_job_fields(self):
        status = build_status_text(
            {
                "status": "running",
                "ticker": "BTCUSDT",
                "analysis_date": "2026-04-09",
                "research_depth": 5,
                "llm_provider": "openai",
                "quick_model": "gpt-5.4-mini",
                "deep_model": "gpt-5.4",
                "current_stage": "Research Team",
            }
        )

        self.assertIn("running", status)
        self.assertIn("BTCUSDT", status)
        self.assertIn("Research Team", status)

    def test_build_main_menu_keyboard_has_start_and_cancel_controls(self):
        keyboard = build_main_menu_keyboard()
        labels = [button.text for row in keyboard.inline_keyboard for button in row]

        self.assertIn("Start Analysis", labels)
        self.assertIn("Restore Last Successful", labels)
        self.assertIn("Reset To Defaults", labels)

    def test_build_choice_keyboard_includes_callback_prefix(self):
        keyboard = build_choice_keyboard(
            "pick:provider",
            [("OpenAI", "openai"), ("Anthropic", "anthropic")],
        )
        callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]

        self.assertIn("pick:provider:openai", callbacks)
        self.assertIn("pick:provider:anthropic", callbacks)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_telegram_presentation -v`

Expected: FAIL with `ImportError: cannot import name 'build_draft_summary'`

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/telegram_bot/presentation.py
from __future__ import annotations

from tradingagents.app.analysis_request import AnalysisRequest


def build_draft_summary(request: AnalysisRequest) -> str:
    return "\n".join(
        [
            "Telegram TradingAgents Draft",
            f"Ticker: {request.ticker}",
            f"Analysis Date: {request.analysis_date}",
            f"Output Language: {request.output_language}",
            f"Analysts: {', '.join(request.analysts)}",
            f"Research Depth: {request.research_depth}",
            f"LLM Provider: {request.llm_provider}",
            f"Quick Model: {request.quick_model}",
            f"Deep Model: {request.deep_model}",
            f"Provider Setting: {request.google_thinking_level or request.openai_reasoning_effort or request.anthropic_effort or '-'}",
        ]
    )


def build_status_text(active_job: dict | None) -> str:
    if not active_job:
        return "Status: idle"
    return "\n".join(
        [
            f"Status: {active_job['status']}",
            f"Ticker: {active_job['ticker']}",
            f"Analysis Date: {active_job['analysis_date']}",
            f"Research Depth: {active_job['research_depth']}",
            f"Models: {active_job['llm_provider']} | quick={active_job['quick_model']} | deep={active_job['deep_model']}",
            f"Current Stage: {active_job.get('current_stage', '-')}",
        ]
    )
```

```python
# tradingagents/telegram_bot/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_choice_keyboard(prefix: str, choices) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"{prefix}:{value}")]
        for label, value in choices
    ]
    rows.append([InlineKeyboardButton("Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Edit Ticker", callback_data="edit:ticker"),
                InlineKeyboardButton("Edit Date", callback_data="edit:analysis_date"),
            ],
            [
                InlineKeyboardButton("Edit Language", callback_data="edit:output_language"),
                InlineKeyboardButton("Edit Analysts", callback_data="edit:analysts"),
            ],
            [
                InlineKeyboardButton("Edit Depth", callback_data="edit:research_depth"),
                InlineKeyboardButton("Edit Provider", callback_data="edit:llm_provider"),
            ],
            [
                InlineKeyboardButton("Edit Quick Model", callback_data="edit:quick_model"),
                InlineKeyboardButton("Edit Deep Model", callback_data="edit:deep_model"),
            ],
            [
                InlineKeyboardButton("Edit Provider Setting", callback_data="edit:provider_setting"),
            ],
            [
                InlineKeyboardButton("Start Analysis", callback_data="run:start"),
            ],
            [
                InlineKeyboardButton("Restore Last Successful", callback_data="draft:restore"),
                InlineKeyboardButton("Reset To Defaults", callback_data="draft:reset"),
            ],
        ]
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_telegram_presentation -v`

Expected:

```text
test_build_draft_summary_lists_full_cli_option_set ... ok
test_build_choice_keyboard_includes_callback_prefix ... ok
test_build_main_menu_keyboard_has_start_and_cancel_controls ... ok
test_build_status_text_shows_running_job_fields ... ok
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_telegram_presentation.py \
  tradingagents/telegram_bot/presentation.py \
  tradingagents/telegram_bot/keyboards.py
git commit -m "feat: add telegram draft presentation"
```

### Task 6: Add Telegram Draft Editing Service And Full-Option Callback Flow

**Files:**
- Create: `tradingagents/telegram_bot/service.py`
- Test: `tests/test_telegram_service.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from tradingagents.app.analysis_request import build_default_request
from tradingagents.telegram_bot.draft import DraftSession
from tradingagents.telegram_bot.service import TelegramControlService
from tradingagents.telegram_bot.store import TelegramStateStore


class TelegramServiceTests(unittest.TestCase):
    def test_begin_analyze_uses_last_successful_when_no_draft_exists(self):
        request = build_default_request("BTCUSDT", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_last_successful(request)
            service = TelegramControlService(store)

            response = service.begin_analyze("2026-04-09")

            self.assertEqual(response["mode"], "draft")
            self.assertIn("BTCUSDT", response["text"])

    def test_begin_analyze_returns_switch_prompt_when_job_is_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_active_job({"status": "running", "ticker": "NVDA"})
            service = TelegramControlService(store)

            response = service.begin_analyze("2026-04-09")

            self.assertEqual(response["mode"], "confirm_switch")
            self.assertIn("Cancel current and switch", response["text"])

    def test_apply_text_input_updates_ticker_and_clears_waiting_flag(self):
        request = build_default_request("SPY", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_draft_session(DraftSession(request=request, awaiting_field="ticker"))
            service = TelegramControlService(store)

            session = service.apply_text_input("BTCUSDT")

            self.assertEqual(session.request.ticker, "BTCUSDT")
            self.assertIsNone(session.awaiting_field)

    def test_apply_provider_choice_resets_models_to_provider_defaults(self):
        request = build_default_request("SPY", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_draft_session(DraftSession(request=request))
            service = TelegramControlService(store)

            session = service.apply_provider_choice("anthropic")

            self.assertEqual(session.request.llm_provider, "anthropic")
            self.assertEqual(session.request.quick_model, "claude-sonnet-4-6")
            self.assertEqual(session.request.deep_model, "claude-opus-4-6")

    def test_apply_choice_updates_research_depth(self):
        request = build_default_request("SPY", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            store.save_draft_session(DraftSession(request=request))
            service = TelegramControlService(store)

            session = service.apply_choice("research_depth", "5")

            self.assertEqual(session.request.research_depth, 5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_telegram_service -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'tradingagents.telegram_bot.service'`

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/telegram_bot/service.py
from __future__ import annotations

from tradingagents.app.analysis_request import AnalysisRequest, build_default_request
from tradingagents.telegram_bot.draft import DraftSession, apply_provider_change
from tradingagents.telegram_bot.presentation import build_draft_summary


class TelegramControlService:
    def __init__(self, store):
        self.store = store

    def _default_request(self, today_str: str) -> AnalysisRequest:
        return build_default_request("SPY", today_str)

    def _get_or_create_draft(self, today_str: str) -> DraftSession:
        session = self.store.load_draft_session()
        if session is not None:
            return session
        last_successful = self.store.load_last_successful()
        request = last_successful or self._default_request(today_str)
        session = DraftSession(request=request)
        self.store.save_draft_session(session)
        return session

    def begin_analyze(self, today_str: str) -> dict:
        active_job = self.store.load_active_job() or {}
        if active_job.get("status") == "running":
            return {
                "mode": "confirm_switch",
                "text": "A job is already running. Cancel current and switch?",
            }

        session = self._get_or_create_draft(today_str)
        return {
            "mode": "draft",
            "text": build_draft_summary(session.request),
        }

    def set_waiting_field(self, field_name: str) -> DraftSession:
        session = self.store.load_draft_session()
        if session is None:
            raise RuntimeError("draft session is missing")
        updated = DraftSession(
            request=session.request,
            awaiting_field=field_name,
            summary_message_id=session.summary_message_id,
        )
        self.store.save_draft_session(updated)
        return updated

    def apply_text_input(self, text: str) -> DraftSession:
        session = self.store.load_draft_session()
        if session is None or session.awaiting_field is None:
            raise RuntimeError("no draft field is waiting for text input")

        payload = session.request.to_payload()
        payload[session.awaiting_field] = text.strip()
        updated_request = AnalysisRequest.from_payload(payload)
        updated_session = DraftSession(
            request=updated_request,
            awaiting_field=None,
            summary_message_id=session.summary_message_id,
        )
        self.store.save_draft_session(updated_session)
        return updated_session

    def apply_provider_choice(self, provider: str) -> DraftSession:
        session = self.store.load_draft_session()
        if session is None:
            raise RuntimeError("draft session is missing")
        updated_request = apply_provider_change(session.request, provider)
        updated_session = session.with_request(updated_request)
        self.store.save_draft_session(updated_session)
        return updated_session

    def apply_choice(self, field_name: str, raw_value: str) -> DraftSession:
        session = self.store.load_draft_session()
        if session is None:
            raise RuntimeError("draft session is missing")

        if field_name == "llm_provider":
            return self.apply_provider_choice(raw_value)

        payload = session.request.to_payload()
        if field_name == "research_depth":
            payload[field_name] = int(raw_value)
        elif field_name == "provider_setting":
            payload["google_thinking_level"] = None
            payload["openai_reasoning_effort"] = None
            payload["anthropic_effort"] = None
            provider = payload["llm_provider"]
            if provider == "google":
                payload["google_thinking_level"] = raw_value
            elif provider == "openai":
                payload["openai_reasoning_effort"] = raw_value
            elif provider == "anthropic":
                payload["anthropic_effort"] = raw_value
        else:
            payload[field_name] = raw_value

        updated_request = AnalysisRequest.from_payload(payload)
        updated_session = session.with_request(updated_request)
        self.store.save_draft_session(updated_session)
        return updated_session

    def toggle_analyst(self, analyst: str) -> DraftSession:
        session = self.store.load_draft_session()
        if session is None:
            raise RuntimeError("draft session is missing")
        analysts = list(session.request.analysts)
        if analyst in analysts and len(analysts) > 1:
            analysts.remove(analyst)
        elif analyst not in analysts:
            analysts.append(analyst)
        payload = session.request.to_payload()
        payload["analysts"] = analysts
        updated_request = AnalysisRequest.from_payload(payload)
        updated_session = session.with_request(updated_request)
        self.store.save_draft_session(updated_session)
        return updated_session
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_telegram_service -v`

Expected:

```text
test_apply_provider_choice_resets_models_to_provider_defaults ... ok
test_apply_choice_updates_research_depth ... ok
test_apply_text_input_updates_ticker_and_clears_waiting_flag ... ok
test_begin_analyze_returns_switch_prompt_when_job_is_running ... ok
test_begin_analyze_uses_last_successful_when_no_draft_exists ... ok
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_telegram_service.py tradingagents/telegram_bot/service.py
git commit -m "feat: add telegram draft editing service"
```

### Task 7: Add Telegram Job Controller, Worker, And Polling Bot Handlers

**Files:**
- Create: `tradingagents/telegram_bot/runtime.py`
- Create: `tradingagents/telegram_bot/worker.py`
- Create: `tradingagents/telegram_bot/main.py`
- Test: `tests/test_telegram_runtime.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from tradingagents.app.analysis_request import build_default_request
from tradingagents.telegram_bot.runtime import TelegramJobController
from tradingagents.telegram_bot.store import TelegramStateStore


class _FakeProcess:
    def __init__(self):
        self.pid = 4321
        self.returncode = None
        self.terminated = False

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    async def wait(self):
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode


class TelegramRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_job_persists_active_job_metadata(self):
        request = build_default_request("NVDA", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            bot = AsyncMock()
            controller = TelegramJobController(store=store, bot=bot, worker_module="tests.fake_worker")
            fake_process = _FakeProcess()
            controller._spawn_process = AsyncMock(return_value=fake_process)

            await controller.start_job(chat_id=123, request=request)

            active_job = store.load_active_job()
            self.assertEqual(active_job["status"], "running")
            self.assertEqual(active_job["pid"], 4321)
            self.assertEqual(active_job["ticker"], "NVDA")

    async def test_cancel_job_terminates_running_process(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            bot = AsyncMock()
            controller = TelegramJobController(store=store, bot=bot, worker_module="tests.fake_worker")
            process = _FakeProcess()
            controller._active_process = process
            store.save_active_job({"status": "running", "pid": 4321, "ticker": "NVDA"})

            await controller.cancel_job()

            self.assertTrue(process.terminated)
            self.assertEqual(store.load_active_job()["status"], "cancelled")

    async def test_wait_for_completion_sends_report_document(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "complete_report.md"
            report_path.write_text("report")
            store = TelegramStateStore(Path(tmpdir))
            bot = AsyncMock()
            controller = TelegramJobController(store=store, bot=bot, worker_module="tests.fake_worker")
            controller._active_process = _FakeProcess()
            store.save_active_job(
                {
                    "status": "running",
                    "chat_id": 123,
                    "report_file": str(report_path),
                    "decision": "BUY",
                }
            )

            await controller.wait_for_completion()

            bot.send_message.assert_awaited()
            bot.send_document.assert_awaited()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_telegram_runtime -v`

Expected: FAIL with `ImportError: cannot import name 'TelegramJobController'`

- [ ] **Step 3: Write minimal implementation**

```python
# tradingagents/telegram_bot/runtime.py
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from tradingagents.app.analysis_request import AnalysisRequest


class TelegramJobController:
    def __init__(self, store, bot, worker_module: str = "tradingagents.telegram_bot.worker"):
        self.store = store
        self.bot = bot
        self.worker_module = worker_module
        self._active_process = None

    async def _spawn_process(self, request_path: Path, state_root: Path):
        return await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            self.worker_module,
            str(request_path),
            str(state_root),
        )

    async def start_job(self, chat_id: int, request: AnalysisRequest) -> None:
        request_path = self.store.root / "active_request.json"
        request_path.write_text(json.dumps(request.to_payload(), indent=2))
        process = await self._spawn_process(request_path, self.store.root)
        self._active_process = process
        self.store.save_active_job(
            {
                "status": "running",
                "pid": process.pid,
                "chat_id": chat_id,
                "ticker": request.ticker,
                "analysis_date": request.analysis_date,
                "research_depth": request.research_depth,
                "llm_provider": request.llm_provider,
                "quick_model": request.quick_model,
                "deep_model": request.deep_model,
                "current_stage": "Starting",
            }
        )

    async def cancel_job(self) -> None:
        if self._active_process is not None:
            self._active_process.terminate()
        active_job = self.store.load_active_job() or {}
        active_job["status"] = "cancelled"
        self.store.save_active_job(active_job)
```

```python
# tradingagents/telegram_bot/worker.py
from __future__ import annotations

import json
import sys
from pathlib import Path

from tradingagents.app.analysis_request import AnalysisRequest
from tradingagents.app.analysis_runner import run_analysis_request
from tradingagents.telegram_bot.store import TelegramStateStore


def main() -> int:
    request_path = Path(sys.argv[1])
    state_root = Path(sys.argv[2])
    store = TelegramStateStore(state_root)
    request = AnalysisRequest.from_payload(json.loads(request_path.read_text()))

    active_job = store.load_active_job() or {}

    def event_sink(event: dict) -> None:
        current = store.load_active_job() or active_job
        if event["type"] == "job_started":
            current["current_stage"] = "Running"
        elif event["type"] == "stage":
            current["current_stage"] = event["current_stage"]
        elif event["type"] == "job_finished":
            current["status"] = "completed"
            current["report_file"] = event["report_file"]
        store.save_active_job(current)

    result = run_analysis_request(request, event_sink=event_sink)
    store.save_last_successful(request)
    current = store.load_active_job() or active_job
    current["status"] = "completed"
    current["report_file"] = str(result.report_file)
    current["decision"] = result.decision
    store.save_active_job(current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# tradingagents/telegram_bot/main.py
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from tradingagents.app.options import (
    OUTPUT_LANGUAGE_CHOICES,
    PROVIDER_CHOICES,
    PROVIDER_SETTING_CHOICES,
    RESEARCH_DEPTH_CHOICES,
)
from tradingagents.llm_clients.model_catalog import get_model_options
from tradingagents.telegram_bot.keyboards import build_choice_keyboard, build_main_menu_keyboard
from tradingagents.telegram_bot.presentation import build_draft_summary, build_status_text
from tradingagents.telegram_bot.runtime import TelegramJobController
from tradingagents.telegram_bot.service import TelegramControlService
from tradingagents.telegram_bot.store import TelegramStateStore


def _ensure_allowed(update: Update) -> bool:
    allowed_chat_id = os.environ["TELEGRAM_ALLOWED_CHAT_ID"]
    return str(update.effective_chat.id) == str(allowed_chat_id)


def _build_field_choices(service: TelegramControlService, field_name: str):
    session = service.store.load_draft_session()
    request = session.request
    if field_name == "llm_provider":
        return [(label, provider) for label, provider, _ in PROVIDER_CHOICES]
    if field_name == "output_language":
        return [(language, language) for language in OUTPUT_LANGUAGE_CHOICES]
    if field_name == "research_depth":
        return [(label, str(value)) for label, value in RESEARCH_DEPTH_CHOICES]
    if field_name == "quick_model":
        return get_model_options(request.llm_provider, "quick")
    if field_name == "deep_model":
        return get_model_options(request.llm_provider, "deep")
    if field_name == "provider_setting":
        return PROVIDER_SETTING_CHOICES.get(request.llm_provider, [])
    if field_name == "analysts":
        return [(label.title(), label) for label in ("market", "social", "news", "fundamentals")]
    raise KeyError(field_name)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return
    service: TelegramControlService = context.application.bot_data["service"]
    response = service.begin_analyze(datetime.now().strftime("%Y-%m-%d"))
    if response["mode"] == "confirm_switch":
        await update.effective_chat.send_message(
            response["text"],
            reply_markup=build_choice_keyboard(
                "switch",
                [("Cancel current and switch", "yes"), ("Keep current job", "no")],
            ),
        )
        return

    session = service.store.load_draft_session()
    await update.effective_chat.send_message(
        build_draft_summary(session.request),
        reply_markup=build_main_menu_keyboard(),
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return
    store: TelegramStateStore = context.application.bot_data["state_store"]
    await update.effective_chat.send_message(build_status_text(store.load_active_job()))


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return
    controller: TelegramJobController = context.application.bot_data["job_controller"]
    await controller.cancel_job()
    await update.effective_chat.send_message("Active job cancelled.")


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return

    query = update.callback_query
    await query.answer()
    service: TelegramControlService = context.application.bot_data["service"]
    controller: TelegramJobController = context.application.bot_data["job_controller"]
    action, *rest = query.data.split(":")

    if query.data == "menu:main":
        session = service.store.load_draft_session()
        await query.edit_message_text(
            build_draft_summary(session.request),
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if action == "edit":
        field_name = rest[0]
        if field_name in {"ticker", "analysis_date"}:
            service.set_waiting_field(field_name)
            await query.edit_message_text(f"Send {field_name.replace('_', ' ')} as plain text.")
            return
        choices = _build_field_choices(service, field_name)
        await query.edit_message_text(
            f"Choose {field_name.replace('_', ' ')}:",
            reply_markup=build_choice_keyboard(f"pick:{field_name}", choices),
        )
        return

    if action == "pick":
        field_name, raw_value = rest
        if field_name == "analysts":
            session = service.toggle_analyst(raw_value)
        else:
            session = service.apply_choice(field_name, raw_value)
        await query.edit_message_text(
            build_draft_summary(session.request),
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if action == "switch" and rest[0] == "yes":
        await controller.cancel_job()
        session = service.store.load_draft_session()
        await query.edit_message_text(
            build_draft_summary(session.request),
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if action == "run" and rest[0] == "start":
        session = service.store.load_draft_session()
        await controller.start_job(update.effective_chat.id, session.request)
        context.application.create_task(controller.wait_for_completion())
        await query.edit_message_text("Analysis started.")
        return


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return
    service: TelegramControlService = context.application.bot_data["service"]
    session = service.apply_text_input(update.message.text)
    await update.effective_chat.send_message(
        build_draft_summary(session.request),
        reply_markup=build_main_menu_keyboard(),
    )


def main() -> None:
    state_root = Path(os.getenv("TRADINGAGENTS_TELEGRAM_STATE_DIR", "./results/_telegram_bot"))
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    store = TelegramStateStore(state_root)
    service = TelegramControlService(store)
    application = ApplicationBuilder().token(token).build()
    application.bot_data["state_store"] = store
    application.bot_data["service"] = service
    application.bot_data["job_controller"] = TelegramJobController(store=store, bot=application.bot)
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    application.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_telegram_runtime -v`

Expected:

```text
test_cancel_job_terminates_running_process ... ok
test_start_job_persists_active_job_metadata ... ok
test_wait_for_completion_sends_report_document ... ok
```

- [ ] **Step 5: Extend the bot to deliver completion output**

```python
# tradingagents/telegram_bot/runtime.py
    async def wait_for_completion(self) -> None:
        if self._active_process is None:
            return
        return_code = await self._active_process.wait()
        active_job = self.store.load_active_job() or {}
        if return_code == 0 and active_job.get("report_file"):
            await self.bot.send_message(
                chat_id=active_job["chat_id"],
                text=f"Analysis complete: {active_job.get('decision', '-')}",
            )
            with open(active_job["report_file"], "rb") as handle:
                await self.bot.send_document(
                    chat_id=active_job["chat_id"],
                    document=handle,
                    filename=Path(active_job["report_file"]).name,
                )
        elif return_code != 0:
            active_job["status"] = "failed"
            self.store.save_active_job(active_job)
            await self.bot.send_message(
                chat_id=active_job["chat_id"],
                text="Analysis failed. Check local artifacts for details.",
            )
        self._active_process = None
```

- [ ] **Step 6: Run the Telegram-focused regression**

Run: `uv run python -m unittest tests.test_telegram_store tests.test_telegram_presentation tests.test_telegram_service tests.test_telegram_runtime -v`

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add tests/test_telegram_runtime.py \
  tradingagents/telegram_bot/runtime.py \
  tradingagents/telegram_bot/worker.py \
  tradingagents/telegram_bot/main.py
git commit -m "feat: add telegram bot runtime"
```

### Task 8: Wire Packaging, Compose, Env, And User-Facing Docs

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `README.md`

- [ ] **Step 1: Write the failing smoke command**

Run: `docker compose config`

Expected: FAIL or omit the `telegram-bot` service because it does not exist yet

- [ ] **Step 2: Add dependency, entrypoint, env vars, and compose service**

```toml
# pyproject.toml
dependencies = [
    "tqdm>=4.67.1",
    "python-telegram-bot>=22.5",
    "typing-extensions>=4.14.0",
]

[project.scripts]
tradingagents = "cli.main:app"
tradingagents-telegram = "tradingagents.telegram_bot.main:main"
```

```dotenv
# .env.example
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_CHAT_ID=
TRADINGAGENTS_TELEGRAM_STATE_DIR=./results/_telegram_bot
```

```yaml
# docker-compose.yml
services:
  tradingagents:
    build: .
    env_file:
      - .env
    volumes:
      - ./results:/home/appuser/app/results
    tty: true
    stdin_open: true

  telegram-bot:
    build: .
    env_file:
      - .env
    volumes:
      - ./results:/home/appuser/app/results
    entrypoint: ["python", "-m", "tradingagents.telegram_bot.main"]
    restart: unless-stopped
```

```markdown
# README.md
## Telegram Control Surface

This fork can optionally expose a private Telegram control surface for remote analysis control.

Setup:

    cp .env.example .env
    # set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_CHAT_ID
    docker compose up -d telegram-bot

Supported commands:

- `/analyze`
- `/status`
- `/cancel`
```

- [ ] **Step 3: Run the packaging and config checks**

Run: `uv run python -m unittest tests.test_analysis_request tests.test_analysis_runner tests.test_cli_runner_bridge tests.test_report_save_path tests.test_telegram_store tests.test_telegram_presentation tests.test_telegram_service tests.test_telegram_runtime -v`

Expected: all tests PASS

Run: `docker compose config`

Expected: PASS and include a `telegram-bot` service with the project image, `.env`, and the shared `results` volume

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .env.example docker-compose.yml README.md
git commit -m "chore: wire telegram bot service"
```

### Task 9: Final Verification And Local Smoke

**Files:**
- Modify: none
- Test: `tests/test_analysis_request.py`
- Test: `tests/test_analysis_runner.py`
- Test: `tests/test_cli_runner_bridge.py`
- Test: `tests/test_report_save_path.py`
- Test: `tests/test_telegram_store.py`
- Test: `tests/test_telegram_presentation.py`
- Test: `tests/test_telegram_service.py`
- Test: `tests/test_telegram_runtime.py`

- [ ] **Step 1: Run the full targeted regression suite**

Run: `uv run python -m unittest tests.test_analysis_request tests.test_analysis_runner tests.test_cli_runner_bridge tests.test_report_save_path tests.test_telegram_store tests.test_telegram_presentation tests.test_telegram_service tests.test_telegram_runtime -v`

Expected: all tests PASS

- [ ] **Step 2: Run a bot import smoke**

Run: `uv run python -c "from tradingagents.telegram_bot.main import main; print('IMPORT_OK')"`

Expected:

```text
IMPORT_OK
```

- [ ] **Step 3: Run a compose config smoke**

Run: `docker compose config | rg "telegram-bot|TELEGRAM_BOT_TOKEN|TRADINGAGENTS_TELEGRAM_STATE_DIR"`

Expected: lines for the new `telegram-bot` service and Telegram environment variables

- [ ] **Step 4: Commit the final verification checkpoint**

```bash
git commit --allow-empty -m "test: verify telegram control surface"
```
