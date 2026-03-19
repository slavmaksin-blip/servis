import json
import logging
import os
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db import (
    get_user,
    update_user_balance,
    get_categories,
    get_products,
    get_product,
    get_product_stock,
    pop_product_files,
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
from utils.mailbuy import get_domains, buy_email, refresh_email, get_email_messages, recreate_email

logger = logging.getLogger(__name__)
router = Router()

# Telegram message size limit (max 4096 chars; use 4000 to leave room for formatting)
MAX_MESSAGE_LENGTH = 4000


async def _safe_edit(
    message: Message,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> None:
    """Edit or replace a message, handling media/caption messages gracefully."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except TelegramBadRequest as exc:
        if "no text in the message" in str(exc).lower():
            try:
                await message.edit_caption(
                    caption=text, reply_markup=reply_markup, parse_mode=parse_mode
                )
                return
            except TelegramBadRequest:
                pass
    except Exception:
        pass
    # Fallback: delete original and send new
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


@router.callback_query(F.data == "menu:shop")
async def show_shop(callback: CallbackQuery) -> None:
    try:
        await _safe_edit(
            callback.message,
            "🛒 <b>Магазин</b>\n\nВыберите раздел:",
            reply_markup=shop_keyboard(),
        )
    except Exception as exc:
        logger.warning("show_shop error: %s", exc)
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
    try:
        await _safe_edit(callback.message, "⏳ Загрузка доменов...")
        domains = await get_domains(api_key)
    except Exception as exc:
        logger.error("get_domains error: %s", exc)
        domains = []

    if not domains:
        try:
            await _safe_edit(
                callback.message,
                "❌ Не удалось загрузить список доменов. Попробуйте позже.",
                reply_markup=shop_keyboard(),
            )
        except Exception:
            pass
        await callback.answer()
        return

    try:
        await _safe_edit(
            callback.message,
            "📬 <b>Купить почту</b>\n\nВыберите домен (цена × 3):",
            reply_markup=email_domains_keyboard(domains),
        )
    except Exception as exc:
        logger.warning("shop_email edit error: %s", exc)
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

    try:
        domains = await get_domains(api_key)
    except Exception as exc:
        logger.error("get_domains error: %s", exc)
        domains = []

    domain_info = next((d for d in domains if d["domain"] == domain), None)
    if not domain_info:
        await callback.answer("❌ Домен не найден.", show_alert=True)
        return

    price = domain_info["price"] * 3
    user = await get_user(callback.from_user.id)
    if not user or user["balance"] < price:
        balance = user["balance"] if user else 0.0
        await callback.answer(
            f"❌ Недостаточно баланса. Нужно ${price:.2f}, у вас ${balance:.2f}",
            show_alert=True,
        )
        return

    try:
        await _safe_edit(callback.message, "⏳ Покупка почты...")
        result = await buy_email(api_key, domain)
    except Exception as exc:
        logger.error("buy_email error: %s", exc)
        result = {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": "unexpected_error",
            "error": str(exc),
        }

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

        try:
            await _safe_edit(
                callback.message,
                f"✅ <b>Почта успешно создана!</b>\n\n"
                f"📧 Email: <code>{email_addr}</code>\n"
                f"🔑 Пароль/Код: <code>{password}</code>\n"
                f"🔗 Ссылка: {link or '—'}\n"
                f"📋 Статус: {status}\n\n"
                f"💸 Списано: <b>${price:.2f}</b>",
                reply_markup=email_actions_keyboard(),
            )
        except Exception as exc:
            logger.warning("email result edit error: %s", exc)
    else:
        error_detail = result.get("error") or result.get("status", "—")
        try:
            await _safe_edit(
                callback.message,
                f"❌ Ошибка при покупке почты: {error_detail}",
                reply_markup=shop_keyboard(),
            )
        except Exception as exc:
            logger.warning("email error edit error: %s", exc)
    await callback.answer()


@router.callback_query(F.data == "email:refresh")
async def email_refresh(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    email = data.get("email")
    if not email:
        await callback.answer("❌ Сессия истекла.", show_alert=True)
        return
    api_key = os.getenv("MAILBUY_API_KEY", "")
    try:
        result = await refresh_email(api_key, email)
        status_text = result["status"]
    except Exception as exc:
        logger.error("refresh_email error: %s", exc)
        status_text = "connection_error"
    await callback.answer(f"🔄 Статус: {status_text}", show_alert=True)


@router.callback_query(F.data == "email:recreate")
async def email_recreate(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    email = data.get("email")
    domain = data.get("domain")
    if not email or not domain:
        await callback.answer("❌ Сессия истекла.", show_alert=True)
        return
    api_key = os.getenv("MAILBUY_API_KEY", "")
    try:
        await _safe_edit(callback.message, "⏳ Пересоздание почты...")
        result = await recreate_email(api_key, email, domain)
    except Exception as exc:
        logger.error("recreate_email error: %s", exc)
        result = {"success": False, "error": str(exc), "status": "unexpected_error"}

    if result["success"]:
        await state.update_data(
            email=result["email"],
            password=result["password"],
            link=result["link"],
        )
        try:
            await _safe_edit(
                callback.message,
                f"✅ <b>Почта пересоздана!</b>\n\n"
                f"📧 Email: <code>{result['email']}</code>\n"
                f"🔑 Пароль/Код: <code>{result['password']}</code>\n"
                f"🔗 Ссылка: {result['link'] or '—'}\n"
                f"📋 Статус: {result['status']}",
                reply_markup=email_actions_keyboard(),
            )
        except Exception as exc:
            logger.warning("recreate result edit error: %s", exc)
    else:
        error_detail = result.get("error") or result.get("status", "—")
        try:
            await _safe_edit(
                callback.message,
                f"❌ Ошибка пересоздания: {error_detail}",
                reply_markup=email_actions_keyboard(),
            )
        except Exception as exc:
            logger.warning("recreate error edit error: %s", exc)
    await callback.answer()


@router.callback_query(F.data == "email:get_message")
async def email_get_message(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    email = data.get("email")
    if not email:
        await callback.answer("❌ Сессия истекла.", show_alert=True)
        return
    api_key = os.getenv("MAILBUY_API_KEY", "")
    try:
        result = await get_email_messages(api_key, email)
    except Exception as exc:
        logger.error("get_email_messages error: %s", exc)
        result = {"success": False, "messages": [], "raw": {}, "error": str(exc)}

    if result["success"] and result["messages"]:
        raw_text = json.dumps(result["messages"], ensure_ascii=False, indent=2)
    elif result["success"]:
        raw_text = "📭 Нет новых сообщений."
    else:
        raw_text = f"❌ Ошибка: {result.get('error', '—')}"

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
    try:
        categories = await get_categories()
    except Exception as exc:
        logger.error("get_categories error: %s", exc)
        categories = []

    if not categories:
        await callback.answer("📦 Товаров пока нет.", show_alert=True)
        return
    try:
        await _safe_edit(
            callback.message,
            "📦 <b>Товары</b>\n\nВыберите категорию:",
            reply_markup=categories_keyboard(categories),
        )
    except Exception as exc:
        logger.warning("shop_products edit error: %s", exc)
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
    try:
        products = await get_products(category_id)
    except Exception as exc:
        logger.error("get_products error: %s", exc)
        products = []

    await state.update_data(category_id=category_id)
    if not products:
        await callback.answer("📦 В этой категории пока нет товаров.", show_alert=True)
        return
    try:
        await _safe_edit(
            callback.message,
            "📦 <b>Товары</b>\n\nВыберите товар:",
            reply_markup=products_keyboard(products),
        )
    except Exception as exc:
        logger.warning("category_selected edit error: %s", exc)
    await state.set_state(ShopProductStates.product)
    await callback.answer()


@router.callback_query(ShopProductStates.product, F.data.startswith("prod:"))
async def product_selected(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[1])
    try:
        product = await get_product(product_id)
    except Exception as exc:
        logger.error("get_product error: %s", exc)
        product = None

    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    stock = product.get("stock", 0)
    if stock == 0:
        await callback.answer("❌ Товар закончился.", show_alert=True)
        return

    await state.update_data(product_id=product_id)
    try:
        await _safe_edit(
            callback.message,
            f"📦 <b>{product['name']}</b> [в наличии: {stock}]\n\n"
            f"📝 {product['description'] or '—'}\n"
            f"💰 Цена за ед.: <b>${product['price']:.2f}</b>\n\n"
            f"Введите количество (макс. {stock}):",
        )
    except Exception as exc:
        logger.warning("product_selected edit error: %s", exc)
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
    try:
        product = await get_product(product_id)
    except Exception as exc:
        logger.error("get_product error: %s", exc)
        product = None

    if not product:
        await message.answer("❌ Товар не найден.", reply_markup=main_menu_keyboard(), parse_mode="HTML")
        await state.clear()
        return

    stock = product.get("stock", 0)
    if quantity > stock:
        await message.answer(
            f"❌ Недостаточно товара в наличии. Доступно: {stock} шт.",
            reply_markup=cancel_keyboard(),
        )
        return

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

    try:
        product = await get_product(product_id)
    except Exception as exc:
        logger.error("get_product error during purchase: %s", exc)
        await callback.answer("❌ Ошибка при получении товара.", show_alert=True)
        return

    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    # Re-check stock at purchase time to prevent race conditions
    stock = product.get("stock", 0)
    if stock < quantity:
        await callback.answer(
            f"❌ Недостаточно товара. В наличии: {stock} шт.",
            show_alert=True,
        )
        return

    total = product["price"] * quantity
    user = await get_user(callback.from_user.id)
    if not user or user["balance"] < total:
        balance = user["balance"] if user else 0.0
        await callback.answer(
            f"❌ Недостаточно баланса. Нужно ${total:.2f}, у вас ${balance:.2f}",
            show_alert=True,
        )
        return

    # Atomically consume N stock units
    try:
        file_ids = await pop_product_files(product_id, quantity)
    except Exception as exc:
        logger.error("pop_product_files error: %s", exc)
        await callback.answer("❌ Ошибка при обработке заказа.", show_alert=True)
        return

    if len(file_ids) < quantity:
        await callback.answer(
            "❌ Не хватает товара в наличии (Not enough stock).",
            show_alert=True,
        )
        return

    try:
        await update_user_balance(callback.from_user.id, -total)
        await log_purchase(callback.from_user.id, product_id, quantity, total)
    except Exception as exc:
        logger.error("balance/log error during purchase: %s", exc)

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В магазин", callback_data="menu:shop"))

    result_caption = (
        f"✅ <b>Покупка выполнена!</b>\n\n"
        f"📦 Товар: <b>{product['name']}</b>\n"
        f"🔢 Количество: {quantity}\n"
        f"💸 Списано: <b>${total:.2f}</b>"
    )

    # Delete the confirmation message
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Send each purchased file as a separate document
    for idx, fid in enumerate(file_ids):
        caption = result_caption if idx == 0 else None
        try:
            await callback.message.answer_document(
                document=fid,
                caption=caption,
                reply_markup=builder.as_markup() if idx == len(file_ids) - 1 else None,
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.error("Error sending file %s: %s", fid, exc)

    # Notify admin
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
