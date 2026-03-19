from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from utils.api import SMSSendAPI, MailBuyAPI
from utils.keyboards import back_keyboard, confirm_keyboard, modules_keyboard
from utils.states import SMSStates, MailStates
from utils.validators import validate_phone, sanitize_message

router = Router()

sms_api = SMSSendAPI()
mail_api = MailBuyAPI()


# ── SMS module ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "module_sms")
async def sms_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SMSStates.enter_phone)
    await callback.message.edit_text(
        "📱 <b>SMS рассылка</b>\n\nВведите номер телефона получателя\n"
        "Формат: +79001234567",
        reply_markup=back_keyboard("modules"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SMSStates.enter_phone)
async def sms_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not validate_phone(phone):
        await message.answer(
            "❌ Неверный формат номера. Используйте формат: +79001234567"
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(SMSStates.enter_message)
    await message.answer("✏️ Введите текст сообщения (до 160 символов):")


@router.message(SMSStates.enter_message)
async def sms_message_text(message: Message, state: FSMContext) -> None:
    text = sanitize_message(message.text)
    data = await state.get_data()
    await state.update_data(message=text)
    await state.set_state(SMSStates.confirm)
    await message.answer(
        f"📋 <b>Подтвердите отправку:</b>\n\n"
        f"📞 Номер: {data['phone']}\n"
        f"💬 Сообщение: {text}",
        reply_markup=confirm_keyboard("sms_confirm_yes", "sms_confirm_no"),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "sms_confirm_yes", SMSStates.confirm)
async def sms_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.message.edit_text("⏳ Отправляю SMS...")
    result = await sms_api.send_sms(data["phone"], data["message"])
    if result:
        await callback.message.edit_text(
            "✅ SMS успешно отправлено!",
            reply_markup=back_keyboard("modules"),
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при отправке SMS. Попробуйте позже.",
            reply_markup=back_keyboard("modules"),
        )
    await callback.answer()


@router.callback_query(F.data == "sms_confirm_no", SMSStates.confirm)
async def sms_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "🛠 <b>Модули</b>\n\nВыберите инструмент:",
        reply_markup=modules_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Mail module ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "module_mail")
async def mail_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("⏳ Создаю временный почтовый ящик...")
    mailbox = await mail_api.create_mailbox()
    if not mailbox:
        await callback.message.edit_text(
            "❌ Не удалось создать почтовый ящик. Попробуйте позже.",
            reply_markup=back_keyboard("modules"),
        )
        await callback.answer()
        return

    mailbox_id = mailbox.get("id", "")
    address = mailbox.get("address", "N/A")
    await state.set_state(MailStates.viewing_mailbox)
    await state.update_data(mailbox_id=mailbox_id)
    await callback.message.edit_text(
        f"📧 <b>Ваш временный ящик:</b>\n\n<code>{address}</code>\n\n"
        "Нажмите кнопку ниже, чтобы проверить входящие письма.",
        reply_markup=back_keyboard("modules"),
        parse_mode="HTML",
    )
    await callback.answer()
