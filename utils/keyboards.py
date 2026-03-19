from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔧 Модули", callback_data="modules"),
            InlineKeyboardButton(text="🛒 Магазин", callback_data="shop"),
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        ],
    ])


def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")],
    ])


def subscription_kb(channel_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 Перейти в канал",
            url=f"https://t.me/{channel_username}",
        )],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")],
    ])


def modules_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 SMS", callback_data="module_sms")],
        [InlineKeyboardButton(text="📧 Mailer", callback_data="module_mailer")],
        [InlineKeyboardButton(text="🖥 Screen", callback_data="module_screen")],
        [InlineKeyboardButton(text="🔗 Proxy", callback_data="module_proxy")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def sms_countries_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Швейцария", callback_data="sms_country_ch")],
        [InlineKeyboardButton(text="❌ Германия (временно недоступна)", callback_data="sms_country_disabled")],
        [InlineKeyboardButton(text="❌ Австрия (временно недоступна)", callback_data="sms_country_disabled")],
        [InlineKeyboardButton(text="❌ США (временно недоступна)", callback_data="sms_country_disabled")],
        [InlineKeyboardButton(text="❌ Франция (временно недоступна)", callback_data="sms_country_disabled")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def shop_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📧 Купить почту", callback_data="shop_mail")],
        [InlineKeyboardButton(text="🛍 Товары", callback_data="shop_products")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Связаться с поддержкой", url="https://t.me/mensorsim")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="topup")],
        [InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy_sub")],
        [InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def payment_system_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 CryptoBot", callback_data="pay_cryptobot")],
        [InlineKeyboardButton(text="🚀 xRocket", callback_data="pay_xrocket")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def check_payment_kb(invoice_id: str, payment_system: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Проверить оплату",
            callback_data=f"check_pay:{payment_system}:{invoice_id}",
        )],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def subscription_plans_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 день — 6$", callback_data="sub_1")],
        [InlineKeyboardButton(text="3 дня — 12$", callback_data="sub_3")],
        [InlineKeyboardButton(text="15 дней — 28$", callback_data="sub_15")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def mail_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"mail_check:{order_id}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def mail_received_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Пересоздать", callback_data=f"mail_recreate:{order_id}")],
        [InlineKeyboardButton(text="📨 Получить сообщение", callback_data=f"mail_getmsg:{order_id}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Забанить", callback_data="admin_ban"),
         InlineKeyboardButton(text="✅ Разбанить", callback_data="admin_unban")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📦 Товары", callback_data="admin_products")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="admin_balance")],
        [InlineKeyboardButton(text="👥 Балансы", callback_data="admin_balances")],
        [InlineKeyboardButton(text="🎁 Промокоды", callback_data="admin_promos")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def admin_products_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_add_category")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="📤 Загрузить файлы (сток)", callback_data="admin_upload_stock")],
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data="admin_delete_product")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin")],
    ])


def admin_balance_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Выдать баланс", callback_data="admin_give_balance")],
        [InlineKeyboardButton(text="➖ Списать баланс", callback_data="admin_take_balance")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin")],
    ])
