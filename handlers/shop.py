import logging

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID, MAILBUY_MARKUP
from utils.api import MailBuyAPI
from utils.keyboards import (
    shop_kb,
    cancel_kb,
    back_kb,
    categories_kb,
    products_kb,
    quantity_kb,
)
from utils.states import MailModule, ProductModule

router = Router()
logger = logging.getLogger(__name__)


# ── Email shop ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "shop_email")
async def cb_shop_email(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "📧 <b>Магазин почты</b>\n\nВведите домен (например: gmail.com):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(MailModule.enter_domain)


@router.message(MailModule.enter_domain)
async def msg_mail_domain(message: types.Message, state: FSMContext) -> None:
    domain = message.text.strip().lower()
    if "." not in domain or len(domain) < 4:
        await message.answer("❌ Некорректный домен. Попробуйте снова:", reply_markup=cancel_kb())
        return

    await state.update_data(domain=domain)
    status_msg = await message.answer("⏳ Ищем доступные ящики…")

    try:
        result = await MailBuyAPI.order_email(domain)

        if not result or "email" not in result:
            await status_msg.edit_text(
                "❌ Нет доступных ящиков для этого домена.",
                reply_markup=back_kb("shop"),
            )
            await state.clear()
            return

        raw_price = float(result.get("price", 1.0))
        if raw_price <= 0:
            raw_price = 1.0
        price = round(raw_price * MAILBUY_MARKUP, 2)

        await state.update_data(
            domain=domain,
            email=result["email"],
            password=result.get("password", ""),
            order_id=result.get("order_id", ""),
            price=price,
        )

        await status_msg.edit_text(
            f"📧 Найден ящик:\n"
            f"<code>{result['email']}</code>\n\n"
            f"💵 Цена: <b>${price:.2f}</b>\n\n"
            f"Подтвердить покупку?",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="✅ Купить", callback_data="mail_confirm"
                        ),
                        types.InlineKeyboardButton(
                            text="❌ Отмена", callback_data="cancel"
                        ),
                    ]
                ]
            ),
        )
        await state.set_state(MailModule.confirm)
    except Exception as exc:
        logger.error("MailBuy order error: %s", exc)
        await status_msg.edit_text(
            f"❌ Ошибка: {exc}",
            reply_markup=back_kb("shop"),
        )
        await state.clear()


@router.callback_query(MailModule.confirm, F.data == "mail_confirm")
async def cb_mail_confirm(
    callback: types.CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)

    if not user:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        await state.clear()
        return

    price = data["price"]
    if user["balance"] < price:
        await callback.answer(
            f"❌ Недостаточно средств! Нужно: ${price:.2f}, у вас: ${user['balance']:.2f}",
            show_alert=True,
        )
        await state.clear()
        return

    await db.update_balance(callback.from_user.id, -price)
    await db.add_transaction(callback.from_user.id, -price, "email_purchase", data["email"])
    order_id = await db.add_email_order(
        callback.from_user.id,
        data["domain"],
        data["email"],
        data["password"],
        data["order_id"],
    )
    await state.update_data(order_db_id=order_id)
    await state.set_state(MailModule.view_inbox)

    await callback.message.edit_text(
        f"✅ <b>Покупка успешна!</b>\n\n"
        f"📧 Email: <code>{data['email']}</code>\n"
        f"🔑 Пароль: <code>{data['password']}</code>\n"
        f"💵 Списано: ${price:.2f}",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🔄 Обновить письма",
                        callback_data=f"mail_refresh:{order_id}",
                    )
                ],
                [types.InlineKeyboardButton(text="◀️ Магазин", callback_data="shop")],
            ]
        ),
    )


@router.callback_query(F.data.startswith("mail_refresh:"))
async def cb_mail_refresh(callback: types.CallbackQuery, state: FSMContext) -> None:
    order_db_id = int(callback.data.split(":")[1])
    order = await db.get_email_order(order_db_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    try:
        messages = await MailBuyAPI.get_message(order["order_id"])
        if not messages:
            await callback.answer("📭 Писем нет.", show_alert=True)
            return

        text = "📬 <b>Входящие письма:</b>\n\n"
        for msg in messages[:5]:
            text += (
                f"👤 От: {msg.get('from', '?')}\n"
                f"📌 Тема: {msg.get('subject', '?')}\n"
                f"📄 Текст: {msg.get('body', '')[:200]}\n\n"
            )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="🔄 Обновить",
                            callback_data=f"mail_refresh:{order_db_id}",
                        )
                    ],
                    [
                        types.InlineKeyboardButton(
                            text="◀️ Магазин", callback_data="shop"
                        )
                    ],
                ]
            ),
        )
    except Exception as exc:
        await callback.answer(f"Ошибка: {exc}", show_alert=True)


# ── Products shop ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "shop_products")
async def cb_shop_products(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    cats = await db.get_categories()
    if not cats:
        await callback.message.edit_text(
            "🛒 Категорий пока нет.",
            reply_markup=back_kb("shop"),
        )
        return

    await callback.message.edit_text(
        "🛒 <b>Товары</b>\n\nВыберите категорию:",
        parse_mode="HTML",
        reply_markup=categories_kb(cats),
    )
    await state.set_state(ProductModule.choose_category)


@router.callback_query(ProductModule.choose_category, F.data.startswith("category:"))
async def cb_choose_category(callback: types.CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    products = await db.get_products_by_category(category_id)
    if not products:
        await callback.message.edit_text(
            "📦 Товаров в этой категории нет.",
            reply_markup=back_kb("shop_products"),
        )
        return

    await state.update_data(category_id=category_id)
    await callback.message.edit_text(
        "📦 <b>Товары</b>\n\nВыберите товар:",
        parse_mode="HTML",
        reply_markup=products_kb(products),
    )
    await state.set_state(ProductModule.choose_product)


@router.callback_query(ProductModule.choose_product, F.data.startswith("product:"))
async def cb_choose_product(callback: types.CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    await state.update_data(product_id=product_id, product=product)
    await callback.message.edit_text(
        f"📦 <b>{product['name']}</b>\n"
        f"{product.get('description', '')}\n\n"
        f"💵 Цена: ${product['price']:.2f} за 1 шт.\n\n"
        f"Выберите количество:",
        parse_mode="HTML",
        reply_markup=quantity_kb(),
    )
    await state.set_state(ProductModule.choose_quantity)


@router.callback_query(ProductModule.choose_quantity, F.data.startswith("qty:"))
async def cb_choose_quantity(
    callback: types.CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    qty = int(callback.data.split(":")[1])
    data = await state.get_data()
    product = data["product"]
    total = round(product["price"] * qty, 2)

    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка пользователя.", show_alert=True)
        await state.clear()
        return

    if user["balance"] < total:
        await callback.answer(
            f"❌ Недостаточно средств! Нужно: ${total:.2f}, у вас: ${user['balance']:.2f}",
            show_alert=True,
        )
        return

    await db.update_balance(callback.from_user.id, -total)
    await db.add_transaction(
        callback.from_user.id, -total, "product_purchase", product["name"]
    )
    await db.add_product_purchase(
        callback.from_user.id, product["id"], qty, total
    )
    await state.clear()

    await callback.message.edit_text(
        f"✅ <b>Покупка успешна!</b>\n\n"
        f"📦 Товар: {product['name']}\n"
        f"🔢 Количество: {qty}\n"
        f"💵 Списано: ${total:.2f}\n\n"
        f"📋 <b>Содержимое:</b>\n<code>{product['content']}</code>",
        parse_mode="HTML",
        reply_markup=back_kb("shop"),
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"🛒 Новая покупка товара:\n"
            f"👤 @{callback.from_user.username or callback.from_user.id}\n"
            f"📦 {product['name']} × {qty}\n"
            f"💵 ${total:.2f}",
        )
    except Exception as exc:
        logger.warning("Admin notify error: %s", exc)
