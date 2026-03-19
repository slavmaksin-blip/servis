from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

router = Router()


@router.message(Command("modules"))
async def cmd_modules(message: Message):
    await message.answer(
        "🔧 <b>Модули</b>\n\n"
        "Доступные модули:\n"
        "• SMS — отправка SMS\n"
        "• Email — работа с почтой",
    )
