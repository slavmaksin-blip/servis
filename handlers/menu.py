from aiogram import Router, F
from aiogram.types import CallbackQuery

from utils.keyboards import main_menu_keyboard, modules_keyboard

router = Router()


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🏠 Главное меню. Выберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "modules")
async def show_modules(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🛠 <b>Модули</b>\n\nВыберите инструмент:",
        reply_markup=modules_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
