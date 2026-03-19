from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import Database

router = Router()
db = Database()


@router.message(Command("shop"))
async def cmd_shop(message: Message):
    user = await db.get_user(message.from_user.id)
    balance = user["balance"] if user else 0.0
    await message.answer(
        f"🛒 <b>Магазин</b>\n\n"
        f"Ваш баланс: <b>{balance:.2f} руб.</b>\n\n"
        "Выберите товар или услугу.",
    )
