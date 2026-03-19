from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛠 Модули", callback_data="modules")],
            [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        ]
    )


def modules_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 SMS рассылка", callback_data="module_sms")],
            [InlineKeyboardButton(text="📧 Временная почта", callback_data="module_mail")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
        ]
    )


def back_keyboard(callback: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=callback)],
        ]
    )


def confirm_keyboard(yes_callback: str, no_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=yes_callback),
                InlineKeyboardButton(text="❌ Нет", callback_data=no_callback),
            ]
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="admin_balance")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        ]
    )
