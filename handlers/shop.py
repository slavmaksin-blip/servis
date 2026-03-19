"""
Email shop handler.

Uses MailBuyAPI (AnyMessage Shop) from utils/api.py.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import MAILBUY_TOKEN
from utils.api import MailBuyAPI
from utils.keyboards import (
    shop_action_keyboard,
    shop_cancel_keyboard,
    shop_domains_keyboard,
)
from utils.states import ShopStates

router = Router()
logger = logging.getLogger(__name__)

_api = MailBuyAPI(token=MAILBUY_TOKEN)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@router.message(F.text == "📧 Магазин почты")
async def shop_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📧 <b>Магазин почты</b>\n\n"
        "Введите сайт, для которого хотите получить почту.\n"
        "Например: <code>instagram.com</code>",
        reply_markup=shop_cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ShopStates.waiting_for_site)


# ---------------------------------------------------------------------------
# Step 1 — site name
# ---------------------------------------------------------------------------

@router.message(ShopStates.waiting_for_site)
async def shop_site_received(message: Message, state: FSMContext) -> None:
    site = message.text.strip().lower() if message.text else ""

    if not site or "." not in site:
        await message.answer(
            "❌ Введите корректное имя сайта.\nПример: <code>instagram.com</code>",
            reply_markup=shop_cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    await message.answer("⏳ Получаю список доступных доменов…")

    result = _api.get_email_quantity(site)

    if result.get("status") != "success":
        error_val = result.get("value", "unknown")
        await message.answer(
            f"❌ Ошибка: {_api.describe_error(error_val)}",
            reply_markup=shop_cancel_keyboard(),
        )
        return

    domains: dict = result.get("data", {})
    available = {k: v for k, v in domains.items() if v.get("count", 0) > 0}

    if not available:
        await message.answer(
            "😔 Для этого сайта нет доступных почтовых ящиков.",
            reply_markup=shop_cancel_keyboard(),
        )
        return

    await state.update_data(site=site)
    await message.answer(
        f"✅ Найдено {sum(v['count'] for v in available.values())} доступных почт "
        f"для <b>{site}</b>.\n\nВыберите домен:",
        reply_markup=shop_domains_keyboard(available),
        parse_mode="HTML",
    )
    await state.set_state(ShopStates.waiting_for_domain)


# ---------------------------------------------------------------------------
# Step 2 — domain selection
# ---------------------------------------------------------------------------

@router.callback_query(ShopStates.waiting_for_domain, F.data.startswith("shop_domain:"))
async def shop_domain_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    domain = callback.data.split(":", 1)[1]
    data = await state.get_data()
    site: str = data["site"]

    await callback.message.edit_text(f"⏳ Заказываю почту <b>@{domain}</b>…", parse_mode="HTML")

    result = _api.order_email(site=site, domain=domain)

    if result.get("status") != "success":
        error_val = result.get("value", "unknown")
        await callback.message.edit_text(
            f"❌ Ошибка заказа почты: {_api.describe_error(error_val)}",
            reply_markup=shop_cancel_keyboard(),
        )
        return

    activation_id: str = result["id"]
    email: str = result["email"]

    db.save_email_order(
        user_tg_id=callback.from_user.id,
        activation_id=activation_id,
        email=email,
        site=site,
        domain=domain,
    )

    await state.update_data(activation_id=activation_id, email=email)
    await callback.message.edit_text(
        f"✅ <b>Почта успешно заказана!</b>\n\n"
        f"📧 Адрес: <code>{email}</code>\n"
        f"🌐 Сайт: {site}\n"
        f"🆔 ID активации: <code>{activation_id}</code>\n\n"
        "Нажмите «Проверить письмо» когда будете ждать входящего сообщения.",
        reply_markup=shop_action_keyboard(activation_id),
        parse_mode="HTML",
    )
    await state.clear()


# ---------------------------------------------------------------------------
# Check message
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("shop_check:"))
async def shop_check_message(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("⏳ Проверяю…")
    activation_id = callback.data.split(":", 1)[1]

    result = _api.get_message(activation_id)

    if result.get("status") == "success":
        code = result.get("value", "")
        await callback.message.edit_text(
            f"📨 <b>Письмо получено!</b>\n\n"
            f"🔑 Код / значение: <code>{code}</code>\n"
            f"🆔 ID активации: <code>{activation_id}</code>",
            reply_markup=shop_action_keyboard(activation_id),
            parse_mode="HTML",
        )
        db.update_email_order_status(activation_id, "message_received")
    else:
        error_val = result.get("value", "unknown")
        if error_val == "wait message":
            await callback.message.edit_text(
                "⏳ Письмо ещё не пришло. Попробуйте немного позже.",
                reply_markup=shop_action_keyboard(activation_id),
            )
        else:
            await callback.message.edit_text(
                f"❌ {_api.describe_error(error_val)}",
                reply_markup=shop_action_keyboard(activation_id),
            )


# ---------------------------------------------------------------------------
# Reorder
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("shop_reorder:"))
async def shop_reorder(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("⏳ Повторный заказ…")
    activation_id = callback.data.split(":", 1)[1]

    result = _api.reorder_email(activation_id=activation_id)

    if result.get("status") == "success":
        new_id: str = result["id"]
        email: str = result["email"]
        db.update_email_order_status(activation_id, "reordered")
        await callback.message.edit_text(
            f"🔁 <b>Повторный заказ выполнен!</b>\n\n"
            f"📧 Адрес: <code>{email}</code>\n"
            f"🆔 Новый ID: <code>{new_id}</code>",
            reply_markup=shop_action_keyboard(new_id),
            parse_mode="HTML",
        )
    else:
        error_val = result.get("value", "unknown")
        await callback.message.edit_text(
            f"❌ Ошибка повторного заказа: {_api.describe_error(error_val)}",
            reply_markup=shop_action_keyboard(activation_id),
        )


# ---------------------------------------------------------------------------
# Cancel order
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("shop_cancel_order:"))
async def shop_cancel_order(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    activation_id = callback.data.split(":", 1)[1]

    result = _api.cancel_email(activation_id)

    if result.get("status") == "success":
        db.update_email_order_status(activation_id, "canceled")
        await callback.message.edit_text(
            f"✅ Почта отменена.\n🆔 ID: <code>{activation_id}</code>",
            parse_mode="HTML",
        )
    else:
        error_val = result.get("value", "unknown")
        await callback.message.edit_text(
            f"❌ Ошибка отмены: {_api.describe_error(error_val)}",
            reply_markup=shop_action_keyboard(activation_id),
        )


# ---------------------------------------------------------------------------
# Generic shop cancel
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "shop_cancel")
async def shop_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Операция отменена.")
