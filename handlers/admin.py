import logging

logger = logging.getLogger(__name__)

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database
from config import ADMIN_IDS
from utils.keyboards import admin_keyboard, back_keyboard
from utils.states import AdminStates
from utils.validators import validate_amount

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    await message.answer(
        "⚙️ <b>Панель администратора</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return
    users = await database.get_all_users()
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: {len(users)}",
        reply_markup=back_keyboard("admin_back"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_balance")
async def admin_balance_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return
    await state.set_state(AdminStates.enter_user_id)
    await callback.message.edit_text(
        "💰 Введите Telegram ID пользователя:",
        reply_markup=back_keyboard("admin_back"),
    )
    await callback.answer()


@router.message(AdminStates.enter_user_id)
async def admin_enter_user_id(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат ID.")
        return
    await state.update_data(target_user_id=target_id)
    await state.set_state(AdminStates.enter_amount)
    await message.answer("💵 Введите сумму (может быть отрицательной для списания):")


@router.message(AdminStates.enter_amount)
async def admin_enter_amount(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    amount = validate_amount(message.text)
    if amount is None:
        await message.answer("❌ Неверная сумма.")
        return
    data = await state.get_data()
    await state.clear()
    target_id = data["target_user_id"]
    await database.update_balance(target_id, amount)
    await message.answer(
        f"✅ Баланс пользователя {target_id} изменён на {amount:+.2f}₽"
    )


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return
    await state.set_state(AdminStates.broadcast)
    await callback.message.edit_text(
        "📢 Введите текст рассылки:",
        reply_markup=back_keyboard("admin_back"),
    )
    await callback.answer()


@router.message(AdminStates.broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    users = await database.get_all_users()
    sent, failed = 0, 0
    for user in users:
        try:
            await message.bot.send_message(user["telegram_id"], message.text)
            sent += 1
        except Exception as exc:
            logger.warning("Failed to send broadcast to %s: %s", user["telegram_id"], exc)
            failed += 1
    await message.answer(f"📢 Рассылка завершена.\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")
