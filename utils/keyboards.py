from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def cancel_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="❌ Отмена"))
    return kb.as_markup(resize_keyboard=True)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔧 Модули", callback_data="menu:modules"),
        InlineKeyboardButton(text="🛒 Магазин", callback_data="menu:shop"),
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="menu:help"),
        InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
    )
    return builder.as_markup()


def subscription_keyboard(channel_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    channel_url = (
        f"https://t.me/{channel_id.lstrip('@')}"
        if channel_id.startswith("@")
        else f"https://t.me/c/{channel_id.lstrip('-100')}"
    )
    builder.row(
        InlineKeyboardButton(text="📢 Перейти в канал", url=channel_url)
    )
    builder.row(
        InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")
    )
    return builder.as_markup()


def modules_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📧 Mailer", callback_data="module:mailer"),
        InlineKeyboardButton(text="📸 Screen", callback_data="module:screen"),
    )
    builder.row(
        InlineKeyboardButton(text="🌐 Proxy", callback_data="module:proxy"),
        InlineKeyboardButton(text="📱 SMS", callback_data="module:sms"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    )
    return builder.as_markup()


def sms_countries_keyboard(countries: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in countries:
        builder.add(
            InlineKeyboardButton(
                text=c["name"], callback_data=f"sms_country:{c['code']}"
            )
        )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="menu:back"))
    return builder.as_markup()


def shop_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📬 Купить почту", callback_data="shop:email"),
        InlineKeyboardButton(text="📦 Товары", callback_data="shop:products"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    )
    return builder.as_markup()


def email_domains_keyboard(domains: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in domains:
        price_display = f"${d['price'] * 3:.2f}"
        builder.add(
            InlineKeyboardButton(
                text=f"{d['domain']} — {price_display}",
                callback_data=f"email_domain:{d['domain']}",
            )
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="shop:email_cancel"))
    return builder.as_markup()


def email_actions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="email:refresh"),
        InlineKeyboardButton(text="♻️ Пересоздать", callback_data="email:recreate"),
    )
    builder.row(
        InlineKeyboardButton(text="📨 Получить сообщение", callback_data="email:get_message")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="shop:email")
    )
    return builder.as_markup()


def categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.add(
            InlineKeyboardButton(
                text=cat["name"], callback_data=f"cat:{cat['id']}"
            )
        )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="shop:products_cancel"))
    return builder.as_markup()


def products_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.add(
            InlineKeyboardButton(
                text=f"{p['name']} — ${p['price']:.2f}",
                callback_data=f"prod:{p['id']}",
            )
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="shop:products"))
    return builder.as_markup()


def product_confirm_keyboard(product_id: int, quantity: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить", callback_data=f"buy_confirm:{product_id}:{quantity}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="shop:products")
    )
    return builder.as_markup()


def profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="profile:topup")
    )
    builder.row(
        InlineKeyboardButton(text="⏳ Купить подписку", callback_data="profile:sub")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Промокод", callback_data="profile:promo")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    )
    return builder.as_markup()


def topup_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🤖 CryptoBot", callback_data="topup:cryptobot"),
        InlineKeyboardButton(text="🚀 xRocket", callback_data="topup:xrocket"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="profile:cancel")
    )
    return builder.as_markup()


def sub_plans_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 день — $1.00", callback_data="sub:1"),
        InlineKeyboardButton(text="3 дня — $2.50", callback_data="sub:3"),
        InlineKeyboardButton(text="15 дней — $10.00", callback_data="sub:15"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="profile:cancel")
    )
    return builder.as_markup()


SUB_PRICES = {1: 1.00, 3: 2.50, 15: 10.00}


def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚫 Забанить", callback_data="admin:ban"),
        InlineKeyboardButton(text="✅ Разбанить", callback_data="admin:unban"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast"),
    )
    builder.row(
        InlineKeyboardButton(text="📁 Категории", callback_data="admin:categories"),
        InlineKeyboardButton(text="📦 Товары", callback_data="admin:products"),
    )
    builder.row(
        InlineKeyboardButton(text="💸 Выдать баланс", callback_data="admin:give_balance"),
        InlineKeyboardButton(text="💰 Списать баланс", callback_data="admin:take_balance"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Балансы", callback_data="admin:balances"),
        InlineKeyboardButton(text="🎁 Промокод", callback_data="admin:promo"),
    )
    return builder.as_markup()


def admin_categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.add(
            InlineKeyboardButton(
                text=f"🗑 {cat['name']}", callback_data=f"admin_del_cat:{cat['id']}"
            )
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin:add_category")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")
    )
    return builder.as_markup()


def admin_products_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.add(
            InlineKeyboardButton(
                text=f"🗑 {p['name']}", callback_data=f"admin_del_prod:{p['id']}"
            )
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin:add_product")
    )
    builder.row(
        InlineKeyboardButton(text="📎 Загрузить файл", callback_data="admin:upload_file")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")
    )
    return builder.as_markup()
