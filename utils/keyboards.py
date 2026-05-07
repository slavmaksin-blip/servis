from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📧 Отправить письмо", "send_email")],
        ]
    )


def send_email_choice_kb() -> InlineKeyboardMarkup:
    """Choose between a custom (uploaded) template or a preset template."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn("📎 Свой шаблон", "custom_email"),
                _btn("📋 Общий шаблон", "preset_email"),
            ],
            [_btn("❌ Отмена", "cancel")],
        ]
    )


def preset_template_kb() -> InlineKeyboardMarkup:
    """Choose which preset template to use."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn("🧾 Ricardo 2.0", "preset_ricardo"),
                _btn("🧾 PostFinance 2.0", "preset_postfinance"),
            ],
            [_btn("❌ Отмена", "cancel")],
        ]
    )


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("❌ Отмена", "cancel")],
        ]
    )
