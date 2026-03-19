import os
import json
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    get_user,
    update_user_balance,
    get_categories,
    get_products,
    get_product,
    log_purchase,
)
from handlers.states import ShopEmailStates, ShopProductStates
from utils.keyboards import (
    shop_keyboard,
    email_domains_keyboard,
    email_actions_keyboard,
    categories_keyboard,
    products_keyboard,
    product_confirm_keyboard,
    cancel_keyboard,
    main_menu_keyboard,
)
from utils.mailbuy import get_domains, buy_email, refresh_email, get_email_message, recreate_email

logger = logging.getLogger(__name__)
router = Router()

# Telegram message size limit (max 4096 chars; use 4000 to leave room for formatting)
MAX_MESSAGE_LENGTH = 4000


@router.callback_query(F.data == "menu:shop")
async def show_shop(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_text(
            "🛒 <b>Магазин</b>\n\nВыберите раздел:",
            reply_markup=shop_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "🛒 <b>Магазин</b>\n\nВыберите раздел:",
            reply_markup=shop_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


# ─── EMAIL SECTION ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "shop:email")
async def shop_email(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    api_key = os.getenv("MAILBUY_API_KEY", "")
    await callback.message.edit_text("⏳ Загрузка доменов...", parse_mode="HTML")
    domains = await get_domains(api_key)
    if not domains:
        await callback.message.edit_text(
            "❌ Не удалось загрузить список доменов. Попробуйте позже.",
            reply_markup=shop_keyboard(),
            parse_mode="HTML",
        )
        return
    await callback.message.edit_text(
        "📬 <b>Купить почту</b>\n\nВыберите домен (цена × 3):",
        reply_markup=email_domains_keyboard(domains),
        parse_mode="HTML",
    )
    await state.set_state(ShopEmailStates.select_domain)
    await callback.answer()


@router.callback_query(F.data == "shop:email_cancel")
async def email_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_shop(callback)


@router.callback_query(ShopEmailStates.select_domain, F.data.startswith("email_domain:"))
async def email_domain_selected(callback: CallbackQuery, state: FSMContext) -> None:
    domain = callback.data.split(":", 1)[1]

    api_key = os.getenv("MAILBUY_API_KEY", "")
    domains = await get_domains(api_key)
    domain_info = next((d for d in domains if d["domain"] == domain), None)
    if not domain_info:
        await callback.answer("❌ Домен не найден.", show_alert=True)
        return

    price = domain_info["price"] * 3
    user = await get_user(callback.from_user.id)
    if not user or user["balance"] < price:
        await callback.answer(
            f"❌ Недостаточно баланса. Нужно ${price:.2f}, у вас ${user['balance']:.2f}",
            show_alert=True,
        )
        return

    await callback.message.edit_text("⏳ Покупка почты...")
    result = await buy_email(api_key, domain)

    if result["success"]:
        await update_user_balance(callback.from_user.id, -price)
        email_addr = result["email"]
        password = result["password"]
        link = result["link"]
        status = result["status"]

        await state.update_data(
            email=email_addr, domain=domain, password=password, link=link
        )
        await state.set_state(ShopEmailStates.domain_input)

        await callback.message.edit_text(
            f"✅ <b>Почта успешно создана!</b>\n\n"
            f"📧 Email: <code>{email_addr}</code>\n"
            f"🔑 Пароль/Код: <code>{password}</code>\n"
            f"🔗 Ссылка: {link or '—'}\n"
            f"📋 Статус: {status}\n\n"
            f"💸 Списано: <b>${price:.2f}</b>",
            reply_markup=email_actions_keyboard(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка при покупке почты: {result['status']}",
            reply_markup=shop_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "email:refresh")
async def email_refresh(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    email = data.get("email")
    if not email:
        await callback.answer("❌ Сессия истекла.", show_alert=True)
        return
    api_key = os.getenv("MAILBUY_API_KEY", "")
    result = await refresh_email(api_key, email)
    await callback.answer(
        f"🔄 Статус: {result['status']}", show_alert=True
    )


@router.callback_query(F.data == "email:recreate")
async def email_recreate(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    email = data.get("email")
    domain = data.get("domain")
    if not email or not domain:
        await callback.answer("❌ Сессия истекла.", show_alert=True)
        return
    api_key = os.getenv("MAILBUY_API_KEY", "")
    await callback.message.edit_text("⏳ Пересоздание почты...")
    result = await recreate_email(api_key, email, domain)
    if result["success"]:
        await state.update_data(
            email=result["email"],
            password=result["password"],
            link=result["link"],
        )
        await callback.message.edit_text(
            f"✅ <b>Почта пересоздана!</b>\n\n"
            f"📧 Email: <code>{result['email']}</code>\n"
            f"🔑 Пароль/Код: <code>{result['password']}</code>\n"
            f"🔗 Ссылка: {result['link'] or '—'}\n"
            f"📋 Статус: {result['status']}",
            reply_markup=email_actions_keyboard(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка пересоздания: {result['status']}",
            reply_markup=email_actions_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "email:get_message")
async def email_get_message(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    email = data.get("email")
    if not email:
        await callback.answer("❌ Сессия истекла.", show_alert=True)
        return
    api_key = os.getenv("MAILBUY_API_KEY", "")
    result = await get_email_message(api_key, email)
    raw_text = json.dumps(result["raw"], ensure_ascii=False, indent=2)
    if len(raw_text) > MAX_MESSAGE_LENGTH:
        raw_text = raw_text[:MAX_MESSAGE_LENGTH] + "\n...(обрезано)"
    await callback.message.answer(
        f"📨 <b>Сообщения для {email}:</b>\n\n<pre>{raw_text}</pre>",
        parse_mode="HTML",
    )
    await callback.answer()


# ─── PRODUCTS SECTION ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "shop:products")
async def shop_products(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    categories = await get_categories()
    if not categories:
        await callback.answer("📦 Товаров пока нет.", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            "📦 <b>Товары</b>\n\nВыберите категорию:",
            reply_markup=categories_keyboard(categories),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "📦 <b>Товары</b>\n\nВыберите категорию:",
            reply_markup=categories_keyboard(categories),
            parse_mode="HTML",
        )
    await state.set_state(ShopProductStates.category)
    await callback.answer()


@router.callback_query(F.data == "shop:products_cancel")
async def products_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_shop(callback)


@router.callback_query(ShopProductStates.category, F.data.startswith("cat:"))
async def category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    products = await get_products(category_id)
    await state.update_data(category_id=category_id)
    if not products:
        await callback.answer("📦 В этой категории пока нет товаров.", show_alert=True)
        return
    await callback.message.edit_text(
        "📦 <b>Товары</b>\n\nВыберите товар:",
        reply_markup=products_keyboard(products),
        parse_mode="HTML",
    )
    await state.set_state(ShopProductStates.product)
    await callback.answer()


@router.callback_query(ShopProductStates.product, F.data.startswith("prod:"))
async def product_selected(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await get_product(product_id)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return
    await state.update_data(product_id=product_id)
    await callback.message.edit_text(
        f"📦 <b>{product['name']}</b>\n\n"
        f"📝 {product['description'] or '—'}\n"
        f"💰 Цена: <b>${product['price']:.2f}</b>\n\n"
        f"Введите количество:",
        parse_mode="HTML",
    )
    await state.set_state(ShopProductStates.quantity)
    await callback.answer()


@router.message(ShopProductStates.quantity)
async def product_quantity_entered(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введите корректное количество (целое число больше 0):",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()
    product_id = data["product_id"]
    product = await get_product(product_id)
    total = product["price"] * quantity
    await state.update_data(quantity=quantity, total=total)

    await message.answer(
        f"📦 <b>Подтверждение заказа</b>\n\n"
        f"Товар: <b>{product['name']}</b>\n"
        f"Количество: {quantity}\n"
        f"Сумма: <b>${total:.2f}</b>\n\n"
        f"Подтвердить покупку?",
        reply_markup=product_confirm_keyboard(product_id, quantity),
        parse_mode="HTML",
    )
    await state.set_state(ShopProductStates.confirm)


@router.callback_query(ShopProductStates.confirm, F.data.startswith("buy_confirm:"))
async def product_buy_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    parts = callback.data.split(":")
    product_id = int(parts[1])
    quantity = int(parts[2])

    product = await get_product(product_id)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    total = product["price"] * quantity
    user = await get_user(callback.from_user.id)
    if not user or user["balance"] < total:
        await callback.answer(
            f"❌ Недостаточно баланса. Нужно ${total:.2f}, у вас ${user['balance']:.2f}",
            show_alert=True,
        )
        return

    await update_user_balance(callback.from_user.id, -total)
    await log_purchase(callback.from_user.id, product_id, quantity, total)
    await state.clear()

    result_text = (
        f"✅ <b>Покупка выполнена!</b>\n\n"
        f"📦 Товар: <b>{product['name']}</b>\n"
        f"🔢 Количество: {quantity}\n"
        f"💸 Списано: <b>${total:.2f}</b>"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В магазин", callback_data="menu:shop"))

    if product.get("file_id"):
        await callback.message.answer_document(
            document=product["file_id"],
            caption=result_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
        await callback.message.delete()
    else:
        await callback.message.edit_text(
            result_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )

    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        try:
            u = callback.from_user
            mention = f"@{u.username}" if u.username else u.full_name
            await bot.send_message(
                int(admin_id),
                f"🛒 <b>Новая покупка!</b>\n\n"
                f"👤 Пользователь: {mention} (<code>{u.id}</code>)\n"
                f"📦 Товар: {product['name']}\n"
                f"🔢 Кол-во: {quantity}\n"
                f"💰 Сумма: ${total:.2f}",
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Cannot notify admin about purchase: %s", exc)

    await callback.answer()
