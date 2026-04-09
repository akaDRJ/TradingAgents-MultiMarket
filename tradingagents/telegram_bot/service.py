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

    def restore_last_successful(self, today_str: str) -> DraftSession:
        request = self.store.load_last_successful() or self._default_request(today_str)
        session = DraftSession(request=request)
        self.store.save_draft_session(session)
        return session

    def reset_to_defaults(self, today_str: str) -> DraftSession:
        session = DraftSession(request=self._default_request(today_str))
        self.store.save_draft_session(session)
        return session

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
