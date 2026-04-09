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


def _infer_stage(chunk: dict) -> str:
    if chunk.get("final_trade_decision"):
        return "Portfolio Management"
    if chunk.get("trader_investment_plan"):
        return "Trading Team"
    if chunk.get("investment_debate_state", {}).get("judge_decision"):
        return "Research Team"
    if chunk.get("market_report") or chunk.get("sentiment_report") or chunk.get("news_report") or chunk.get("fundamentals_report"):
        return "Analyst Team"
    return "Running"


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
        event_sink(
            {
                "type": "job_started",
                "ticker": request.ticker,
                "analysis_date": request.analysis_date,
            }
        )

    final_state = None
    for chunk in graph.graph.stream(init_state, **args):
        final_state = chunk
        if event_sink:
            event_sink({"type": "stage", "current_stage": _infer_stage(chunk)})

    if final_state is None:
        raise RuntimeError("analysis runner received no graph output")

    decision = graph.process_signal(final_state["final_trade_decision"])
    report_dir = build_default_report_save_path(config, request.ticker, request.analysis_date)
    report_file = save_report_to_disk(
        final_state,
        request.ticker,
        report_dir,
        include_subdirectories=False,
    )

    if event_sink:
        event_sink(
            {
                "type": "job_finished",
                "decision": decision,
                "report_file": str(report_file),
            }
        )

    return AnalysisRunResult(
        final_state=final_state,
        decision=decision,
        result_dir=report_dir.parent,
        report_file=report_file,
        stats=stats_handler.get_stats(),
    )
