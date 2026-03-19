"""
Admin panel handler.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import ADMIN_IDS
from utils.keyboards import admin_keyboard
from utils.states import AdminStates

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@router.message(Command("admin"))
async def admin_menu(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    await message.answer(
        "🛠 <b>Админ-панель</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Users list
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    await callback.answer()

    users = db.get_all_users()
    if not users:
        await callback.message.edit_text("Нет зарегистрированных пользователей.")
        return

    lines = [f"👥 <b>Пользователи ({len(users)}):</b>\n"]
    for u in users[:20]:
        lines.append(
            f"• {u['full_name']} (@{u['username']}) — "
            f"ID: <code>{u['tg_id']}</code> — 💰 {u['balance']:.4f}$"
        )
    if len(users) > 20:
        lines.append(f"\n…и ещё {len(users) - 20} пользователей.")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Top-up user balance
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_topup")
async def admin_topup_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "Введите Telegram ID пользователя, которому хотите пополнить баланс:"
    )
    await state.set_state(AdminStates.waiting_for_user_id)


@router.message(AdminStates.waiting_for_user_id)
async def admin_topup_user_id(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    text = message.text.strip() if message.text else ""
    if not text.isdigit():
        await message.answer("❌ Введите числовой Telegram ID.")
        return
    user_id = int(text)
    user = db.get_user(user_id)
    if not user:
        await message.answer(f"❌ Пользователь с ID {user_id} не найден.")
        await state.clear()
        return
    await state.update_data(target_user_id=user_id)
    await message.answer(
        f"✅ Пользователь: {user['full_name']} (@{user['username']})\n"
        f"Текущий баланс: {user['balance']:.4f}$\n\n"
        "Введите сумму пополнения (например: 5.00):"
    )
    await state.set_state(AdminStates.waiting_for_amount)


@router.message(AdminStates.waiting_for_amount)
async def admin_topup_amount(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    text = message.text.strip().replace(",", ".") if message.text else ""
    try:
        amount = float(text)
    except ValueError:
        await message.answer("❌ Введите корректную сумму (число).")
        return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть положительной.")
        return

    data = await state.get_data()
    target_id: int = data["target_user_id"]
    new_balance = db.update_balance(
        tg_id=target_id,
        delta=amount,
        description=f"Пополнение администратором ({message.from_user.id})",
    )
    await message.answer(
        f"✅ Баланс пользователя <code>{target_id}</code> пополнен на <b>{amount:.4f}$</b>.\n"
        f"Новый баланс: <b>{new_balance:.4f}$</b>",
        parse_mode="HTML",
    )
    await state.clear()


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text("📣 Введите текст для рассылки всем пользователям:")
    await state.set_state(AdminStates.waiting_for_broadcast)


@router.message(AdminStates.waiting_for_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    text = message.text or message.caption or ""
    if not text:
        await message.answer("❌ Текст рассылки не может быть пустым.")
        return

    users = db.get_all_users()
    sent = 0
    failed = 0
    bot = message.bot
    for user in users:
        try:
            await bot.send_message(user["tg_id"], f"📣 <b>Рассылка:</b>\n\n{text}", parse_mode="HTML")
            sent += 1
        except Exception as exc:
            logger.warning("Broadcast failed for %s: %s", user["tg_id"], exc)
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена.\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )
    await state.clear()


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    await callback.answer()

    users = db.get_all_users()
    total_users = len(users)
    total_balance = sum(u["balance"] for u in users)

    await callback.message.edit_text(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💰 Суммарный баланс: ${total_balance:.4f}",
        parse_mode="HTML",
    )
