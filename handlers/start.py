from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from database import Database

router = Router()
db = Database()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await db.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name or "",
        )

    await message.answer(
        f"👋 Добро пожаловать, {message.from_user.full_name}!\n\n"
        "Используйте меню для навигации по боту."
    )
