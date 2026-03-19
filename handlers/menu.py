from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import Database

router = Router()
db = Database()


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(
        "📋 <b>Главное меню</b>\n\n"
        "Выберите нужный раздел:\n"
        "• /modules — Модули\n"
        "• /shop — Магазин\n"
        "• /profile — Профиль\n"
        "• /admin — Администрирование",
    )
