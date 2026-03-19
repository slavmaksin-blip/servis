import os
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db import get_user
from handlers.states import SMSStates
from utils.keyboards import (
    modules_keyboard,
    sms_countries_keyboard,
    cancel_keyboard,
    main_menu_keyboard,
)
from utils.smssend import COUNTRIES, get_country_prefix, send_sms

logger = logging.getLogger(__name__)
router = Router()

# SMS validation constants (per SMS standard and SMSSEND API requirements)
MIN_PHONE_DIGITS = 7       # minimum digits in a phone number (excl. country code)
MAX_SENDER_LENGTH = 11     # maximum sender ID length per SMS standard
MAX_SMS_LENGTH = 160       # standard single SMS character limit


async def has_active_subscription(user: dict) -> bool:
    sub_end = user.get("sub_end")
    if not sub_end:
        return False
    if isinstance(sub_end, str):
        try:
            sub_end = datetime.fromisoformat(sub_end)
        except ValueError:
            return False
    return sub_end > datetime.now()


async def require_subscription(callback: CallbackQuery) -> bool:
    user = await get_user(callback.from_user.id)
    if not user or not await has_active_subscription(user):
        await callback.answer(
            "⏳ У вас нет активной подписки.\nПерейдите в Профиль → Купить подписку.",
            show_alert=True,
        )
        return False
    return True


async def safe_edit_text(
    message: Message,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> None:
    """
    Edit a message safely, handling Telegram's limitations:
    - If the message has no text (e.g. it contains media), use edit_caption.
    - If editing is not possible (e.g. the message is too old or unchanged),
      delete the original and send a new message.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except TelegramBadRequest as exc:
        error_text = str(exc).lower()
        if "no text in the message" in error_text or "message has no text" in error_text:
            # Message contains media — try editing the caption instead
            try:
                await message.edit_caption(
                    caption=text, reply_markup=reply_markup, parse_mode=parse_mode
                )
                return
            except TelegramBadRequest:
                pass
        # Fallback: delete original and send a new message
        try:
            await message.delete()
        except Exception:
            pass
    except Exception:
        pass

    await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


@router.callback_query(F.data == "menu:modules")
async def show_modules(callback: CallbackQuery) -> None:
    if not await require_subscription(callback):
        return
    await safe_edit_text(
        callback.message,
        "🔧 <b>Модули</b>\n\nВыберите нужный модуль:",
        reply_markup=modules_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "module:mailer")
async def module_mailer(callback: CallbackQuery) -> None:
    if not await require_subscription(callback):
        return
    await callback.answer("🚧 Модуль Mailer — в разработке.", show_alert=True)


@router.callback_query(F.data == "module:screen")
async def module_screen(callback: CallbackQuery) -> None:
    if not await require_subscription(callback):
        return
    await callback.answer("🚧 Модуль Screen — в разработке.", show_alert=True)


@router.callback_query(F.data == "module:proxy")
async def module_proxy(callback: CallbackQuery) -> None:
    if not await require_subscription(callback):
        return
    await callback.answer("🚧 Модуль Proxy — в разработке.", show_alert=True)


@router.callback_query(F.data == "module:sms")
async def module_sms(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_subscription(callback):
        return
    await safe_edit_text(
        callback.message,
        "📱 <b>SMS-рассылка</b>\n\nШаг 1. Выберите страну:",
        reply_markup=sms_countries_keyboard(COUNTRIES),
    )
    await state.set_state(SMSStates.country)
    await callback.answer()


@router.callback_query(SMSStates.country, F.data.startswith("sms_country:"))
async def sms_country_selected(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":")[1]
    prefix = get_country_prefix(code)
    await state.update_data(country_code=code, prefix=prefix)
    await safe_edit_text(
        callback.message,
        f"📱 <b>SMS-рассылка</b>\n\n"
        f"Выбрана страна: {prefix}\n\n"
        f"Шаг 2. Введите номер телефона в формате <code>{prefix}xxxxxxx</code>\n"
        f"(только цифры после кода страны):",
    )
    await state.set_state(SMSStates.phone)
    await callback.answer()


@router.message(SMSStates.phone)
async def sms_phone_entered(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    prefix = data.get("prefix", "")
    phone_input = message.text.strip()

    if not phone_input.startswith("+"):
        phone_input = prefix + phone_input.lstrip("0")

    digits = phone_input.lstrip("+").replace(" ", "").replace("-", "")
    if not digits.isdigit() or len(digits) < MIN_PHONE_DIGITS:
        await message.answer(
            f"❌ Неверный формат. Введите номер в формате <code>{prefix}xxxxxxx</code>:",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(phone=phone_input)
    await message.answer(
        "📱 <b>SMS-рассылка</b>\n\n"
        f"Шаг 3. Введите имя отправителя (не более {MAX_SENDER_LENGTH} символов):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(SMSStates.sender)


@router.message(SMSStates.sender)
async def sms_sender_entered(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    sender = message.text.strip()
    if len(sender) > MAX_SENDER_LENGTH:
        await message.answer(
            f"❌ Имя отправителя не может быть длиннее {MAX_SENDER_LENGTH} символов. Попробуйте снова:",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(sender=sender)
    await message.answer(
        "📱 <b>SMS-рассылка</b>\n\n"
        f"Шаг 4. Введите текст сообщения (не более {MAX_SMS_LENGTH} символов):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(SMSStates.message)


@router.message(SMSStates.message)
async def sms_message_entered(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    text = message.text.strip()
    if len(text) > MAX_SMS_LENGTH:
        await message.answer(
            f"❌ Сообщение слишком длинное ({len(text)} симв.). Максимум {MAX_SMS_LENGTH} символов:",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()
    phone = data["phone"]
    sender = data["sender"]
    await state.clear()

    api_key = os.getenv("SMSSEND_API_KEY", "")
    status_msg = await message.answer("⏳ Отправка SMS...")

    result = await send_sms(api_key=api_key, phone=phone, message=text, sender=sender)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:modules"))

    if result["success"]:
        status_text = (
            f"✅ <b>SMS отправлено!</b>\n\n"
            f"📞 Номер: <code>{phone}</code>\n"
            f"👤 Отправитель: <code>{sender}</code>\n"
            f"📋 Статус: {result['status']}\n"
            f"🆔 ID: {result.get('message_id') or '—'}"
        )
    else:
        error_detail = result.get("error") or result.get("status", "—")
        status_text = (
            f"❌ <b>Ошибка отправки SMS</b>\n\n"
            f"📞 Номер: <code>{phone}</code>\n"
            f"📋 Причина: {error_detail}"
        )

    await status_msg.edit_text(
        status_text, reply_markup=builder.as_markup(), parse_mode="HTML"
    )
