"""Admin handler for the /smtp command.

Allows bot administrators (listed in ADMIN_IDS env var) to change the active
SMTP configuration at runtime without restarting the bot.  The new settings
are written to ``smtp_override.json`` and take effect immediately.
"""
import logging

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import ADMIN_IDS
import smtp_settings
from smtp_settings import SmtpConfig, apply as smtp_apply
from utils.states import SmtpStates

log = logging.getLogger(__name__)
router = Router()


# ──────────────────────────────── keyboards ──────────────────────────────────

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


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="smtp_cancel")]
        ]
    )


# ──────────────────────────────── helpers ────────────────────────────────────

def _summary(data: dict) -> str:
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
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    cfg = smtp_settings.current
    mode = "SSL/TLS (порт 465)" if cfg.use_ssl else "STARTTLS (порт 587)"
    await message.answer(
        f"⚙️ <b>Текущие настройки SMTP:</b>\n"
        f"🌐 Сервер: <code>{cfg.host}</code>\n"
        f"🔌 Порт: <code>{cfg.port}</code>\n"
        f"🔒 Шифрование: {mode}\n"
        f"👤 Пользователь: <code>{cfg.user}</code>\n\n"
        "Введите новый <b>SMTP-сервер</b> (например: <code>smtp.mail.ch</code>):",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await state.set_state(SmtpStates.host)


# ──────────────────────────────── wizard steps ───────────────────────────────

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
        f"📋 <b>Проверьте новые настройки SMTP:</b>\n\n{_summary(data)}\n\n"
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
    )
    await callback.answer()


@router.callback_query(F.data == "smtp_cancel")
async def cb_smtp_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Изменение SMTP отменено.")
    await callback.answer()
