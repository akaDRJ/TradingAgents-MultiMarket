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
