import json
import os

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID, MAIL_PRICE_MULTIPLIER
from states.states import MailStates, ShopStates
from utils.keyboards import (
    shop_kb, mail_order_kb, mail_received_kb, cancel_kb, back_to_main_kb,
)
from utils.api import mailbuy_get_domains, mailbuy_buy_account, mailbuy_check_messages

router = Router()

START_IMAGE = "start.png"


async def _send_shop_menu(bot: Bot, chat_id: int) -> None:
    text = "🛒 <b>Магазин</b>\n\nВыберите раздел:"
    if os.path.exists(START_IMAGE):
        photo = FSInputFile(START_IMAGE)
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=text,
            reply_markup=shop_kb(),
            parse_mode="HTML",
        )
    else:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=shop_kb(), parse_mode="HTML")


@router.callback_query(F.data == "shop")
async def show_shop(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _send_shop_menu(callback.bot, callback.message.chat.id)
    await callback.answer()


# ─────────────────────── MAIL ───────────────────────

@router.callback_query(F.data == "shop_mail")
async def shop_mail(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MailStates.domain_input)
    await callback.message.answer(
        "📧 <b>Купить почту</b>\n\nВведите домен (например: <code>instagram.com</code>):",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(MailStates.domain_input)
async def mail_domain_input(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip().lower()
    if not query:
        await message.answer("❌ Введите домен:", reply_markup=cancel_kb())
        return

    await message.answer("⏳ Загружаю доступные домены...")
    domains = await mailbuy_get_domains()

    if not domains:
        await message.answer(
            "❌ Не удалось загрузить список доменов. Попробуйте позже.",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
        return

    # Filter by query if specified
    filtered = [d for d in domains if query in d.get("name", "").lower()]
    if not filtered:
        filtered = domains[:20]  # show all if no match

    await state.update_data(domains=filtered)
    await state.set_state(MailStates.selecting_domain)

    buttons = []
    for d in filtered[:20]:
        name = d.get("name", "")
        api_price = float(d.get("price", 0))
        bot_price = round(api_price * MAIL_PRICE_MULTIPLIER, 2)
        buttons.append([InlineKeyboardButton(
            text=f"{name} — {bot_price}$",
            callback_data=f"mail_buy:{name}:{bot_price}",
        )])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "📋 <b>Доступные домены:</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mail_buy:"), MailStates.selecting_domain)
async def mail_buy_domain(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    domain = parts[1]
    price = float(parts[2])

    user = await db.get_user(callback.from_user.id)
    if not user or user["balance"] < price:
        await callback.answer(
            f"❌ Недостаточно средств. Нужно {price}$, у вас {user['balance'] if user else 0}$.",
            show_alert=True,
        )
        return

    await callback.message.answer("⏳ Покупаю почтовый аккаунт...")

    result = await mailbuy_buy_account(domain)

    if "error" in result or not result.get("email"):
        err = result.get("error", "Неизвестная ошибка")
        await callback.message.answer(
            f"❌ Ошибка при покупке почты: <code>{err}</code>",
            reply_markup=back_to_main_kb(),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    # Deduct balance
    await db.update_balance(callback.from_user.id, -price)

    email = result.get("email", "")
    ext_id = str(result.get("id", ""))
    code = result.get("code", "—")
    link = result.get("link", "—")
    status = result.get("status", "pending")
    full_data = json.dumps(result, ensure_ascii=False)

    order_id = await db.create_mail_order(
        tg_id=callback.from_user.id,
        domain=domain,
        email=email,
        price=price,
        external_id=ext_id,
        full_data=full_data,
    )

    await state.clear()

    await callback.message.answer(
        f"✅ <b>Почта куплена!</b>\n\n"
        f"🌐 Сайт: <code>{domain}</code>\n"
        f"📧 Email: <code>{email}</code>\n"
        f"💰 Цена: <code>{price}$</code>\n"
        f"🔑 Код: <code>{code}</code>\n"
        f"🔗 Ссылка: {link}\n"
        f"📊 Статус: <code>{status}</code>",
        reply_markup=mail_order_kb(order_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mail_check:"))
async def mail_check(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    order = await db.get_mail_order(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return

    result = await mailbuy_check_messages(order["external_id"])
    messages = result.get("messages", [])
    count = result.get("count", 0)

    if count > 0 or messages:
        full_data = json.dumps(result, ensure_ascii=False)
        await db.update_mail_order(order_id, "received", full_data)
        await callback.message.answer(
            f"📬 <b>Письмо получено!</b>\nКоличество: {count}",
            reply_markup=mail_received_kb(order_id),
            parse_mode="HTML",
        )
    else:
        await callback.answer("📭 Письма ещё нет. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("mail_getmsg:"))
async def mail_getmsg(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    order = await db.get_mail_order(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return
    await callback.message.answer(
        f"<pre>{order['full_data']}</pre>",
        reply_markup=back_to_main_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mail_recreate:"))
async def mail_recreate(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":")[1])
    order = await db.get_mail_order(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return

    result = await mailbuy_buy_account(order["domain"])
    if "error" in result or not result.get("email"):
        err = result.get("error", "Неизвестная ошибка")
        await callback.message.answer(
            f"❌ Ошибка при пересоздании: <code>{err}</code>",
            reply_markup=back_to_main_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    email = result.get("email", "")
    ext_id = str(result.get("id", ""))
    code = result.get("code", "—")
    link = result.get("link", "—")
    status = result.get("status", "pending")
    full_data = json.dumps(result, ensure_ascii=False)

    await db.update_mail_order(order_id, status, full_data)

    await callback.message.answer(
        f"🔄 <b>Почта пересоздана!</b>\n\n"
        f"📧 Email: <code>{email}</code>\n"
        f"🔑 Код: <code>{code}</code>\n"
        f"🔗 Ссылка: {link}\n"
        f"📊 Статус: <code>{status}</code>",
        reply_markup=mail_order_kb(order_id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────── PRODUCTS ───────────────────────

async def _build_products_kb(category_id: int) -> InlineKeyboardMarkup:
    products = await db.get_products(category_id)
    buttons = []
    for p in products:
        stock = await db.get_stock_count(p["id"])
        buttons.append([InlineKeyboardButton(
            text=f"{p['name']} [{stock}] — {p['price']}$",
            callback_data=f"product:{p['id']}",
        )])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "shop_products")
async def shop_products(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ShopStates.category)
    categories = await db.get_categories()
    if not categories:
        await callback.answer("❌ Нет доступных категорий.", show_alert=True)
        return

    buttons = [[InlineKeyboardButton(
        text=cat["name"], callback_data=f"category:{cat['id']}"
    )] for cat in categories]
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = "🛍 <b>Выберите категорию:</b>"
    if os.path.exists(START_IMAGE):
        photo = FSInputFile(START_IMAGE)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=photo,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("category:"), ShopStates.category)
async def show_category_products(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=cat_id)
    await state.set_state(ShopStates.product)

    kb = await _build_products_kb(cat_id)
    await callback.message.answer("🛍 <b>Выберите товар:</b>", reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("product:"), ShopStates.product)
async def show_product(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    stock = await db.get_stock_count(product_id)
    await state.update_data(product_id=product_id)
    await state.set_state(ShopStates.quantity)

    await callback.message.answer(
        f"📦 <b>{product['name']}</b>\n\n"
        f"📄 {product.get('description', '—')}\n"
        f"💰 Цена: {product['price']}$ за шт.\n"
        f"📊 В наличии: {stock}\n\n"
        "Введите количество:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ShopStates.quantity)
async def product_quantity(message: Message, state: FSMContext) -> None:
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❌ Введите корректное количество (целое число > 0):", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    product_id = data["product_id"]
    product = await db.get_product(product_id)
    stock = await db.get_stock_count(product_id)

    if qty > stock:
        await message.answer(
            f"❌ Недостаточно товара на складе. В наличии: {stock}",
            reply_markup=cancel_kb(),
        )
        return

    total = round(product["price"] * qty, 2)
    await state.update_data(quantity=qty, total=total)
    await state.set_state(ShopStates.confirm)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_purchase")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")],
    ])
    await message.answer(
        f"🛍 <b>Подтверждение покупки</b>\n\n"
        f"📦 Товар: {product['name']}\n"
        f"🔢 Количество: {qty}\n"
        f"💰 Итого: {total}$",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "confirm_purchase", ShopStates.confirm)
async def confirm_purchase(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    product_id = data["product_id"]
    qty = data["quantity"]
    total = data["total"]

    user = await db.get_user(callback.from_user.id)
    if not user or user["balance"] < total:
        await callback.answer(
            f"❌ Недостаточно средств. Нужно {total}$, у вас {user['balance'] if user else 0}$.",
            show_alert=True,
        )
        return

    items = await db.take_stock_items(product_id, qty)
    if not items:
        await callback.answer("❌ Товар закончился на складе.", show_alert=True)
        return

    await db.update_balance(callback.from_user.id, -total)
    product = await db.get_product(product_id)
    await db.create_order(callback.from_user.id, product_id, qty, total)
    await state.clear()

    await callback.message.answer(
        f"✅ <b>Покупка совершена!</b>\n"
        f"📦 {product['name']} x{qty} — {total}$\n\n"
        "Ваши файлы:"
    )

    for item in items:
        try:
            await callback.bot.send_document(
                chat_id=callback.message.chat.id,
                document=item["file_id"],
                caption=f"📄 {item.get('file_name', 'file')}",
            )
        except Exception as exc:
            await callback.message.answer(f"❌ Не удалось отправить файл: {exc}")

    await callback.message.answer("✅ Всё готово!", reply_markup=back_to_main_kb())

    if ADMIN_ID:
        try:
            uname = callback.from_user.username or str(callback.from_user.id)
            await callback.bot.send_message(
                ADMIN_ID,
                f"📦 Покупка товара: @{uname}, ID: {callback.from_user.id}, "
                f"{product['name']} x{qty}",
            )
        except Exception:
            pass

    await callback.answer()
