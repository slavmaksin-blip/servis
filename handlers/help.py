import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from utils.keyboards import help_kb, back_to_main_kb

router = Router()

START_IMAGE = "start.png"


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text = (
        "❓ <b>Помощь</b>\n\n"
        "Этот бот предоставляет следующие услуги:\n"
        "• 📨 SMS — отправка SMS через SMSSEND API\n"
        "• 📧 Магазин — покупка почтовых аккаунтов и цифровых товаров\n"
        "• 💎 Подписка — доступ к модулям на определённый срок\n"
        "• 💰 Баланс — пополнение через CryptoBot или xRocket\n\n"
        "По всем вопросам обращайтесь в поддержку 👇"
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    if os.path.exists(START_IMAGE):
        photo = FSInputFile(START_IMAGE)
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=photo,
            caption=text,
            reply_markup=help_kb(),
            parse_mode="HTML",
        )
    else:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=help_kb(),
            parse_mode="HTML",
        )
    await callback.answer()
