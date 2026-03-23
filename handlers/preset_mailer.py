"""Preset template mailer — sends Ricardo 2.0 or PostFinance 2.0 emails.

The user picks a template, enters the recipient email, product price,
delivery method and a (possibly shortened) payment link.  The bot reads the
corresponding TXT file from the PDF/ folder, substitutes the placeholders,
and sends the result via the currently active SMTP configuration.
"""
from __future__ import annotations

import random
import smtplib

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

import template_settings
from template_settings import TEMPLATE_FILES, TEMPLATE_LABELS
from utils.keyboards import cancel_kb, main_menu_kb, preset_template_kb
from utils.send import send_email
from utils.states import PresetMailerStates
from utils.validators import EMAIL_PATTERN

router = Router()

_PLACEHOLDER_LINK = "HTTPLINK.TT"
_PLACEHOLDER_PRICE = "111000111"
_PLACEHOLDER_DELIVERY = "DOSTAVKA"


# ──────────────────────────────── helpers ────────────────────────────────────

def _build_subject(base: str) -> str:
    """Append anti-spam suffix #XXXX to the subject."""
    suffix = "".join(str(random.randint(0, 9)) for _ in range(4))
    return f"{base}#{suffix}"


def _build_body(template_id: str, price: str, delivery: str, link: str) -> str:
    """Read the TXT template and replace all placeholders."""
    tpl_path = TEMPLATE_FILES[template_id]
    body = tpl_path.read_text(encoding="utf-8", errors="replace")
    body = body.replace(_PLACEHOLDER_LINK, link)
    body = body.replace(_PLACEHOLDER_PRICE, price)
    body = body.replace(_PLACEHOLDER_DELIVERY, delivery)
    return body


# ──────────────────────────────── entry ──────────────────────────────────────

@router.callback_query(F.data == "preset_email")
async def cb_preset_email(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "📋 <b>Общий шаблон</b>\n\nВыберите шаблон письма:",
        parse_mode="HTML",
        reply_markup=preset_template_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.in_({"preset_ricardo", "preset_postfinance"}))
async def cb_choose_template(callback: types.CallbackQuery, state: FSMContext) -> None:
    template_id = "ricardo" if callback.data == "preset_ricardo" else "postfinance"
    label = TEMPLATE_LABELS[template_id]
    cfg = template_settings.current[template_id]

    if not cfg.sender_name or not cfg.subject:
        await callback.message.edit_text(
            f"⚠️ Настройки для шаблона <b>{label}</b> ещё не заданы администратором.\n"
            "Попросите администратора настроить их через /smtp.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await state.update_data(template_id=template_id)
    await state.set_state(PresetMailerStates.recipient_email)
    await callback.message.edit_text(
        f"🧾 <b>{label}</b>\n\n"
        "Шаг 1/4 — Введите <b>email получателя</b>:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


# ──────────────────────────────── wizard steps ───────────────────────────────

@router.message(PresetMailerStates.recipient_email)
async def msg_preset_recipient(message: types.Message, state: FSMContext) -> None:
    email = message.text.strip() if message.text else ""
    if not EMAIL_PATTERN.match(email):
        await message.answer(
            "⚠️ Неверный формат email. Введите корректный адрес получателя:",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(recipient_email=email)
    await state.set_state(PresetMailerStates.price)
    await message.answer(
        "Шаг 2/4 — Введите <b>цену товара</b> (например: <code>199.90</code>):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(PresetMailerStates.price)
async def msg_preset_price(message: types.Message, state: FSMContext) -> None:
    price = message.text.strip() if message.text else ""
    if not price:
        await message.answer("⚠️ Введите цену товара:", reply_markup=cancel_kb())
        return
    await state.update_data(price=price)
    await state.set_state(PresetMailerStates.delivery)
    await message.answer(
        "Шаг 3/4 — Введите <b>способ доставки</b>:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(PresetMailerStates.delivery)
async def msg_preset_delivery(message: types.Message, state: FSMContext) -> None:
    delivery = message.text.strip() if message.text else ""
    if not delivery:
        await message.answer("⚠️ Введите способ доставки:", reply_markup=cancel_kb())
        return
    await state.update_data(delivery=delivery)
    await state.set_state(PresetMailerStates.link)
    await message.answer(
        "Шаг 4/4 — Введите <b>ссылку для оплаты</b>\n"
        "<i>(используйте сокращатор, если домен не чистый)</i>:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(PresetMailerStates.link)
async def msg_preset_link(message: types.Message, state: FSMContext) -> None:
    link = message.text.strip() if message.text else ""
    if not link:
        await message.answer("⚠️ Введите ссылку:", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    template_id: str = data["template_id"]
    recipient: str = data["recipient_email"]
    price: str = data["price"]
    delivery: str = data["delivery"]

    await state.clear()

    cfg = template_settings.current[template_id]
    sender_name = cfg.sender_name
    subject = _build_subject(cfg.subject)

    try:
        html_body = _build_body(template_id, price, delivery, link)
    except OSError as exc:
        await message.answer(
            f"❌ Не удалось прочитать файл шаблона: {exc}",
            reply_markup=main_menu_kb(),
        )
        return

    label = TEMPLATE_LABELS[template_id]
    status_msg = await message.answer("⏳ Отправляем письмо…")
    try:
        await send_email(sender_name, recipient, subject, html_body)
        await status_msg.edit_text(
            f"✅ Письмо успешно отправлено!\n\n"
            f"🧾 Шаблон: {label}\n"
            f"👤 Отправитель: {sender_name}\n"
            f"📬 Получатель: {recipient}\n"
            f"📌 Тема: {subject}",
            reply_markup=main_menu_kb(),
        )
    except smtplib.SMTPAuthenticationError:
        await status_msg.edit_text(
            "❌ Ошибка аутентификации SMTP. Проверьте учётные данные.",
            reply_markup=main_menu_kb(),
        )
    except smtplib.SMTPRecipientsRefused:
        await status_msg.edit_text(
            "❌ Адрес получателя отклонён сервером. Проверьте email получателя.",
            reply_markup=main_menu_kb(),
        )
    except smtplib.SMTPException as exc:
        await status_msg.edit_text(
            f"❌ Ошибка SMTP при отправке письма: {exc}",
            reply_markup=main_menu_kb(),
        )
    except OSError as exc:
        await status_msg.edit_text(
            f"❌ Ошибка сети при подключении к SMTP: {exc}",
            reply_markup=main_menu_kb(),
        )
