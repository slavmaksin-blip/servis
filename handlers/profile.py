import os
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from database.db import (
    get_user,
    update_user_balance,
    update_user_sub,
    get_promo,
    use_promo,
    has_used_promo,
    delete_promo,
)
from handlers.states import ProfileStates
from utils.keyboards import (
    profile_keyboard,
    topup_keyboard,
    sub_plans_keyboard,
    cancel_keyboard,
    main_menu_keyboard,
    SUB_PRICES,
)
from utils.cryptobot import create_cryptobot_invoice, create_xrocket_invoice

logger = logging.getLogger(__name__)
router = Router()


def _start_photo_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "start.png")


def _sub_remaining(sub_end) -> str:
    if not sub_end:
        return "❌ Нет подписки"
    if isinstance(sub_end, str):
        try:
            sub_end = datetime.fromisoformat(sub_end)
        except ValueError:
            return "❌ Нет подписки"
    if sub_end <= datetime.now():
        return "❌ Истекла"
    delta = sub_end - datetime.now()
    days = delta.days
    hours = delta.seconds // 3600
    return f"✅ {days} дн. {hours} ч."


@router.callback_query(F.data == "menu:profile")
async def show_profile(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    tg_user = callback.from_user
    username = f"@{tg_user.username}" if tg_user.username else "—"
    sub_info = _sub_remaining(user.get("sub_end"))

    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{tg_user.id}</code>\n"
        f"👤 Username: {username}\n"
        f"⏳ Подписка: {sub_info}\n"
        f"💰 Баланс: <b>${user['balance']:.2f}</b>"
    )

    photo_path = _start_photo_path()
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        try:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=profile_keyboard(),
                parse_mode="HTML",
            )
        except Exception:
            await callback.message.answer(text, reply_markup=profile_keyboard(), parse_mode="HTML")
    else:
        try:
            await callback.message.edit_text(text, reply_markup=profile_keyboard(), parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=profile_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "profile:cancel")
async def profile_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_profile(callback)


# ─── TOP UP BALANCE ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile:topup")
async def topup_menu(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "💰 <b>Пополнение баланса</b>\n\nВыберите способ оплаты:",
        reply_markup=topup_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "topup:cryptobot")
async def topup_cryptobot(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(topup_method="cryptobot")
    await callback.message.edit_text(
        "💰 <b>Пополнение через CryptoBot</b>\n\nВведите сумму в USD:",
        parse_mode="HTML",
    )
    await state.set_state(ProfileStates.topup_amount)
    await callback.answer()


@router.callback_query(F.data == "topup:xrocket")
async def topup_xrocket(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(topup_method="xrocket")
    await callback.message.edit_text(
        "🚀 <b>Пополнение через xRocket</b>\n\nВведите сумму в USD:",
        parse_mode="HTML",
    )
    await state.set_state(ProfileStates.topup_amount)
    await callback.answer()


@router.message(ProfileStates.topup_amount)
async def topup_amount_entered(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введите корректную сумму (например: 5.00):",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()
    method = data.get("topup_method", "cryptobot")
    await state.clear()

    user_id = message.from_user.id
    description = f"Пополнение баланса бота на ${amount:.2f}"

    if method == "cryptobot":
        token = os.getenv("CRYPTOBOT_TOKEN", "")
        pay_url = await create_cryptobot_invoice(token, amount, description, str(user_id))
        # payload = str(user_id) links the invoice to the user for manual verification
        # (auto-crediting requires a webhook; implement separately if needed)
        service = "CryptoBot"
    else:
        token = os.getenv("XROCKET_TOKEN", "")
        pay_url = await create_xrocket_invoice(token, amount, description)
        service = "xRocket"

    if pay_url:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=f"💳 Оплатить через {service}", url=pay_url))
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:profile"))

        await message.answer(
            f"💰 <b>Счёт создан!</b>\n\n"
            f"Сумма: <b>${amount:.2f}</b>\n"
            f"Сервис: {service}\n\n"
            f"Нажмите кнопку для оплаты:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )

        admin_id = os.getenv("ADMIN_ID")
        if admin_id:
            try:
                u = message.from_user
                mention = f"@{u.username}" if u.username else u.full_name
                await bot.send_message(
                    int(admin_id),
                    f"💰 <b>Запрос на пополнение!</b>\n\n"
                    f"👤 {mention} (<code>{u.id}</code>)\n"
                    f"💵 Сумма: ${amount:.2f}\n"
                    f"📲 Метод: {service}",
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.warning("Cannot notify admin about topup: %s", exc)
    else:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:profile"))
        await message.answer(
            f"❌ Ошибка создания счёта через {service}. Проверьте настройки API.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )


# ─── SUBSCRIPTION ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile:sub")
async def sub_menu(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "⏳ <b>Покупка подписки</b>\n\nВыберите план:",
        reply_markup=sub_plans_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sub:"))
async def buy_subscription(callback: CallbackQuery, bot: Bot) -> None:
    days = int(callback.data.split(":")[1])
    price = SUB_PRICES.get(days)
    if price is None:
        await callback.answer("❌ Неверный план.", show_alert=True)
        return

    user = await get_user(callback.from_user.id)
    if not user or user["balance"] < price:
        await callback.answer(
            f"❌ Недостаточно баланса. Нужно ${price:.2f}, у вас ${user['balance']:.2f}",
            show_alert=True,
        )
        return

    current_sub = user.get("sub_end")
    if current_sub:
        if isinstance(current_sub, str):
            try:
                current_sub = datetime.fromisoformat(current_sub)
            except ValueError:
                current_sub = datetime.now()
        if current_sub < datetime.now():
            current_sub = datetime.now()
    else:
        current_sub = datetime.now()

    new_sub_end = current_sub + timedelta(days=days)
    await update_user_balance(callback.from_user.id, -price)
    await update_user_sub(callback.from_user.id, new_sub_end)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В профиль", callback_data="menu:profile"))

    await callback.message.edit_text(
        f"✅ <b>Подписка активирована!</b>\n\n"
        f"📅 Дней добавлено: {days}\n"
        f"📆 Действует до: {new_sub_end.strftime('%d.%m.%Y %H:%M')}\n"
        f"💸 Списано: <b>${price:.2f}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        try:
            u = callback.from_user
            mention = f"@{u.username}" if u.username else u.full_name
            await bot.send_message(
                int(admin_id),
                f"⏳ <b>Покупка подписки!</b>\n\n"
                f"👤 {mention} (<code>{u.id}</code>)\n"
                f"📅 Дней: {days}\n"
                f"💰 Сумма: ${price:.2f}\n"
                f"📆 До: {new_sub_end.strftime('%d.%m.%Y %H:%M')}",
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Cannot notify admin about subscription: %s", exc)
    await callback.answer()


# ─── PROMO CODE ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile:promo")
async def promo_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "🎁 <b>Промокод</b>\n\nВведите код:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(ProfileStates.promo)
    await callback.answer()


@router.message(ProfileStates.promo)
async def promo_entered(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    code = message.text.strip()
    promo = await get_promo(code)

    if not promo:
        await message.answer(
            "❌ Промокод не найден.",
            reply_markup=cancel_keyboard(),
        )
        return

    user_id = message.from_user.id
    if await has_used_promo(promo["id"], user_id):
        await message.answer(
            "❌ Вы уже использовали этот промокод.",
            reply_markup=cancel_keyboard(),
        )
        return

    if promo["used_count"] >= promo["limit_uses"]:
        await message.answer(
            "❌ Лимит активаций промокода исчерпан.",
            reply_markup=cancel_keyboard(),
        )
        return

    await use_promo(promo["id"], user_id)
    new_balance = await update_user_balance(user_id, promo["amount"])

    if promo["used_count"] + 1 >= promo["limit_uses"]:
        await delete_promo(promo["id"])

    await state.clear()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В профиль", callback_data="menu:profile"))

    await message.answer(
        f"✅ <b>Промокод активирован!</b>\n\n"
        f"💵 Начислено: <b>${promo['amount']:.2f}</b>\n"
        f"💰 Ваш баланс: <b>${new_balance:.2f}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
