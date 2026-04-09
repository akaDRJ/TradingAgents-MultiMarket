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
