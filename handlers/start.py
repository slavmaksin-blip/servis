import os
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from database.db import get_user, create_user
from utils.keyboards import main_menu_keyboard, subscription_keyboard

logger = logging.getLogger(__name__)
router = Router()


def _start_photo_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "start.png")


async def check_channel_subscription(bot: Bot, user_id: int, channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status not in ("left", "kicked", "banned", "restricted")
    except Exception:
        return False


async def send_main_menu(message: Message) -> None:
    photo_path = _start_photo_path()
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await message.answer_photo(
            photo=photo,
            caption="🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    await create_user(user_id, username, first_name)
    user = await get_user(user_id)

    if user and user.get("is_banned"):
        await message.answer("🚫 Вы заблокированы в этом боте.")
        return

    channel_id = os.getenv("CHANNEL_ID", "")
    is_subscribed = await check_channel_subscription(bot, user_id, channel_id)

    if not is_subscribed and channel_id:
        await message.answer(
            "📢 <b>Для использования бота необходимо подписаться на наш канал!</b>\n\n"
            "После подписки нажмите кнопку «Проверить подписку».",
            reply_markup=subscription_keyboard(channel_id),
            parse_mode="HTML",
        )
        await notify_admin_new_user(bot, user_id, username, first_name, subscribed=False)
        return

    await notify_admin_new_user(bot, user_id, username, first_name, subscribed=True)
    await send_main_menu(message)


@router.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot) -> None:
    user_id = callback.from_user.id
    channel_id = os.getenv("CHANNEL_ID", "")
    is_subscribed = await check_channel_subscription(bot, user_id, channel_id)

    if is_subscribed:
        await callback.message.delete()
        await send_main_menu(callback.message)
        await callback.answer("✅ Подписка подтверждена!")
    else:
        await callback.answer("❌ Вы ещё не подписались на канал.", show_alert=True)


@router.callback_query(F.data == "menu:back")
async def back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    photo_path = _start_photo_path()
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        try:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo,
                caption="🏠 <b>Главное меню</b>\n\nВыберите раздел:",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML",
            )
        except Exception:
            await callback.message.edit_text(
                "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML",
            )
    else:
        try:
            await callback.message.edit_text(
                "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML",
            )
        except Exception:
            await callback.message.answer(
                "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML",
            )
    await callback.answer()


async def notify_admin_new_user(
    bot: Bot, user_id: int, username: str, first_name: str, subscribed: bool
) -> None:
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        return
    try:
        status = "✅ подписан на канал" if subscribed else "❌ не подписан на канал"
        mention = f"@{username}" if username else first_name or str(user_id)
        await bot.send_message(
            int(admin_id),
            f"👤 <b>Новый пользователь!</b>\n\n"
            f"ID: <code>{user_id}</code>\n"
            f"Имя: {first_name or '—'}\n"
            f"Username: {mention}\n"
            f"Статус: {status}",
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("Cannot notify admin: %s", exc)
