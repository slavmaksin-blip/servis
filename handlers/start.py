import os

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID, CHANNEL_ID, CHANNEL_USERNAME
from utils.keyboards import main_menu_kb, subscription_kb, back_to_main_kb

router = Router()

START_IMAGE = "start.png"


async def _send_main_menu(bot: Bot, chat_id: int, state: FSMContext | None = None) -> None:
    if state:
        await state.clear()
    text = (
        "👋 <b>Добро пожаловать в Multi-Tool & Shop!</b>\n\n"
        "Выберите раздел:"
    )
    if os.path.exists(START_IMAGE):
        photo = FSInputFile(START_IMAGE)
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=text,
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )


async def _is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await db.get_user(message.from_user.id)
    is_new = user is None
    await db.register_user(
        tg_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
    )

    if CHANNEL_ID and not await _is_subscribed(message.bot, message.from_user.id):
        await message.answer(
            "📢 Для использования бота необходимо подписаться на наш канал.\n"
            "После подписки нажмите «Проверить подписку».",
            reply_markup=subscription_kb(CHANNEL_USERNAME),
        )
        return

    if is_new and ADMIN_ID:
        try:
            await message.bot.send_message(
                ADMIN_ID,
                f"🆕 Новый пользователь: {message.from_user.full_name}, "
                f"ID: {message.from_user.id}",
            )
        except Exception:
            pass

    await _send_main_menu(message.bot, message.chat.id, state)


@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery, state: FSMContext) -> None:
    if CHANNEL_ID and not await _is_subscribed(callback.bot, callback.from_user.id):
        await callback.answer("❌ Вы ещё не подписались на канал!", show_alert=True)
        return

    await callback.message.delete()

    user = await db.get_user(callback.from_user.id)
    is_new = user is None
    await db.register_user(
        tg_id=callback.from_user.id,
        username=callback.from_user.username or "",
        full_name=callback.from_user.full_name or "",
    )

    if is_new and ADMIN_ID:
        try:
            await callback.bot.send_message(
                ADMIN_ID,
                f"🆕 Новый пользователь: {callback.from_user.full_name}, "
                f"ID: {callback.from_user.id}",
            )
        except Exception:
            pass

    await _send_main_menu(callback.bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _send_main_menu(callback.bot, callback.message.chat.id)
    await callback.answer()
