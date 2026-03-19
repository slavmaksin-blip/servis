from aiogram import Router, F
from aiogram.types import CallbackQuery

import database
from utils.keyboards import back_keyboard

router = Router()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery) -> None:
    user = await database.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Профиль не найден.", show_alert=True)
        return

    balance = user.get("balance", 0.0)
    username = f"@{user['username']}" if user.get("username") else "не задан"
    await callback.message.edit_text(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user['telegram_id']}</code>\n"
        f"👤 Username: {username}\n"
        f"📛 Имя: {user['full_name']}\n"
        f"💰 Баланс: {balance:.2f}₽\n"
        f"📅 Регистрация: {user['registered_at']}",
        reply_markup=back_keyboard("back_main"),
        parse_mode="HTML",
    )
    await callback.answer()
