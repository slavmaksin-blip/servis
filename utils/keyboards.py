"""
Inline and reply keyboards for the bot.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📱 SMS модуль"),
        KeyboardButton(text="📧 Магазин почты"),
    )
    builder.row(
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="ℹ️ Помощь"),
    )
    return builder.as_markup(resize_keyboard=True)


# ---------------------------------------------------------------------------
# SMS module
# ---------------------------------------------------------------------------

def sms_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="sms_cancel")
    return builder.as_markup()


def sms_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="sms_send_confirm")
    builder.button(text="❌ Отмена", callback_data="sms_cancel")
    builder.adjust(2)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Shop keyboards
# ---------------------------------------------------------------------------

def shop_domains_keyboard(domains: dict) -> InlineKeyboardMarkup:
    """Build an inline keyboard from available email domains."""
    builder = InlineKeyboardBuilder()
    for domain, info in domains.items():
        count = info.get("count", 0)
        price = info.get("price", 0)
        if count > 0:
            builder.button(
                text=f"@{domain} — {count} шт. / ${price:.4f}",
                callback_data=f"shop_domain:{domain}",
            )
    builder.button(text="❌ Отмена", callback_data="shop_cancel")
    builder.adjust(1)
    return builder.as_markup()


def shop_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="shop_cancel")
    return builder.as_markup()


def shop_action_keyboard(activation_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔄 Проверить письмо",
        callback_data=f"shop_check:{activation_id}",
    )
    builder.button(
        text="🔁 Повторный заказ",
        callback_data=f"shop_reorder:{activation_id}",
    )
    builder.button(
        text="❌ Отменить почту",
        callback_data=f"shop_cancel_order:{activation_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Пополнить баланс", callback_data="profile_topup")
    builder.button(text="📊 История операций", callback_data="profile_history")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="💸 Пополнить баланс", callback_data="admin_topup")
    builder.button(text="📣 Рассылка", callback_data="admin_broadcast")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.adjust(2)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

remove_keyboard = ReplyKeyboardRemove()
