from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database
from utils.keyboards import back_keyboard

router = Router()

PRODUCTS: list[dict] = [
    {"id": "sms_pack", "name": "📦 SMS пакет (100 сообщений)", "price": 99.0},
    {"id": "mail_pack", "name": "📬 Почта Pro (30 дней)", "price": 49.0},
]


def shop_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"{p['name']} — {p['price']}₽", callback_data=f"buy_{p['id']}")]
        for p in PRODUCTS
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "shop")
async def show_shop(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🛒 <b>Магазин</b>\n\nВыберите товар:",
        reply_markup=shop_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: CallbackQuery) -> None:
    product_id = callback.data.removeprefix("buy_")
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    balance = await database.get_balance(callback.from_user.id)
    if balance < product["price"]:
        await callback.answer(
            f"❌ Недостаточно средств. Ваш баланс: {balance:.2f}₽",
            show_alert=True,
        )
        return

    await database.update_balance(callback.from_user.id, -product["price"])
    await database.create_order(callback.from_user.id, product["name"], product["price"])
    await callback.message.edit_text(
        f"✅ Вы успешно приобрели:\n<b>{product['name']}</b>\n\n"
        f"Списано: {product['price']}₽\n"
        f"Остаток: {balance - product['price']:.2f}₽",
        reply_markup=back_keyboard("shop"),
        parse_mode="HTML",
    )
    await callback.answer()
