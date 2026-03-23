from aiogram import Router, types
from aiogram.filters import CommandStart

from utils.keyboards import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    await message.answer(
        "👋 Привет! Выберите действие:",
        reply_markup=main_menu_kb(),
    )
