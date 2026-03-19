from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

import database
from utils.keyboards import main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await database.create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "Добро пожаловать в MultiTool & Shop бот.\n"
        "Выберите раздел из меню ниже:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
