import time
import logging

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID, SUBSCRIPTION_PRICES, CRYPTOBOT_TOKEN, XROCKET_TOKEN
from utils.keyboards import (
    profile_kb,
    payment_kb,
    subscription_kb,
    cancel_kb,
    back_kb,
)
from utils.states import ProfileModule
from utils.validators import validate_amount, validate_promo_code

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "my_profile")
async def cb_my_profile(callback: types.CallbackQuery) -> None:
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Профиль не найден.", show_alert=True)
        return

    now = int(time.time())
    sub_until = user["subscription_until"]
    if sub_until > now:
        remaining = sub_until - now
        days = remaining // 86400
        hours = (remaining % 86400) // 3600
        sub_text = f"✅ Активна (ещё {days}д {hours}ч)"
    else:
        sub_text = "❌ Нет подписки"

    await callback.message.edit_text(
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{user['telegram_id']}</code>\n"
        f"👤 Username: @{callback.from_user.username or '—'}\n"
        f"💰 Баланс: <b>${user['balance']:.2f}</b>\n"
        f"⭐ Подписка: {sub_text}",
        parse_mode="HTML",
        reply_markup=profile_kb(),
    )


@router.callback_query(F.data == "topup_balance")
async def cb_topup_balance(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "💳 <b>Пополнение баланса</b>\n\nВыберите способ оплаты:",
        parse_mode="HTML",
        reply_markup=payment_kb(),
    )
    await state.set_state(ProfileModule.choose_payment)


@router.callback_query(
    ProfileModule.choose_payment,
    F.data.in_({"pay_cryptobot", "pay_xrocket"}),
)
async def cb_choose_payment(callback: types.CallbackQuery, state: FSMContext) -> None:
    method = callback.data
    await state.update_data(payment_method=method)
    await callback.message.edit_text(
        "💵 Введите сумму пополнения в USD (минимум 1):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(ProfileModule.enter_amount)


@router.message(ProfileModule.enter_amount)
async def msg_enter_amount(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    ok, err = validate_amount(message.text.strip())
    if not ok:
        await message.answer(f"❌ {err}\n\nВведите сумму ещё раз:", reply_markup=cancel_kb())
        return

    amount = float(message.text.strip())
    data = await state.get_data()
    method = data["payment_method"]

    method_name = "CryptoBot" if method == "pay_cryptobot" else "xRocket"
    token = CRYPTOBOT_TOKEN if method == "pay_cryptobot" else XROCKET_TOKEN

    await state.clear()

    if not token:
        await message.answer(
            f"⚠️ Платёжный метод <b>{method_name}</b> не настроен.\n"
            "Обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=back_kb("profile"),
        )
        return

    await db.update_balance(message.from_user.id, amount)
    await db.add_transaction(
        message.from_user.id, amount, "topup", f"via {method_name}"
    )

    await message.answer(
        f"✅ Баланс пополнен на <b>${amount:.2f}</b> через {method_name}.\n\n"
        f"(В реальном боте здесь будет ссылка на оплату через {method_name} API)",
        parse_mode="HTML",
        reply_markup=back_kb("profile"),
    )


@router.callback_query(F.data == "buy_subscription")
async def cb_buy_subscription(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "⭐ <b>Подписка</b>\n\nВыберите тариф:",
        parse_mode="HTML",
        reply_markup=subscription_kb(SUBSCRIPTION_PRICES),
    )
    await state.set_state(ProfileModule.choose_subscription)


@router.callback_query(ProfileModule.choose_subscription, F.data.startswith("sub:"))
async def cb_choose_subscription(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
    days = int(callback.data.split(":")[1])
    price = SUBSCRIPTION_PRICES.get(days)
    if price is None:
        await callback.answer("Тариф не найден.", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка пользователя.", show_alert=True)
        await state.clear()
        return

    if user["balance"] < price:
        await callback.answer(
            f"❌ Недостаточно средств! Нужно: ${price:.2f}, у вас: ${user['balance']:.2f}",
            show_alert=True,
        )
        return

    now = int(time.time())
    current_until = max(user["subscription_until"], now)
    new_until = current_until + days * 86400

    await db.update_balance(callback.from_user.id, -price)
    await db.set_subscription(callback.from_user.id, new_until)
    await db.add_transaction(
        callback.from_user.id, -price, "subscription", f"{days}d"
    )
    await state.clear()

    await callback.message.edit_text(
        f"✅ Подписка активирована на <b>{days} дней</b>!\n"
        f"💵 Списано: ${price:.2f}",
        parse_mode="HTML",
        reply_markup=back_kb("profile"),
    )


@router.callback_query(F.data == "promo_code")
async def cb_promo_code(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "🎁 Введите промокод:",
        reply_markup=cancel_kb(),
    )
    await state.set_state(ProfileModule.enter_promo)


@router.message(ProfileModule.enter_promo)
async def msg_promo_code(message: types.Message, state: FSMContext) -> None:
    code = message.text.strip()
    ok, err = validate_promo_code(code)
    if not ok:
        await message.answer(f"❌ {err}", reply_markup=cancel_kb())
        return

    promo = await db.get_promo_code(code)
    if not promo:
        await message.answer(
            "❌ Промокод не найден или уже использован.",
            reply_markup=back_kb("profile"),
        )
        await state.clear()
        return

    amount = promo["amount"]
    await db.use_promo_code(code)
    await db.update_balance(message.from_user.id, amount)
    await db.add_transaction(message.from_user.id, amount, "promo", code)
    await state.clear()

    await message.answer(
        f"✅ Промокод активирован!\n💰 Начислено: <b>${amount:.2f}</b>",
        parse_mode="HTML",
        reply_markup=back_kb("profile"),
    )
