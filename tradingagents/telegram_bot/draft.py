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
