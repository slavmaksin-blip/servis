"""
Start & help handlers.
"""

import logging

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

import database as db
from utils.keyboards import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = db.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
    )
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "Я — многофункциональный бот. Выберите раздел в меню ниже:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Помощь</b>\n\n"
        "📱 <b>SMS модуль</b> — отправка SMS через SMSSend API\n"
        "📧 <b>Магазин почты</b> — заказ временных email через AnyMessage Shop\n"
        "👤 <b>Профиль</b> — баланс и история операций\n\n"
        "По любым вопросам обращайтесь к администратору.",
        parse_mode="HTML",
    )


@router.message(lambda m: m.text == "ℹ️ Помощь")
async def btn_help(message: Message) -> None:
    await cmd_help(message)