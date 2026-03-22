from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Скрин", callback_data="menu:screen")],
        ]
    )


def countries_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇨🇭 Швейцария", callback_data="screen:country:ch")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back")],
        ]
    )


def platforms_kb(country_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Скриншот банка", callback_data=f"screen:platform:{country_code}:bank")],
            [InlineKeyboardButton(text="📄 PDF выписка", callback_data=f"pdf:start:{country_code}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="screen:back:countries")],
        ]
    )
