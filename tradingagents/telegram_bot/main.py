from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from telegram import BotCommand, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from tradingagents.app.options import (
    OUTPUT_LANGUAGE_CHOICES,
    PROVIDER_CHOICES,
    PROVIDER_SETTING_CHOICES,
    RESEARCH_DEPTH_CHOICES,
)
from tradingagents.llm_clients.model_catalog import get_model_options
from tradingagents.telegram_bot.keyboards import build_choice_keyboard, build_main_menu_keyboard
from tradingagents.telegram_bot.presentation import build_draft_summary, build_status_text
from tradingagents.telegram_bot.runtime import TelegramJobController
from tradingagents.telegram_bot.service import TelegramControlService
from tradingagents.telegram_bot.store import TelegramStateStore


def _ensure_allowed(update: Update) -> bool:
    allowed_chat_id = os.environ["TELEGRAM_ALLOWED_CHAT_ID"]
    return str(update.effective_chat.id) == str(allowed_chat_id)


async def register_bot_commands(bot) -> None:
    await bot.set_my_commands(
        commands=[
            BotCommand("analyze", "Configure and start an analysis"),
            BotCommand("status", "Show the active analysis status"),
            BotCommand("cancel", "Cancel the active analysis"),
        ]
    )


def _build_analyst_choices(selected: tuple[str, ...]):
    options = []
    for analyst in ("market", "social", "news", "fundamentals"):
        label = f"{'✓ ' if analyst in selected else ''}{analyst.title()}"
        options.append((label, analyst))
    return options


def _build_field_choices(service: TelegramControlService, field_name: str):
    session = service.store.load_draft_session()
    request = session.request
    if field_name == "llm_provider":
        return [(label, provider) for label, provider, _ in PROVIDER_CHOICES]
    if field_name == "output_language":
        return [(language, language) for language in OUTPUT_LANGUAGE_CHOICES]
    if field_name == "research_depth":
        return [(label, str(value)) for label, value in RESEARCH_DEPTH_CHOICES]
    if field_name == "quick_model":
        return get_model_options(request.llm_provider, "quick")
    if field_name == "deep_model":
        return get_model_options(request.llm_provider, "deep")
    if field_name == "provider_setting":
        return PROVIDER_SETTING_CHOICES.get(request.llm_provider, [])
    if field_name == "analysts":
        return _build_analyst_choices(request.analysts)
    raise KeyError(field_name)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return
    service: TelegramControlService = context.application.bot_data["service"]
    response = service.begin_analyze(datetime.now().strftime("%Y-%m-%d"))
    if response["mode"] == "confirm_switch":
        await update.effective_chat.send_message(
            response["text"],
            reply_markup=build_choice_keyboard(
                "switch",
                [("Cancel current and switch", "yes"), ("Keep current job", "no")],
            ),
        )
        return

    session = service.store.load_draft_session()
    await update.effective_chat.send_message(
        build_draft_summary(session.request),
        reply_markup=build_main_menu_keyboard(),
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return
    store: TelegramStateStore = context.application.bot_data["state_store"]
    await update.effective_chat.send_message(build_status_text(store.load_active_job()))


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return
    controller: TelegramJobController = context.application.bot_data["job_controller"]
    await controller.cancel_job()
    await update.effective_chat.send_message("Active job cancelled.")


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return

    query = update.callback_query
    await query.answer()
    service: TelegramControlService = context.application.bot_data["service"]
    controller: TelegramJobController = context.application.bot_data["job_controller"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    action, *rest = query.data.split(":")

    if query.data == "menu:main":
        session = service.store.load_draft_session()
        await query.edit_message_text(
            build_draft_summary(session.request),
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if query.data == "draft:restore":
        session = service.restore_last_successful(today_str)
        await query.edit_message_text(
            build_draft_summary(session.request),
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if query.data == "draft:reset":
        session = service.reset_to_defaults(today_str)
        await query.edit_message_text(
            build_draft_summary(session.request),
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if action == "edit":
        field_name = rest[0]
        if field_name in {"ticker", "analysis_date"}:
            service.set_waiting_field(field_name)
            await query.edit_message_text(
                f"Send {field_name.replace('_', ' ')} as plain text."
            )
            return
        choices = _build_field_choices(service, field_name)
        await query.edit_message_text(
            f"Choose {field_name.replace('_', ' ')}:",
            reply_markup=build_choice_keyboard(f"pick:{field_name}", choices),
        )
        return

    if action == "pick":
        field_name, raw_value = rest
        if field_name == "analysts":
            session = service.toggle_analyst(raw_value)
        else:
            session = service.apply_choice(field_name, raw_value)
        await query.edit_message_text(
            build_draft_summary(session.request),
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if action == "switch":
        if rest[0] == "yes":
            await controller.cancel_job()
            session = service.restore_last_successful(today_str)
            await query.edit_message_text(
                build_draft_summary(session.request),
                reply_markup=build_main_menu_keyboard(),
            )
        else:
            await query.edit_message_text("Keeping current job.")
        return

    if action == "run" and rest[0] == "start":
        session = service.store.load_draft_session()
        await controller.start_job(update.effective_chat.id, session.request)
        context.application.create_task(controller.wait_for_completion())
        await query.edit_message_text("Analysis started.")
        return


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _ensure_allowed(update):
        return
    service: TelegramControlService = context.application.bot_data["service"]
    session = service.store.load_draft_session()
    if session is None or session.awaiting_field is None:
        return
    updated = service.apply_text_input(update.message.text)
    await update.effective_chat.send_message(
        build_draft_summary(updated.request),
        reply_markup=build_main_menu_keyboard(),
    )


def main() -> None:
    state_root = Path(
        os.getenv("TRADINGAGENTS_TELEGRAM_STATE_DIR", "./results/_telegram_bot")
    )
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    store = TelegramStateStore(state_root)
    service = TelegramControlService(store)
    application = (
        ApplicationBuilder()
        .token(token)
        .post_init(lambda app: register_bot_commands(app.bot))
        .build()
    )
    application.bot_data["state_store"] = store
    application.bot_data["service"] = service
    application.bot_data["job_controller"] = TelegramJobController(
        store=store,
        bot=application.bot,
    )
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    application.run_polling()


if __name__ == "__main__":
    main()
