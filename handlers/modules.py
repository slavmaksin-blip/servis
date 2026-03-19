import logging

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID, SMS_COUNTRIES
from utils.api import SMSSendAPI
from utils.keyboards import (
    modules_kb,
    sms_country_kb,
    cancel_kb,
    back_kb,
)
from utils.states import SMSModule
from utils.validators import validate_phone_number, validate_sender_name, validate_sms_content

router = Router()
logger = logging.getLogger(__name__)


# ── SMS Module ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sms_module")
async def cb_sms_module(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "📱 <b>SMS-модуль</b>\n\nВыберите страну назначения:",
        parse_mode="HTML",
        reply_markup=sms_country_kb(),
    )
    await state.set_state(SMSModule.choose_country)


@router.callback_query(SMSModule.choose_country, F.data.startswith("sms_country:"))
async def cb_sms_country(callback: types.CallbackQuery, state: FSMContext) -> None:
    country_key = callback.data.split(":", 1)[1]
    if country_key not in SMS_COUNTRIES:
        await callback.answer("Неизвестная страна", show_alert=True)
        return

    country = SMS_COUNTRIES[country_key]
    await state.update_data(country_key=country_key, country=country)
    await callback.message.edit_text(
        f"🌍 Страна: <b>{country_key}</b> ({country['prefix']})\n\n"
        f"Введите номер телефона (без кода страны, {country['digits']} цифр):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(SMSModule.enter_phone)


@router.message(SMSModule.enter_phone)
async def msg_sms_phone(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    country = data["country"]
    phone = message.text.strip()

    ok, err = validate_phone_number(phone, country["digits"])
    if not ok:
        await message.answer(f"❌ {err}\n\nВведите номер ещё раз:", reply_markup=cancel_kb())
        return

    full_phone = country["prefix"] + phone
    await state.update_data(phone=full_phone)
    await message.answer(
        "✏️ Введите имя отправителя (макс. 12 символов):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(SMSModule.enter_sender)


@router.message(SMSModule.enter_sender)
async def msg_sms_sender(message: types.Message, state: FSMContext) -> None:
    sender = message.text.strip()
    ok, err = validate_sender_name(sender)
    if not ok:
        await message.answer(f"❌ {err}\n\nВведите имя ещё раз:", reply_markup=cancel_kb())
        return

    await state.update_data(sender=sender)
    await message.answer(
        "💬 Введите текст SMS (макс. 160 символов):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(SMSModule.enter_text)


@router.message(SMSModule.enter_text)
async def msg_sms_text(message: types.Message, state: FSMContext, bot: Bot) -> None:
    text = message.text.strip()
    ok, err = validate_sms_content(text)
    if not ok:
        await message.answer(f"❌ {err}\n\nВведите текст ещё раз:", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    await state.clear()

    status_msg = await message.answer("⏳ Отправка SMS…")
    try:
        result = await SMSSendAPI.send_sms(data["phone"], data["sender"], text)
        await status_msg.edit_text(
            f"✅ SMS отправлено!\n\n"
            f"📞 Номер: <code>{data['phone']}</code>\n"
            f"👤 Отправитель: {data['sender']}\n"
            f"📨 Статус: {result.get('status', 'ok')}",
            parse_mode="HTML",
            reply_markup=back_kb("modules"),
        )
    except Exception as exc:
        logger.error("SMS send error: %s", exc)
        await status_msg.edit_text(
            f"❌ Ошибка отправки SMS: {exc}",
            reply_markup=back_kb("modules"),
        )


# ── Stubs ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({"mailer_module", "screen_module", "proxy_module"}))
async def cb_stub_module(callback: types.CallbackQuery) -> None:
    names = {
        "mailer_module": "Mailer",
        "screen_module": "Screen",
        "proxy_module": "Proxy",
    }
    name = names.get(callback.data, callback.data)
    await callback.message.edit_text(
        f"🔧 <b>{name}</b>\n\n🚧 В разработке…",
        parse_mode="HTML",
        reply_markup=back_kb("modules"),
    )


# ── Cancel ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=back_kb("main_menu"),
    )
