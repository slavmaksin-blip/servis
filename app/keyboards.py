from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Screen", callback_data="menu:screen")],
        ]
    )


def countries_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇨🇭 Schweiz", callback_data="screen:country:ch")],
            [InlineKeyboardButton(text="◀️ Zurück", callback_data="menu:back")],
        ]
    )


def platforms_kb(country_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Bank-Screenshot", callback_data=f"screen:platform:{country_code}:bank")],
            [InlineKeyboardButton(text="📄 PDF Kontoauszug", callback_data=f"pdf:start:{country_code}")],
            [InlineKeyboardButton(text="◀️ Zurück", callback_data="screen:back:countries")],
        ]
    )
