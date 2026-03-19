from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import Database

router = Router()
db = Database()


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Профиль не найден. Используйте /start для регистрации.")
        return

    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{user['telegram_id']}</code>\n"
        f"👤 Имя: {user['full_name']}\n"
        f"📱 Username: @{user['username'] or 'не указан'}\n"
        f"💰 Баланс: <b>{user['balance']:.2f} руб.</b>",
    )
