import time
import logging

from aiogram import Bot, Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, CHANNEL_ID, CHANNEL_URL
import database as db
from utils.keyboards import check_subscription_kb, main_menu_kb
from utils.states import SubscriptionCheck

router = Router()
logger = logging.getLogger(__name__)


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False


@router.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    existing = await db.get_user(user.id)
    is_new = existing is None
    await db.add_user(user.id, user.username)
    record = await db.get_user(user.id)

    if record and record["is_banned"]:
        await message.answer("🚫 Вы заблокированы в данном боте.")
        return

    subscribed = await is_subscribed(bot, user.id)
    if not subscribed:
        await state.set_state(SubscriptionCheck.waiting)
        await message.answer(
            "👋 Привет! Чтобы использовать бота, подпишитесь на наш канал.",
            reply_markup=check_subscription_kb(CHANNEL_URL),
        )
        return

    await _welcome(message, bot, is_new=is_new)


@router.callback_query(SubscriptionCheck.waiting, F.data == "check_subscription")
async def cb_check_subscription(
    callback: types.CallbackQuery, bot: Bot, state: FSMContext
) -> None:
    subscribed = await is_subscribed(bot, callback.from_user.id)
    if not subscribed:
        await callback.answer("❌ Вы ещё не подписались!", show_alert=True)
        return

    await state.clear()
    await callback.message.delete()
    await _welcome(callback.message, bot, is_new=False, user=callback.from_user)


async def _welcome(
    message: types.Message,
    bot: Bot,
    *,
    is_new: bool = False,
    user: types.User | None = None,
) -> None:
    if user is None:
        user = message.from_user

    if is_new:
        text = (
            f"👋 Добро пожаловать, {user.full_name}!\n\n"
            "Вы успешно зарегистрированы. Выберите раздел:"
        )
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🆕 Новый пользователь:\n"
                f"ID: <code>{user.id}</code>\n"
                f"Username: @{user.username or '—'}\n"
                f"Имя: {user.full_name}",
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Failed to notify admin: %s", exc)
    else:
        text = f"👋 С возвращением, {user.full_name}!\n\nВыберите раздел:"

    await message.answer(text, reply_markup=main_menu_kb())
