import os
import re

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID
from states.states import SmsStates
from utils.keyboards import (
    modules_kb, sms_countries_kb, back_to_main_kb, cancel_kb,
)
from utils.api import smssend_send_sms

router = Router()

START_IMAGE = "start.png"
PHONE_PATTERN = re.compile(r"^\+41\d{9}$")


async def _safe_edit_or_send(
    bot: Bot,
    message,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> None:
    """
    Safely edit or send a message.
    - If the message has text: edit_text.
    - If it has a caption (photo/media): edit_caption.
    - Otherwise: delete old and send new.
    """
    try:
        if message.text:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        elif message.caption is not None:
            await message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.delete()
            await bot.send_message(
                message.chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
    except Exception:
        try:
            await message.delete()
        except Exception:
            pass
        await bot.send_message(
            message.chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )


async def _has_active_subscription(user: dict) -> bool:
    from datetime import datetime
    sub_end = user.get("sub_end")
    if not sub_end:
        return False
    try:
        return datetime.fromisoformat(sub_end) > datetime.now()
    except Exception:
        return False


@router.callback_query(F.data == "modules")
async def show_modules(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    if not user or not await _has_active_subscription(user):
        await callback.answer(
            "❌ Для доступа к модулям нужна активная подписка!\n"
            "Купите подписку в разделе «Профиль».",
            show_alert=True,
        )
        return

    text = "🔧 <b>Модули</b>\n\nВыберите модуль:"
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
            reply_markup=modules_kb(),
            parse_mode="HTML",
        )
    else:
        await _safe_edit_or_send(callback.bot, callback.message, text, modules_kb())
    await callback.answer()


@router.callback_query(F.data.in_({"module_mailer", "module_screen", "module_proxy"}))
async def module_stub(callback: CallbackQuery) -> None:
    await callback.answer("🚧 Модуль в разработке", show_alert=True)


@router.callback_query(F.data == "module_sms")
async def module_sms(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SmsStates.country)
    text = "📨 <b>SMS Модуль</b>\n\nВыберите страну:"
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
            reply_markup=sms_countries_kb(),
            parse_mode="HTML",
        )
    else:
        await _safe_edit_or_send(callback.bot, callback.message, text, sms_countries_kb())
    await callback.answer()


@router.callback_query(F.data == "sms_country_disabled")
async def sms_country_disabled(callback: CallbackQuery) -> None:
    await callback.answer(
        "❌ Эта страна временно недоступна.", show_alert=True
    )


@router.callback_query(F.data == "sms_country_ch", SmsStates.country)
async def sms_country_ch(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SmsStates.phone)
    await state.update_data(country="CH")
    await callback.message.answer(
        "📱 Введите номер телефона в формате <code>+41XXXXXXXXX</code> (9 цифр после кода страны):",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SmsStates.phone)
async def sms_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip() if message.text else ""
    if not PHONE_PATTERN.match(phone):
        await message.answer(
            "❌ Неверный формат. Введите номер в формате <code>+41XXXXXXXXX</code>:",
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(SmsStates.sender)
    await message.answer(
        "✏️ Введите имя отправителя (до 12 символов, только латиница/цифры):",
        reply_markup=cancel_kb(),
    )


@router.message(SmsStates.sender)
async def sms_sender(message: Message, state: FSMContext) -> None:
    sender = message.text.strip() if message.text else ""
    if not sender or len(sender) > 12 or not re.match(r"^[A-Za-z0-9]+$", sender):
        await message.answer(
            "❌ Имя отправителя должно быть до 12 символов (латиница/цифры):",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(sender=sender)
    await state.set_state(SmsStates.message)
    await message.answer(
        "💬 Введите текст сообщения (до 160 символов):",
        reply_markup=cancel_kb(),
    )


@router.message(SmsStates.message)
async def sms_message(message: Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else ""
    if not text or len(text) > 160:
        await message.answer(
            "❌ Сообщение должно быть от 1 до 160 символов:",
            reply_markup=cancel_kb(),
        )
        return

    data = await state.get_data()
    await state.clear()

    phone = data["phone"]
    sender = data["sender"]

    await message.answer("⏳ Отправляю SMS...")

    result = await smssend_send_sms(phone=phone, sender=sender, message=text)

    if result.get("status") == "ok":
        msg_id = result.get("id", "—")
        await message.answer(
            f"✅ <b>SMS отправлена успешно!</b>\n"
            f"📱 Номер: <code>{phone}</code>\n"
            f"👤 Отправитель: <code>{sender}</code>\n"
            f"🆔 ID сообщения: <code>{msg_id}</code>",
            reply_markup=back_to_main_kb(),
            parse_mode="HTML",
        )
    else:
        err = result.get("message", "Неизвестная ошибка")
        await message.answer(
            f"❌ <b>Ошибка отправки SMS:</b>\n<code>{err}</code>",
            reply_markup=back_to_main_kb(),
            parse_mode="HTML",
        )
