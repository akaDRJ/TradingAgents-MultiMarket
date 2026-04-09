from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_choice_keyboard(prefix: str, choices) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"{prefix}:{value}")]
        for label, value in choices
    ]
    rows.append([InlineKeyboardButton("Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Edit Ticker", callback_data="edit:ticker"),
                InlineKeyboardButton("Edit Date", callback_data="edit:analysis_date"),
            ],
            [
                InlineKeyboardButton("Edit Language", callback_data="edit:output_language"),
                InlineKeyboardButton("Edit Analysts", callback_data="edit:analysts"),
            ],
            [
                InlineKeyboardButton("Edit Depth", callback_data="edit:research_depth"),
                InlineKeyboardButton("Edit Provider", callback_data="edit:llm_provider"),
            ],
            [
                InlineKeyboardButton("Edit Quick Model", callback_data="edit:quick_model"),
                InlineKeyboardButton("Edit Deep Model", callback_data="edit:deep_model"),
            ],
            [
                InlineKeyboardButton("Edit Provider Setting", callback_data="edit:provider_setting"),
            ],
            [
                InlineKeyboardButton("Start Analysis", callback_data="run:start"),
            ],
            [
                InlineKeyboardButton("Restore Last Successful", callback_data="draft:restore"),
                InlineKeyboardButton("Reset To Defaults", callback_data="draft:reset"),
            ],
        ]
    )
