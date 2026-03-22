from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from app.keyboards import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Это бот для шуточных скринов (розыгрыш).\n\n"
        "Выбери действие:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(lambda c: c.data == "menu:back")
async def back_to_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu_kb(),
    )
    await call.answer()
