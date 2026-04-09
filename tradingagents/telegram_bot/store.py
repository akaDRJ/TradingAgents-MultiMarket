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
        self._path("last_successful").write_text(
            json.dumps(request.to_payload(), indent=2)
        )

    def load_draft_session(self) -> DraftSession | None:
        path = self._path("draft_session")
        if not path.exists():
            return None
        return DraftSession.from_payload(json.loads(path.read_text()))

    def save_draft_session(self, session: DraftSession) -> None:
        self._path("draft_session").write_text(
            json.dumps(session.to_payload(), indent=2)
        )

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
