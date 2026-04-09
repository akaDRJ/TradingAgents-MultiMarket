import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from tradingagents.app.analysis_request import build_default_request
from tradingagents.telegram_bot.main import register_bot_commands
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
    async def test_register_bot_commands_sets_slash_menu_entries(self):
        bot = AsyncMock()

        await register_bot_commands(bot)

        bot.set_my_commands.assert_awaited_once()
        commands = bot.set_my_commands.await_args.kwargs["commands"]
        self.assertEqual(
            [(command.command, command.description) for command in commands],
            [
                ("analyze", "Configure and start an analysis"),
                ("status", "Show the active analysis status"),
                ("cancel", "Cancel the active analysis"),
            ],
        )

    async def test_start_job_persists_active_job_metadata(self):
        request = build_default_request("NVDA", "2026-04-09")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelegramStateStore(Path(tmpdir))
            bot = AsyncMock()
            controller = TelegramJobController(
                store=store, bot=bot, worker_module="tests.fake_worker"
            )
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
            controller = TelegramJobController(
                store=store, bot=bot, worker_module="tests.fake_worker"
            )
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
            controller = TelegramJobController(
                store=store, bot=bot, worker_module="tests.fake_worker"
            )
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
