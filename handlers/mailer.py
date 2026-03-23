import re
import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext

import smtp_settings
from utils.keyboards import cancel_kb, main_menu_kb
from utils.states import MailerStates

router = Router()

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ──────────────────────────────── helpers ────────────────────────────────────

def _send_email_sync(
    sender_name: str,
    recipient: str,
    subject: str,
    html_body: str,
) -> None:
    """Blocking SMTP call — runs in a thread-pool executor."""
    cfg = smtp_settings.current  # always read the live singleton

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender_name} <{cfg.user}>"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    ctx = ssl.create_default_context()
    if cfg.use_ssl:
        # Implicit SSL/TLS (e.g. port 465)
        with smtplib.SMTP_SSL(cfg.host, cfg.port, context=ctx, timeout=30) as smtp:
            smtp.login(cfg.user, cfg.password)
            smtp.sendmail(cfg.user, recipient, msg.as_string())
    else:
        # Opportunistic STARTTLS (e.g. port 587)
        with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as smtp:
            smtp.ehlo()
            if smtp.has_extn("STARTTLS"):
                smtp.starttls(context=ctx)
                smtp.ehlo()
            smtp.login(cfg.user, cfg.password)
            smtp.sendmail(cfg.user, recipient, msg.as_string())


async def _send_email(
    sender_name: str,
    recipient: str,
    subject: str,
    html_body: str,
) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, _send_email_sync, sender_name, recipient, subject, html_body
    )


# ──────────────────────────────── handlers ───────────────────────────────────

@router.callback_query(F.data == "send_email")
async def cb_send_email(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MailerStates.sender_name)
    await callback.message.edit_text(
        "✉️ <b>Отправка письма</b>\n\nШаг 1/4 — Введите <b>имя отправителя</b>:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(MailerStates.sender_name)
async def msg_sender_name(message: types.Message, state: FSMContext) -> None:
    name = message.text.strip() if message.text else ""
    if not name:
        await message.answer(
            "⚠️ Имя не может быть пустым. Введите имя отправителя:",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(sender_name=name)
    await state.set_state(MailerStates.recipient_email)
    await message.answer(
        "Шаг 2/4 — Введите <b>адрес получателя</b>:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(MailerStates.recipient_email)
async def msg_recipient_email(message: types.Message, state: FSMContext) -> None:
    email = message.text.strip() if message.text else ""
    if not EMAIL_PATTERN.match(email):
        await message.answer(
            "⚠️ Неверный формат email. Введите корректный адрес получателя:",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(recipient_email=email)
    await state.set_state(MailerStates.subject)
    await message.answer(
        "Шаг 3/4 — Введите <b>тему письма</b>:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(MailerStates.subject)
async def msg_subject(message: types.Message, state: FSMContext) -> None:
    subject = message.text.strip() if message.text else ""
    if not subject:
        await message.answer(
            "⚠️ Тема не может быть пустой. Введите тему письма:",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(subject=subject)
    await state.set_state(MailerStates.template)
    await message.answer(
        "Шаг 4/4 — Загрузите <b>шаблон письма в формате TXT</b>:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(MailerStates.template, F.document)
async def msg_template(message: types.Message, state: FSMContext, bot: Bot) -> None:
    doc = message.document
    if not (doc.file_name or "").lower().endswith(".txt"):
        await message.answer(
            "⚠️ Пожалуйста, загрузите файл в формате <b>.txt</b>.",
            parse_mode="HTML",
            reply_markup=cancel_kb(),
        )
        return

    # Download file content
    file = await bot.get_file(doc.file_id)
    downloaded = await bot.download_file(file.file_path)
    html_body = downloaded.read().decode("utf-8", errors="replace")

    data = await state.get_data()
    sender_name: str = data["sender_name"]
    recipient: str = data["recipient_email"]
    subject: str = data["subject"]

    await state.clear()

    status_msg = await message.answer("⏳ Отправляем письмо…")
    try:
        await _send_email(sender_name, recipient, subject, html_body)
        await status_msg.edit_text(
            f"✅ Письмо успешно отправлено!\n\n"
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


@router.message(MailerStates.template)
async def msg_template_wrong(message: types.Message) -> None:
    await message.answer(
        "⚠️ Пожалуйста, загрузите файл в формате <b>.txt</b>.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено. Выберите действие:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
