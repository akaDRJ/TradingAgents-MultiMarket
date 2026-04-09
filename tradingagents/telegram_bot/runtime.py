from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from tradingagents.app.analysis_request import AnalysisRequest


class TelegramJobController:
    def __init__(
        self,
        store,
        bot,
        worker_module: str = "tradingagents.telegram_bot.worker",
    ):
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
        elif active_job.get("status") != "cancelled":
            active_job["status"] = "failed"
            self.store.save_active_job(active_job)
            if active_job.get("chat_id"):
                await self.bot.send_message(
                    chat_id=active_job["chat_id"],
                    text="Analysis failed. Check local artifacts for details.",
                )
        self._active_process = None
