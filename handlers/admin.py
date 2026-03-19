from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_IDS
from database import Database

router = Router()
db = Database()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return

    users = await db.get_all_users()
    await message.answer(
        f"⚙️ <b>Администрирование</b>\n\n"
        f"👥 Всего пользователей: <b>{len(users)}</b>",
    )
