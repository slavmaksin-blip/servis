from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _url_btn(text: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, url=url)


# ── Main menu ──────────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("🔧 Модули", "modules"), _btn("🛒 Магазин", "shop")],
            [_btn("❓ Помощь", "help"), _btn("👤 Профиль", "profile")],
        ]
    )


# ── Subscription check ─────────────────────────────────────────────────────────

def check_subscription_kb(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_url_btn("📢 Перейти в канал", channel_url)],
            [_btn("✅ Проверить подписку", "check_subscription")],
        ]
    )


# ── Modules ────────────────────────────────────────────────────────────────────

def modules_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📱 SMS-модуль", "sms_module")],
            [_btn("📧 Mailer", "mailer_module"), _btn("🖥 Screen", "screen_module")],
            [_btn("🔒 Proxy", "proxy_module")],
            [_btn("◀️ Назад", "main_menu")],
        ]
    )


# ── SMS countries ──────────────────────────────────────────────────────────────

def sms_country_kb() -> InlineKeyboardMarkup:
    from config import SMS_COUNTRIES

    rows = []
    for country_name in SMS_COUNTRIES:
        rows.append([_btn(country_name, f"sms_country:{country_name}")])
    rows.append([_btn("◀️ Назад", "modules")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Shop ───────────────────────────────────────────────────────────────────────

def shop_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📧 Магазин почты", "shop_email")],
            [_btn("📦 Товары", "shop_products")],
            [_btn("◀️ Назад", "main_menu")],
        ]
    )


# ── Categories ─────────────────────────────────────────────────────────────────

def categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    rows = [[_btn(c["name"], f"category:{c['id']}")] for c in categories]
    rows.append([_btn("◀️ Назад", "shop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Products ───────────────────────────────────────────────────────────────────

def products_kb(products: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [_btn(f"{p['name']} — ${p['price']:.2f}", f"product:{p['id']}")]
        for p in products
    ]
    rows.append([_btn("◀️ Назад", "shop_products")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Quantity ───────────────────────────────────────────────────────────────────

def quantity_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("1", "qty:1"), _btn("2", "qty:2"), _btn("3", "qty:3")],
            [_btn("5", "qty:5"), _btn("10", "qty:10"), _btn("20", "qty:20")],
            [_btn("◀️ Назад", "shop_products")],
        ]
    )


# ── Profile ────────────────────────────────────────────────────────────────────

def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("💰 Пополнить баланс", "topup_balance")],
            [_btn("⭐ Купить подписку", "buy_subscription")],
            [_btn("🎁 Промокод", "promo_code")],
            [_btn("◀️ Назад", "main_menu")],
        ]
    )


# ── Payment ────────────────────────────────────────────────────────────────────

def payment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("🤖 CryptoBot", "pay_cryptobot")],
            [_btn("🚀 xRocket", "pay_xrocket")],
            [_btn("◀️ Назад", "profile")],
        ]
    )


# ── Subscription ───────────────────────────────────────────────────────────────

def subscription_kb(prices: dict) -> InlineKeyboardMarkup:
    rows = []
    labels = {1: "1 день", 3: "3 дня", 15: "15 дней"}
    for days, price in prices.items():
        label = labels.get(days, f"{days} дн.")
        rows.append([_btn(f"{label} — ${price:.2f}", f"sub:{days}")])
    rows.append([_btn("◀️ Назад", "profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Admin ──────────────────────────────────────────────────────────────────────

def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("🔨 Забанить", "admin_ban"), _btn("🔓 Разбанить", "admin_unban")],
            [_btn("📢 Рассылка", "admin_broadcast")],
            [_btn("📁 Категория", "admin_add_category"), _btn("📦 Товар", "admin_add_product")],
            [_btn("💰 Выдать баланс", "admin_give_balance"), _btn("💸 Списать", "admin_take_balance")],
            [_btn("👥 Пользователи", "admin_list_users"), _btn("📊 Статистика", "admin_stats")],
            [_btn("🎁 Промокод", "admin_create_promo"), _btn("📋 Промокоды", "admin_list_promos")],
        ]
    )


# ── Utility keyboards ──────────────────────────────────────────────────────────

def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("❌ Отмена", "cancel")]]
    )


def back_kb(target: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("◀️ Назад", target)]]
    )
