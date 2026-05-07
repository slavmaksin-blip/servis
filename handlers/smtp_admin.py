"""Admin handler for the /smtp command.

The /smtp command opens an admin panel where administrators can:
  1. Change the active SMTP credentials.
  2. Configure the sender name and subject prefix for each preset template.

Changes are persisted to disk and take effect immediately without a restart.
"""
import logging

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import ADMIN_IDS
import smtp_settings
import template_settings
from smtp_settings import SmtpConfig, apply as smtp_apply
from template_settings import (
    TemplateConfig,
    TEMPLATE_IDS,
    TEMPLATE_LABELS,
    apply as tpl_apply,
)
from utils.states import SmtpStates, TemplateAdminStates

log = logging.getLogger(__name__)
router = Router()


# ──────────────────────────────── access guard ───────────────────────────────

def _is_admin(user_id: int) -> bool:
    return bool(ADMIN_IDS) and user_id in ADMIN_IDS


# ──────────────────────────────── keyboards ──────────────────────────────────

def _admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Изменить SMTP", callback_data="smtp_edit")],
            [
                InlineKeyboardButton(text="📝 Ricardo 2.0", callback_data="smtp_tpl_ricardo"),
                InlineKeyboardButton(text="📝 PostFinance 2.0", callback_data="smtp_tpl_postfinance"),
            ],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="smtp_cancel")],
        ]
    )


def _ssl_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔒 SSL/TLS (порт 465)", callback_data="smtp_ssl_yes"),
                InlineKeyboardButton(text="🔓 STARTTLS (порт 587)", callback_data="smtp_ssl_no"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="smtp_cancel")],
        ]
    )


def _confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Применить", callback_data="smtp_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="smtp_cancel"),
            ]
        ]
    )


def _tpl_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="smtp_tpl_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="smtp_cancel"),
            ]
        ]
    )


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="smtp_cancel")]
        ]
    )


# ──────────────────────────────── helpers ────────────────────────────────────

def _admin_panel_text() -> str:
    cfg = smtp_settings.current
    mode = "SSL/TLS (порт 465)" if cfg.use_ssl else "STARTTLS (порт 587)"
    lines = [
        "⚙️ <b>Панель администратора</b>\n",
        "<b>SMTP:</b>",
        f"  🌐 Сервер: <code>{cfg.host}:{cfg.port}</code> ({mode})",
        f"  👤 Пользователь: <code>{cfg.user}</code>",
        "",
        "<b>Настройки шаблонов:</b>",
    ]
    for tid in TEMPLATE_IDS:
        tc = template_settings.current[tid]
        label = TEMPLATE_LABELS[tid]
        sname = f"<code>{tc.sender_name}</code>" if tc.sender_name else "<i>не задано</i>"
        subj = f"<code>{tc.subject}#XXXX</code>" if tc.subject else "<i>не задано</i>"
        lines.append(f"  <b>{label}</b>: {sname} / {subj}")
    return "\n".join(lines)


def _smtp_summary(data: dict) -> str:
    use_ssl = data.get("use_ssl", True)
    mode = "SSL/TLS (порт 465)" if use_ssl else "STARTTLS (порт 587)"
    return (
        f"🌐 Сервер: <code>{data['host']}</code>\n"
        f"🔌 Порт: <code>{data['port']}</code>\n"
        f"🔒 Шифрование: {mode}\n"
        f"👤 Пользователь: <code>{data['user']}</code>\n"
        f"🔑 Пароль: <code>{'*' * len(data['password'])}</code>"
    )


# ──────────────────────────────── /smtp entry ────────────────────────────────

@router.message(Command("smtp"))
async def cmd_smtp(message: types.Message, state: FSMContext) -> None:
    if not ADMIN_IDS:
        log.warning(
            "ADMIN_IDS is not configured — /smtp command is disabled for all users"
        )
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    await state.clear()
    await message.answer(
        _admin_panel_text(),
        parse_mode="HTML",
        reply_markup=_admin_panel_kb(),
    )


# ──────────────────────────────── SMTP wizard ────────────────────────────────

@router.callback_query(F.data == "smtp_edit")
async def cb_smtp_edit(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    cfg = smtp_settings.current
    mode = "SSL/TLS (порт 465)" if cfg.use_ssl else "STARTTLS (порт 587)"
    await callback.message.edit_text(
        f"⚙️ <b>Изменение SMTP</b>\n\n"
        f"Текущий сервер: <code>{cfg.host}:{cfg.port}</code> ({mode})\n\n"
        "Введите новый <b>SMTP-сервер</b> (например: <code>smtp.mail.ch</code>):",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await state.set_state(SmtpStates.host)
    await callback.answer()


@router.message(SmtpStates.host)
async def msg_smtp_host(message: types.Message, state: FSMContext) -> None:
    host = message.text.strip() if message.text else ""
    if not host:
        await message.answer("⚠️ Введите адрес сервера:", reply_markup=_cancel_kb())
        return
    await state.update_data(host=host)
    await state.set_state(SmtpStates.port)
    await message.answer(
        "Введите <b>порт</b> (например: <code>465</code> или <code>587</code>):",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )


@router.message(SmtpStates.port)
async def msg_smtp_port(message: types.Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else ""
    if not text.isdigit() or not (1 <= int(text) <= 65535):
        await message.answer(
            "⚠️ Порт должен быть числом от 1 до 65535:",
            reply_markup=_cancel_kb(),
        )
        return
    await state.update_data(port=int(text))
    await state.set_state(SmtpStates.use_ssl)
    await message.answer(
        "Выберите <b>режим шифрования</b>:",
        parse_mode="HTML",
        reply_markup=_ssl_choice_kb(),
    )


@router.callback_query(SmtpStates.use_ssl, F.data.in_({"smtp_ssl_yes", "smtp_ssl_no"}))
async def cb_smtp_ssl(callback: types.CallbackQuery, state: FSMContext) -> None:
    use_ssl = callback.data == "smtp_ssl_yes"
    await state.update_data(use_ssl=use_ssl)
    await state.set_state(SmtpStates.user)
    await callback.message.edit_text(
        "Введите <b>логин (email) SMTP-пользователя</b>:",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


@router.message(SmtpStates.user)
async def msg_smtp_user(message: types.Message, state: FSMContext) -> None:
    user = message.text.strip() if message.text else ""
    if not user:
        await message.answer("⚠️ Введите логин:", reply_markup=_cancel_kb())
        return
    await state.update_data(user=user)
    await state.set_state(SmtpStates.password)
    await message.answer(
        "Введите <b>пароль SMTP</b>:",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )


@router.message(SmtpStates.password)
async def msg_smtp_password(message: types.Message, state: FSMContext) -> None:
    password = message.text.strip() if message.text else ""
    if not password:
        await message.answer("⚠️ Введите пароль:", reply_markup=_cancel_kb())
        return
    # Delete the message immediately to keep the password out of chat history.
    try:
        await message.delete()
    except Exception:
        pass
    await state.update_data(password=password)
    data = await state.get_data()
    await state.set_state(SmtpStates.confirm)
    await message.answer(
        f"📋 <b>Проверьте новые настройки SMTP:</b>\n\n{_smtp_summary(data)}\n\n"
        "Применить?",
        parse_mode="HTML",
        reply_markup=_confirm_kb(),
    )


@router.callback_query(SmtpStates.confirm, F.data == "smtp_confirm")
async def cb_smtp_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    new_cfg = SmtpConfig(
        host=data["host"],
        port=data["port"],
        user=data["user"],
        password=data["password"],
        use_ssl=data["use_ssl"],
    )
    smtp_apply(new_cfg)

    mode = "SSL/TLS (порт 465)" if new_cfg.use_ssl else "STARTTLS (порт 587)"
    await callback.message.edit_text(
        f"✅ <b>Настройки SMTP обновлены!</b>\n\n"
        f"🌐 Сервер: <code>{new_cfg.host}</code>\n"
        f"🔌 Порт: <code>{new_cfg.port}</code>\n"
        f"🔒 Шифрование: {mode}\n"
        f"👤 Пользователь: <code>{new_cfg.user}</code>",
        parse_mode="HTML",
        reply_markup=_admin_panel_kb(),
    )
    await callback.answer()


# ──────────────────────────────── Template settings wizard ───────────────────

@router.callback_query(F.data.in_({"smtp_tpl_ricardo", "smtp_tpl_postfinance"}))
async def cb_smtp_tpl(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    template_id = "ricardo" if callback.data == "smtp_tpl_ricardo" else "postfinance"
    label = TEMPLATE_LABELS[template_id]
    tc = template_settings.current[template_id]
    await state.update_data(template_id=template_id)
    await state.set_state(TemplateAdminStates.sender_name)
    await callback.message.edit_text(
        f"📝 <b>Настройки шаблона {label}</b>\n\n"
        f"Текущий отправитель: <code>{tc.sender_name or '—'}</code>\n"
        f"Текущая тема: <code>{(tc.subject + '#XXXX') if tc.subject else '—'}</code>\n\n"
        "Введите новое <b>имя отправителя</b>:",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


@router.message(TemplateAdminStates.sender_name)
async def msg_tpl_sender_name(message: types.Message, state: FSMContext) -> None:
    name = message.text.strip() if message.text else ""
    if not name:
        await message.answer("⚠️ Введите имя отправителя:", reply_markup=_cancel_kb())
        return
    await state.update_data(sender_name=name)
    await state.set_state(TemplateAdminStates.subject)
    await message.answer(
        "Введите <b>тему сообщения</b>\n"
        "<i>(суффикс #XXXX добавится автоматически для защиты от спама)</i>:",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )


@router.message(TemplateAdminStates.subject)
async def msg_tpl_subject(message: types.Message, state: FSMContext) -> None:
    subject = message.text.strip() if message.text else ""
    if not subject:
        await message.answer("⚠️ Введите тему:", reply_markup=_cancel_kb())
        return
    await state.update_data(subject=subject)
    data = await state.get_data()
    label = TEMPLATE_LABELS[data["template_id"]]
    await state.set_state(TemplateAdminStates.confirm)
    await message.answer(
        f"📋 <b>Настройки шаблона {label}:</b>\n\n"
        f"👤 Отправитель: <code>{data['sender_name']}</code>\n"
        f"📌 Тема: <code>{data['subject']}#XXXX</code>\n\n"
        "Сохранить?",
        parse_mode="HTML",
        reply_markup=_tpl_confirm_kb(),
    )


@router.callback_query(TemplateAdminStates.confirm, F.data == "smtp_tpl_confirm")
async def cb_tpl_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    tid = data["template_id"]
    new_cfg = TemplateConfig(
        sender_name=data["sender_name"],
        subject=data["subject"],
    )
    tpl_apply(tid, new_cfg)

    label = TEMPLATE_LABELS[tid]
    await callback.message.edit_text(
        f"✅ <b>Настройки шаблона {label} сохранены!</b>\n\n"
        f"👤 Отправитель: <code>{new_cfg.sender_name}</code>\n"
        f"📌 Тема: <code>{new_cfg.subject}#XXXX</code>",
        parse_mode="HTML",
        reply_markup=_admin_panel_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "smtp_cancel")
async def cb_smtp_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Изменение отменено.")
    await callback.answer()
