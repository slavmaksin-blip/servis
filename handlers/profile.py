"""
Profile handler — balance and transaction history.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import database as db
from utils.keyboards import profile_keyboard

router = Router()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@router.message(F.text == "👤 Профиль")
async def profile_menu(message: Message) -> None:
    user = db.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
    )
    balance: float = user["balance"]
    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"💰 Баланс: <b>${balance:.4f}</b>",
        reply_markup=profile_keyboard(),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Top-up notice
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "profile_topup")
async def profile_topup(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "💰 <b>Пополнение баланса</b>\n\n"
        "Для пополнения свяжитесь с администратором.",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Transaction history
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "profile_history")
async def profile_history(callback: CallbackQuery) -> None:
    await callback.answer()
    transactions = db.get_transaction_history(callback.from_user.id, limit=10)

    if not transactions:
        await callback.message.edit_text("📊 История операций пуста.")
        return

    lines = ["📊 <b>История операций (последние 10):</b>\n"]
    for tx in transactions:
        sign = "+" if tx["amount"] >= 0 else ""
        lines.append(
            f"• {tx['created_at'][:16]}  {sign}{tx['amount']:.4f}$"
            + (f"  — {tx['description']}" if tx["description"] else "")
        )
    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
    )