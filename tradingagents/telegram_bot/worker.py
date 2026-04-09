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

    try:
        result = run_analysis_request(request, event_sink=event_sink)
    except Exception as exc:
        current = store.load_active_job() or active_job
        current["status"] = "failed"
        current["error"] = str(exc)
        store.save_active_job(current)
        return 1

    store.save_last_successful(request)
    current = store.load_active_job() or active_job
    current["status"] = "completed"
    current["report_file"] = str(result.report_file)
    current["decision"] = result.decision
    current["current_stage"] = "Completed"
    store.save_active_job(current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
