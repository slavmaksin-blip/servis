"""
SMS module handler.

Phone number format: +41XXXXXXXXX
  • +41 — Switzerland country code
  • XXXXXXXXX — exactly 9 digits

Uses SMSSendAPI from utils/api.py.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import SMSSEND_ACCOUNT, SMSSEND_PASSWORD
from utils.api import SMSSendAPI
from utils.keyboards import sms_cancel_keyboard, sms_confirm_keyboard
from utils.states import SMSStates
from utils.validators import PHONE_FORMAT_ERROR_MESSAGE, validate_phone_number

router = Router()
logger = logging.getLogger(__name__)

_api = SMSSendAPI(account=SMSSEND_ACCOUNT, password=SMSSEND_PASSWORD)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@router.message(F.text == "📱 SMS модуль")
async def sms_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📱 <b>SMS модуль</b>\n\n"
        "Введите номер телефона получателя в формате:\n"
        "<code>+41XXXXXXXXX</code>\n\n"
        "Пример: <code>+41791234567</code>",
        reply_markup=sms_cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(SMSStates.waiting_for_phone)


# ---------------------------------------------------------------------------
# Step 1 — phone number
# ---------------------------------------------------------------------------

@router.message(SMSStates.waiting_for_phone)
async def sms_phone_received(message: Message, state: FSMContext) -> None:
    phone = message.text.strip() if message.text else ""

    if not validate_phone_number(phone):
        await message.answer(
            PHONE_FORMAT_ERROR_MESSAGE,
            reply_markup=sms_cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.update_data(phone=phone)
    await message.answer(
        f"✅ Номер принят: <code>{phone}</code>\n\n"
        "Введите текст SMS-сообщения (до 1024 символов):",
        reply_markup=sms_cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(SMSStates.waiting_for_message)


# ---------------------------------------------------------------------------
# Step 2 — message text
# ---------------------------------------------------------------------------

@router.message(SMSStates.waiting_for_message)
async def sms_text_received(message: Message, state: FSMContext) -> None:
    content = message.text.strip() if message.text else ""

    if not content:
        await message.answer(
            "❌ Текст сообщения не может быть пустым.",
            reply_markup=sms_cancel_keyboard(),
        )
        return

    if len(content) > 1024:
        await message.answer(
            f"❌ Текст слишком длинный ({len(content)} символов). "
            "Максимум — 1024 символа.",
            reply_markup=sms_cancel_keyboard(),
        )
        return

    data = await state.get_data()
    phone = data["phone"]

    await state.update_data(content=content)
    await message.answer(
        f"📋 <b>Подтвердите отправку SMS:</b>\n\n"
        f"📞 Получатель: <code>{phone}</code>\n"
        f"💬 Текст:\n<i>{content}</i>",
        reply_markup=sms_confirm_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(SMSStates.waiting_for_confirm)


# ---------------------------------------------------------------------------
# Step 3 — confirmation
# ---------------------------------------------------------------------------

@router.callback_query(SMSStates.waiting_for_confirm, F.data == "sms_send_confirm")
async def sms_send_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    phone: str = data["phone"]
    content: str = data["content"]

    await callback.message.edit_text("⏳ Отправляю SMS…")

    # Strip leading '+' — API expects digits only for the number field
    number_digits = phone.lstrip("+")

    result = _api.send_sms(numbers=number_digits, content=content)
    status_code: int = result.get("status", -99)

    if status_code == 0:
        success_count: int = result.get("success", 0)
        sms_array = result.get("array", [])
        sms_id = str(sms_array[0][1]) if sms_array else None

        db.log_sms(
            user_tg_id=callback.from_user.id,
            phone=phone,
            content=content,
            sms_id=sms_id,
            status=status_code,
        )

        await callback.message.edit_text(
            f"✅ SMS успешно отправлено!\n\n"
            f"📞 Номер: <code>{phone}</code>\n"
            f"📨 Отправлено: {success_count}\n"
            + (f"🆔 ID: <code>{sms_id}</code>" if sms_id else ""),
            parse_mode="HTML",
        )
    else:
        error_desc = _api.describe_status(status_code)
        db.log_sms(
            user_tg_id=callback.from_user.id,
            phone=phone,
            content=content,
            status=status_code,
        )
        await callback.message.edit_text(
            f"❌ Ошибка отправки SMS.\n\n"
            f"Код: <b>{status_code}</b>\n"
            f"Причина: {error_desc}",
            parse_mode="HTML",
        )

    await state.clear()


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "sms_cancel")
async def sms_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Операция отменена.")
