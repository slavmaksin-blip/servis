import os
import logging
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID
from states.states import ProfileStates
from utils.keyboards import (
    profile_kb, payment_system_kb, check_payment_kb,
    subscription_plans_kb, cancel_kb, back_to_main_kb,
)
from utils.api import (
    cryptobot_create_invoice, cryptobot_check_invoice,
    xrocket_create_invoice, xrocket_check_invoice,
)

router = Router()

START_IMAGE = "start.png"
logger = logging.getLogger(__name__)

SUBSCRIPTION_PLANS = {
    "sub_1": (1, 6.0, "1 день"),
    "sub_3": (3, 12.0, "3 дня"),
    "sub_15": (15, 28.0, "15 дней"),
}


def _sub_status(user: dict) -> str:
    sub_end = user.get("sub_end")
    if not sub_end:
        return "❌ Нет подписки"
    try:
        end_dt = datetime.fromisoformat(sub_end)
        if end_dt <= datetime.now():
            return "❌ Истекла"
        delta = end_dt - datetime.now()
        days = delta.days
        hours = delta.seconds // 3600
        return f"✅ Активна (осталось {days}д {hours}ч)"
    except Exception as exc:
        logger.warning("Failed to parse sub_end '%s': %s", sub_end, exc)
        return "❌ Нет подписки"


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    username = callback.from_user.username or "—"
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{callback.from_user.id}</code>\n"
        f"👤 Username: @{username}\n"
        f"📊 Статус подписки: {_sub_status(user)}\n"
        f"💰 Баланс: <code>{user['balance']}$</code>"
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
            reply_markup=profile_kb(),
            parse_mode="HTML",
        )
    else:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=profile_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


# ─────────────────────── TOP UP ───────────────────────

@router.callback_query(F.data == "topup")
async def topup_select_system(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileStates.payment_system)
    await callback.message.answer(
        "💰 <b>Пополнение баланса</b>\n\nВыберите платёжную систему:",
        reply_markup=payment_system_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.in_({"pay_cryptobot", "pay_xrocket"}), ProfileStates.payment_system)
async def topup_enter_amount(callback: CallbackQuery, state: FSMContext) -> None:
    system = "cryptobot" if callback.data == "pay_cryptobot" else "xrocket"
    await state.update_data(payment_system=system)
    await state.set_state(ProfileStates.amount)
    await callback.message.answer(
        "💵 Введите сумму пополнения в USD (минимум 1$):",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(ProfileStates.amount)
async def topup_create_invoice(message: Message, state: FSMContext) -> None:
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount < 1:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❌ Введите корректную сумму (минимум 1$):", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    system = data["payment_system"]
    await state.set_state(ProfileStates.checking)

    if system == "cryptobot":
        result = await cryptobot_create_invoice(amount)
        if not result.get("ok"):
            err = result.get("error", "Неизвестная ошибка")
            await message.answer(f"❌ Ошибка создания счёта: {err}", reply_markup=back_to_main_kb())
            await state.clear()
            return
        invoice_data = result["result"]
        invoice_id = str(invoice_data["invoice_id"])
        pay_url = invoice_data.get("pay_url", "")
        await db.create_invoice(message.from_user.id, invoice_id, amount, "cryptobot")
        await state.update_data(invoice_id=invoice_id)
        await message.answer(
            f"💳 <b>Счёт создан!</b>\n\n"
            f"💰 Сумма: <code>{amount}$</code>\n"
            f"🔗 <a href='{pay_url}'>Оплатить через CryptoBot</a>\n\n"
            f"После оплаты нажмите «Проверить оплату».",
            reply_markup=check_payment_kb(invoice_id, "cryptobot"),
            parse_mode="HTML",
        )
    else:
        result = await xrocket_create_invoice(amount)
        if not result.get("success"):
            err = result.get("error", "Неизвестная ошибка")
            await message.answer(f"❌ Ошибка создания счёта: {err}", reply_markup=back_to_main_kb())
            await state.clear()
            return
        invoice_data = result["data"]
        invoice_id = str(invoice_data["id"])
        pay_url = invoice_data.get("link", "")
        await db.create_invoice(message.from_user.id, invoice_id, amount, "xrocket")
        await state.update_data(invoice_id=invoice_id)
        await message.answer(
            f"💳 <b>Счёт создан!</b>\n\n"
            f"💰 Сумма: <code>{amount}$</code>\n"
            f"🔗 <a href='{pay_url}'>Оплатить через xRocket</a>\n\n"
            f"После оплаты нажмите «Проверить оплату».",
            reply_markup=check_payment_kb(invoice_id, "xrocket"),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("check_pay:"))
async def check_payment(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    system = parts[1]
    invoice_id = parts[2]

    invoice = await db.get_invoice(invoice_id)
    if not invoice:
        await callback.answer("❌ Счёт не найден.", show_alert=True)
        return

    # Double-credit guard
    if invoice["credited"]:
        await callback.answer("✅ Этот счёт уже был зачислен.", show_alert=True)
        return

    is_paid = False
    if system == "cryptobot":
        result = await cryptobot_check_invoice(invoice_id)
        if result.get("ok"):
            items = result.get("result", {}).get("items", [])
            if items and items[0].get("status") == "paid":
                is_paid = True
    else:
        result = await xrocket_check_invoice(invoice_id)
        if result.get("success"):
            data = result.get("data", {})
            if data.get("status") == "paid":
                is_paid = True

    if not is_paid:
        await callback.answer("⏳ Оплата ещё не подтверждена. Попробуйте позже.", show_alert=True)
        return

    # Mark as credited (strict double-credit protection)
    marked = await db.mark_invoice_credited(invoice_id)
    if not marked:
        await callback.answer("✅ Этот счёт уже был зачислен ранее.", show_alert=True)
        return

    amount = invoice["amount"]
    await db.update_balance(callback.from_user.id, amount)
    await state.clear()

    await callback.message.answer(
        f"✅ <b>Баланс пополнен!</b>\n💰 +{amount}$",
        reply_markup=back_to_main_kb(),
        parse_mode="HTML",
    )

    if ADMIN_ID:
        try:
            uname = callback.from_user.username or str(callback.from_user.id)
            await callback.bot.send_message(
                ADMIN_ID,
                f"💰 Пополнение: @{uname}, ID: {callback.from_user.id}, Сумма: {amount}$",
            )
        except Exception:
            pass
    await callback.answer()


# ─────────────────────── SUBSCRIPTION ───────────────────────

@router.callback_query(F.data == "buy_sub")
async def buy_subscription(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "💎 <b>Купить подписку</b>\n\nВыберите тариф:",
        reply_markup=subscription_plans_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.in_({"sub_1", "sub_3", "sub_15"}))
async def process_subscription(callback: CallbackQuery) -> None:
    plan_key = callback.data
    days, price, label = SUBSCRIPTION_PLANS[plan_key]

    user = await db.get_user(callback.from_user.id)
    if not user or user["balance"] < price:
        await callback.answer(
            f"❌ Недостаточно средств. Нужно {price}$, у вас {user['balance'] if user else 0}$.",
            show_alert=True,
        )
        return

    await db.update_balance(callback.from_user.id, -price)

    # Extend existing subscription or set new
    now = datetime.now()
    try:
        current_end = datetime.fromisoformat(user["sub_end"]) if user.get("sub_end") else now
        base = max(current_end, now)
    except Exception as exc:
        logger.warning("Failed to parse sub_end for extension '%s': %s", user.get("sub_end"), exc)
        base = now
    new_end = base + timedelta(days=days)
    await db.set_subscription(callback.from_user.id, new_end.isoformat())

    await callback.message.answer(
        f"✅ <b>Подписка активирована!</b>\n"
        f"💎 Тариф: {label}\n"
        f"📅 Действует до: {new_end.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=back_to_main_kb(),
        parse_mode="HTML",
    )

    if ADMIN_ID:
        try:
            uname = callback.from_user.username or str(callback.from_user.id)
            await callback.bot.send_message(
                ADMIN_ID,
                f"💎 Куплена подписка: @{uname}, тариф {label}",
            )
        except Exception:
            pass
    await callback.answer()


# ─────────────────────── PROMO ───────────────────────

@router.callback_query(F.data == "promo")
async def promo_enter(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileStates.promo)
    await callback.message.answer(
        "🎁 Введите промокод:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(ProfileStates.promo)
async def promo_activate(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    promo = await db.get_promo(code)
    if not promo:
        await message.answer("❌ Промокод не найден или недействителен.", reply_markup=cancel_kb())
        return

    activated = await db.activate_promo(message.from_user.id, promo["id"])
    if not activated:
        await message.answer("❌ Вы уже использовали этот промокод.", reply_markup=cancel_kb())
        return

    amount = promo["amount"]
    await db.update_balance(message.from_user.id, amount)
    await state.clear()

    await message.answer(
        f"✅ <b>Промокод активирован!</b>\n💰 Начислено: {amount}$",
        reply_markup=back_to_main_kb(),
        parse_mode="HTML",
    )
