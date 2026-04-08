"""Telegram bot — Mensor Partner API client.

Commands:
  /start   — welcome / help
  /ping    — check API health
  /sms     — send an SMS
  /mail    — send an email
  /screen  — generate a bank screenshot (PNG)
  /pdf     — generate a promo PDF (Ricardo / Post)
"""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

import api as mensor

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# ---------------------------------------------------------------------------
# FSM state groups
# ---------------------------------------------------------------------------


class SmsStates(StatesGroup):
    phone = State()
    text = State()
    sender = State()


class MailStates(StatesGroup):
    recipient = State()
    subject = State()
    sender_name = State()
    html_body = State()


class ScreenStates(StatesGroup):
    country = State()
    platform = State()
    service_name = State()
    amount = State()


class PdfStates(StatesGroup):
    template = State()
    lang = State()
    buyer_name = State()
    delivery = State()
    product_name = State()
    amount = State()
    link = State()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CANCEL_KB = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
)

SKIP_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ]
)


def country_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇨🇭 Швейцария (CHF)", callback_data="country:ch"),
                InlineKeyboardButton(text="🇩🇪 Германия (EUR)", callback_data="country:de"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )


def platform_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏦 Bank", callback_data="platform:bank"),
                InlineKeyboardButton(text="📋 Full tranz", callback_data="platform:full_tranz"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )


def template_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Ricardo", callback_data="template:ricardo"),
                InlineKeyboardButton(text="📮 Post", callback_data="template:post"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang:de"),
                InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang:fr"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 <b>Mensor Partner Bot</b>\n\n"
        "Доступные команды:\n"
        "• /ping — проверить доступность API\n"
        "• /sms — отправить SMS\n"
        "• /mail — отправить Email\n"
        "• /screen — сгенерировать скриншот банка (PNG)\n"
        "• /pdf — сгенерировать PDF-документ (Ricardo / Post)",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# /ping
# ---------------------------------------------------------------------------


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    try:
        data = await mensor.ping()
        if data.get("ok"):
            await message.answer(
                f"✅ API доступен\n"
                f"Сервис: <b>{data.get('service')}</b>\n"
                f"Версия: {data.get('version')}",
                parse_mode="HTML",
            )
        else:
            await message.answer("⚠️ API вернул неожиданный ответ.")
    except Exception as exc:
        await message.answer(f"❌ Ошибка соединения: {exc}")


# ---------------------------------------------------------------------------
# Cancel handler (global)
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")  # type: ignore[union-attr]
    await callback.answer()


# ---------------------------------------------------------------------------
# SMS flow
# ---------------------------------------------------------------------------


@router.message(Command("sms"))
async def cmd_sms(message: Message, state: FSMContext) -> None:
    await state.set_state(SmsStates.phone)
    await message.answer(
        "📱 <b>Отправка SMS</b>\n\nВведите номер телефона получателя (с кодом страны, напр. <code>+41791234567</code>):",
        parse_mode="HTML",
        reply_markup=CANCEL_KB,
    )


@router.message(StateFilter(SmsStates.phone))
async def sms_phone(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if not phone.startswith("+"):
        await message.answer("⚠️ Номер должен начинаться с «+». Попробуйте ещё раз:")
        return
    await state.update_data(phone=phone)
    await state.set_state(SmsStates.text)
    await message.answer(
        "✏️ Введите текст SMS (максимум 150 символов):",
        reply_markup=CANCEL_KB,
    )


@router.message(StateFilter(SmsStates.text))
async def sms_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) > 150:
        await message.answer("⚠️ Текст слишком длинный (максимум 150 символов). Попробуйте ещё раз:")
        return
    await state.update_data(text=text)
    await state.set_state(SmsStates.sender)
    await message.answer(
        "🏷 Введите имя отправителя (максимум 12 символов) или нажмите «Пропустить»:",
        reply_markup=SKIP_KB,
    )


@router.callback_query(StateFilter(SmsStates.sender), F.data == "skip")
async def sms_sender_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _do_send_sms(callback.message, state, sender="")  # type: ignore[arg-type]


@router.message(StateFilter(SmsStates.sender))
async def sms_sender(message: Message, state: FSMContext) -> None:
    sender = (message.text or "").strip()
    if len(sender) > 12:
        await message.answer("⚠️ Имя отправителя не должно превышать 12 символов. Попробуйте ещё раз:")
        return
    await _do_send_sms(message, state, sender=sender)


async def _do_send_sms(message: Message, state: FSMContext, sender: str) -> None:
    data = await state.get_data()
    await state.clear()
    wait = await message.answer("⏳ Отправляю SMS…")
    try:
        result = await mensor.send_sms(data["phone"], data["text"], sender)
    except Exception as exc:
        await wait.edit_text(f"❌ Ошибка соединения с API: {exc}")
        return
    if result.get("ok"):
        await wait.edit_text(
            f"✅ SMS отправлено!\nID: <code>{result.get('sms_id', 'n/a')}</code>",
            parse_mode="HTML",
        )
    else:
        await wait.edit_text(f"❌ Ошибка: {result.get('error', 'unknown')}")


# ---------------------------------------------------------------------------
# Mail flow
# ---------------------------------------------------------------------------


@router.message(Command("mail"))
async def cmd_mail(message: Message, state: FSMContext) -> None:
    await state.set_state(MailStates.recipient)
    await message.answer(
        "📧 <b>Отправка Email</b>\n\nВведите адрес получателя:",
        parse_mode="HTML",
        reply_markup=CANCEL_KB,
    )


@router.message(StateFilter(MailStates.recipient))
async def mail_recipient(message: Message, state: FSMContext) -> None:
    recipient = (message.text or "").strip()
    if "@" not in recipient:
        await message.answer("⚠️ Некорректный email. Попробуйте ещё раз:")
        return
    await state.update_data(recipient=recipient)
    await state.set_state(MailStates.subject)
    await message.answer("✏️ Введите тему письма:", reply_markup=CANCEL_KB)


@router.message(StateFilter(MailStates.subject))
async def mail_subject(message: Message, state: FSMContext) -> None:
    await state.update_data(subject=(message.text or "").strip())
    await state.set_state(MailStates.sender_name)
    await message.answer("🏷 Введите имя отправителя (отображается в письме):", reply_markup=CANCEL_KB)


@router.message(StateFilter(MailStates.sender_name))
async def mail_sender_name(message: Message, state: FSMContext) -> None:
    await state.update_data(sender_name=(message.text or "").strip())
    await state.set_state(MailStates.html_body)
    await message.answer(
        "📝 Введите HTML-содержимое письма\n(например: <code>&lt;h1&gt;Привет!&lt;/h1&gt;&lt;p&gt;Текст.&lt;/p&gt;</code>):",
        parse_mode="HTML",
        reply_markup=CANCEL_KB,
    )


@router.message(StateFilter(MailStates.html_body))
async def mail_html_body(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    html_body = (message.text or "").strip()
    await state.clear()
    wait = await message.answer("⏳ Отправляю письмо…")
    try:
        result = await mensor.send_email(
            data["recipient"],
            data["subject"],
            data["sender_name"],
            html_body,
        )
    except Exception as exc:
        await wait.edit_text(f"❌ Ошибка соединения с API: {exc}")
        return
    if result.get("ok"):
        await wait.edit_text(f"✅ Письмо успешно отправлено на <code>{data['recipient']}</code>!", parse_mode="HTML")
    else:
        await wait.edit_text(f"❌ Ошибка: {result.get('error', 'unknown')}")


# ---------------------------------------------------------------------------
# Screen flow
# ---------------------------------------------------------------------------


@router.message(Command("screen"))
async def cmd_screen(message: Message, state: FSMContext) -> None:
    await state.set_state(ScreenStates.country)
    await message.answer(
        "🖼 <b>Генерация скриншота банка</b>\n\nВыберите страну:",
        parse_mode="HTML",
        reply_markup=country_kb(),
    )


@router.callback_query(StateFilter(ScreenStates.country), F.data.startswith("country:"))
async def screen_country(callback: CallbackQuery, state: FSMContext) -> None:
    country = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(country=country)
    await state.set_state(ScreenStates.platform)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "📋 Выберите тип скриншота:",
        reply_markup=platform_kb(),
    )
    await callback.answer()


@router.callback_query(StateFilter(ScreenStates.platform), F.data.startswith("platform:"))
async def screen_platform(callback: CallbackQuery, state: FSMContext) -> None:
    platform = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(platform=platform)
    await state.set_state(ScreenStates.service_name)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🏷 Введите название сервиса (максимум 40 символов, напр. «Netflix»):",
        reply_markup=CANCEL_KB,
    )
    await callback.answer()


@router.message(StateFilter(ScreenStates.service_name))
async def screen_service_name(message: Message, state: FSMContext) -> None:
    service_name = (message.text or "").strip()
    if len(service_name) > 40:
        await message.answer("⚠️ Название не должно превышать 40 символов. Попробуйте ещё раз:")
        return
    await state.update_data(service_name=service_name)
    await state.set_state(ScreenStates.amount)
    await message.answer("💰 Введите сумму списания (напр. <code>12.99</code>):", parse_mode="HTML", reply_markup=CANCEL_KB)


@router.message(StateFilter(ScreenStates.amount))
async def screen_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = float((message.text or "").strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите корректное положительное число (напр. 12.99):")
        return
    data = await state.get_data()
    await state.clear()
    wait = await message.answer("⏳ Генерирую скриншот…")
    try:
        image_bytes, error = await mensor.generate_screen(
            data["country"], data["platform"], data["service_name"], amount
        )
    except Exception as exc:
        await wait.edit_text(f"❌ Ошибка соединения с API: {exc}")
        return
    if image_bytes:
        await wait.delete()
        await message.answer_photo(
            BufferedInputFile(image_bytes, filename="screen.png"),
            caption="✅ Скриншот готов",
        )
    else:
        await wait.edit_text(f"❌ Ошибка: {error}")


# ---------------------------------------------------------------------------
# PDF flow
# ---------------------------------------------------------------------------


@router.message(Command("pdf"))
async def cmd_pdf(message: Message, state: FSMContext) -> None:
    await state.set_state(PdfStates.template)
    await message.answer(
        "📄 <b>Генерация PDF-документа</b>\n\nВыберите шаблон:",
        parse_mode="HTML",
        reply_markup=template_kb(),
    )


@router.callback_query(StateFilter(PdfStates.template), F.data.startswith("template:"))
async def pdf_template(callback: CallbackQuery, state: FSMContext) -> None:
    template = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(template=template)
    await state.set_state(PdfStates.lang)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🌐 Выберите язык документа:",
        reply_markup=lang_kb(),
    )
    await callback.answer()


@router.callback_query(StateFilter(PdfStates.lang), F.data.startswith("lang:"))
async def pdf_lang(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(lang=lang)
    await state.set_state(PdfStates.buyer_name)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "👤 Введите имя покупателя (максимум 80 символов):",
        reply_markup=CANCEL_KB,
    )
    await callback.answer()


@router.message(StateFilter(PdfStates.buyer_name))
async def pdf_buyer_name(message: Message, state: FSMContext) -> None:
    buyer_name = (message.text or "").strip()
    if len(buyer_name) > 80:
        await message.answer("⚠️ Имя не должно превышать 80 символов. Попробуйте ещё раз:")
        return
    await state.update_data(buyer_name=buyer_name)
    await state.set_state(PdfStates.delivery)
    await message.answer(
        "🚚 Введите способ доставки / оплаты (напр. «A-Post» или «Envoi prioritaire»):",
        reply_markup=CANCEL_KB,
    )


@router.message(StateFilter(PdfStates.delivery))
async def pdf_delivery(message: Message, state: FSMContext) -> None:
    await state.update_data(delivery=(message.text or "").strip())
    await state.set_state(PdfStates.product_name)
    await message.answer("📦 Введите название товара (максимум 80 символов):", reply_markup=CANCEL_KB)


@router.message(StateFilter(PdfStates.product_name))
async def pdf_product_name(message: Message, state: FSMContext) -> None:
    product_name = (message.text or "").strip()
    if len(product_name) > 80:
        await message.answer("⚠️ Название товара не должно превышать 80 символов. Попробуйте ещё раз:")
        return
    await state.update_data(product_name=product_name)
    await state.set_state(PdfStates.amount)
    await message.answer(
        "💰 Введите сумму в CHF (напр. <code>1299.00</code>):",
        parse_mode="HTML",
        reply_markup=CANCEL_KB,
    )


@router.message(StateFilter(PdfStates.amount))
async def pdf_amount(message: Message, state: FSMContext) -> None:
    amount_str = (message.text or "").strip().replace(",", ".")
    try:
        float(amount_str)
    except ValueError:
        await message.answer("⚠️ Введите корректное число (напр. 1299.00):")
        return
    await state.update_data(amount=amount_str)
    await state.set_state(PdfStates.link)
    await message.answer(
        "🔗 Введите ссылку на оплату (напр. <code>https://pay.example.com/invoice/abc</code>):",
        parse_mode="HTML",
        reply_markup=CANCEL_KB,
    )


@router.message(StateFilter(PdfStates.link))
async def pdf_link(message: Message, state: FSMContext) -> None:
    link = (message.text or "").strip()
    data = await state.get_data()
    await state.clear()
    wait = await message.answer("⏳ Генерирую PDF…")
    try:
        pdf_bytes, error, filename = await mensor.generate_pdf(
            data["template"],
            data["lang"],
            data["buyer_name"],
            data["delivery"],
            data["product_name"],
            data["amount"],
            link,
        )
    except Exception as exc:
        await wait.edit_text(f"❌ Ошибка соединения с API: {exc}")
        return
    if pdf_bytes:
        await wait.delete()
        await message.answer_document(
            BufferedInputFile(pdf_bytes, filename=filename or "document.pdf"),
            caption="✅ PDF готов",
        )
    else:
        await wait.edit_text(f"❌ Ошибка: {error}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill in the values.")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logger.info("Bot is starting…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
