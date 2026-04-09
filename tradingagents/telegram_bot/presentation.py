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
            "Provider Setting: "
            f"{request.google_thinking_level or request.openai_reasoning_effort or request.anthropic_effort or '-'}",
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
