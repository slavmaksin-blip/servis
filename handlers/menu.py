from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from utils.keyboards import main_menu_kb, modules_kb, shop_kb, profile_kb

router = Router()


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню\n\nВыберите раздел:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "modules")
async def cb_modules(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "🔧 Модули\n\nВыберите модуль:",
        reply_markup=modules_kb(),
    )


@router.callback_query(F.data == "shop")
async def cb_shop(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "🛒 Магазин\n\nВыберите раздел:",
        reply_markup=shop_kb(),
    )


@router.callback_query(F.data == "profile")
async def cb_profile_menu(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "👤 Профиль\n\nВыберите раздел:",
        reply_markup=profile_kb(),
    )


@router.callback_query(F.data == "help")
async def cb_help(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "❓ <b>Помощь</b>\n\n"
        "• <b>Модули</b> — SMS-рассылка и другие инструменты\n"
        "• <b>Магазин</b> — покупка почтовых ящиков и товаров\n"
        "• <b>Профиль</b> — баланс, подписка, промокоды\n\n"
        "По всем вопросам обращайтесь к администратору.",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
            ]
        ),
    )
