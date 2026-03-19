import logging

from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID
from utils.keyboards import admin_kb, cancel_kb, back_kb
from utils.states import AdminModule
from utils.validators import validate_amount

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: types.Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("🚫 Доступ запрещён.")
        return
    await message.answer("🔐 <b>Панель администратора</b>", parse_mode="HTML", reply_markup=admin_kb())


# ── Ban / Unban ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_ban", lambda c: _is_admin(c.from_user.id))
async def cb_admin_ban(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("🔨 Введите ID пользователя для бана:", reply_markup=cancel_kb())
    await state.set_state(AdminModule.ban_user)


@router.message(AdminModule.ban_user)
async def msg_ban_user(message: types.Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID.", reply_markup=cancel_kb())
        return

    await db.ban_user(target_id)
    await state.clear()
    await message.answer(f"✅ Пользователь <code>{target_id}</code> забанен.", parse_mode="HTML", reply_markup=admin_kb())


@router.callback_query(F.data == "admin_unban", lambda c: _is_admin(c.from_user.id))
async def cb_admin_unban(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("🔓 Введите ID пользователя для разбана:", reply_markup=cancel_kb())
    await state.set_state(AdminModule.unban_user)


@router.message(AdminModule.unban_user)
async def msg_unban_user(message: types.Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID.", reply_markup=cancel_kb())
        return

    await db.unban_user(target_id)
    await state.clear()
    await message.answer(f"✅ Пользователь <code>{target_id}</code> разбанен.", parse_mode="HTML", reply_markup=admin_kb())


# ── Broadcast ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast", lambda c: _is_admin(c.from_user.id))
async def cb_admin_broadcast(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "📢 Введите текст рассылки (или отправьте фото с подписью):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AdminModule.broadcast_text)


@router.message(AdminModule.broadcast_text)
async def msg_broadcast(message: types.Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return

    users = await db.get_all_users()
    sent = 0
    failed = 0

    for user in users:
        if user["is_banned"]:
            continue
        try:
            if message.photo:
                await bot.send_photo(
                    user["telegram_id"],
                    message.photo[-1].file_id,
                    caption=message.caption or "",
                )
            else:
                await bot.send_message(user["telegram_id"], message.text or "")
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"📢 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        reply_markup=admin_kb(),
    )


# ── Categories ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_add_category", lambda c: _is_admin(c.from_user.id))
async def cb_admin_add_category(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("📁 Введите название категории:", reply_markup=cancel_kb())
    await state.set_state(AdminModule.add_category)


@router.message(AdminModule.add_category)
async def msg_add_category(message: types.Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    name = message.text.strip()
    await db.add_category(name)
    await state.clear()
    await message.answer(f"✅ Категория «{name}» добавлена.", reply_markup=admin_kb())


# ── Products ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_add_product", lambda c: _is_admin(c.from_user.id))
async def cb_admin_add_product(callback: types.CallbackQuery, state: FSMContext) -> None:
    cats = await db.get_categories()
    if not cats:
        await callback.answer("Сначала создайте категорию.", show_alert=True)
        return

    text = "📦 Введите данные товара в формате:\n<code>category_id|name|description|price|content</code>\n\nКатегории:\n"
    for c in cats:
        text += f"• {c['id']}: {c['name']}\n"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=cancel_kb())
    await state.set_state(AdminModule.add_product)


@router.message(AdminModule.add_product)
async def msg_add_product(message: types.Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.strip().split("|")
    if len(parts) != 5:
        await message.answer("❌ Неверный формат. Попробуйте снова:", reply_markup=cancel_kb())
        return
    try:
        cat_id, name, desc, price_str, content = parts
        price = float(price_str.strip())
        await db.add_product(int(cat_id.strip()), name.strip(), desc.strip(), price, content.strip())
        await state.clear()
        await message.answer(f"✅ Товар «{name.strip()}» добавлен.", reply_markup=admin_kb())
    except Exception as exc:
        await message.answer(f"❌ Ошибка: {exc}", reply_markup=cancel_kb())


# ── Balance management ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_give_balance", lambda c: _is_admin(c.from_user.id))
async def cb_admin_give_balance(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "💰 Введите ID и сумму через пробел (например: 123456789 10.5):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AdminModule.give_balance)


@router.message(AdminModule.give_balance)
async def msg_give_balance(message: types.Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("❌ Неверный формат.", reply_markup=cancel_kb())
        return
    try:
        target_id = int(parts[0])
        amount = float(parts[1])
        await db.update_balance(target_id, amount)
        await db.add_transaction(target_id, amount, "admin_give", "admin")
        await state.clear()
        await message.answer(
            f"✅ Пользователю <code>{target_id}</code> начислено <b>${amount:.2f}</b>.",
            parse_mode="HTML",
            reply_markup=admin_kb(),
        )
    except Exception as exc:
        await message.answer(f"❌ Ошибка: {exc}", reply_markup=cancel_kb())


@router.callback_query(F.data == "admin_take_balance", lambda c: _is_admin(c.from_user.id))
async def cb_admin_take_balance(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "💸 Введите ID и сумму через пробел (например: 123456789 10.5):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AdminModule.take_balance)


@router.message(AdminModule.take_balance)
async def msg_take_balance(message: types.Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("❌ Неверный формат.", reply_markup=cancel_kb())
        return
    try:
        target_id = int(parts[0])
        amount = float(parts[1])
        await db.update_balance(target_id, -amount)
        await db.add_transaction(target_id, -amount, "admin_take", "admin")
        await state.clear()
        await message.answer(
            f"✅ У пользователя <code>{target_id}</code> списано <b>${amount:.2f}</b>.",
            parse_mode="HTML",
            reply_markup=admin_kb(),
        )
    except Exception as exc:
        await message.answer(f"❌ Ошибка: {exc}", reply_markup=cancel_kb())


@router.callback_query(F.data == "admin_list_users", lambda c: _is_admin(c.from_user.id))
async def cb_admin_list_users(callback: types.CallbackQuery) -> None:
    users = await db.get_all_users()
    if not users:
        await callback.answer("Пользователей нет.", show_alert=True)
        return

    text = "👥 <b>Пользователи:</b>\n\n"
    for u in users[:20]:
        text += (
            f"ID: <code>{u['telegram_id']}</code> | "
            f"@{u.get('username') or '—'} | "
            f"${u['balance']:.2f}"
            + (" 🚫" if u["is_banned"] else "")
            + "\n"
        )
    if len(users) > 20:
        text += f"\n…и ещё {len(users) - 20} пользователей."

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("admin_menu"))


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats", lambda c: _is_admin(c.from_user.id))
async def cb_admin_stats(callback: types.CallbackQuery) -> None:
    total = await db.get_user_count()
    subs = await db.get_active_subscription_count()
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"⭐ Активных подписок: <b>{subs}</b>",
        parse_mode="HTML",
        reply_markup=back_kb("admin_menu"),
    )


# ── Promo codes ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_create_promo", lambda c: _is_admin(c.from_user.id))
async def cb_admin_create_promo(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "🎁 Введите промокод, сумму и количество использований через пробел\n"
        "(например: TESTCODE 5.0 10):",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AdminModule.create_promo)


@router.message(AdminModule.create_promo)
async def msg_create_promo(message: types.Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) not in (2, 3):
        await message.answer("❌ Неверный формат.", reply_markup=cancel_kb())
        return
    try:
        code = parts[0].upper()
        amount = float(parts[1])
        uses = int(parts[2]) if len(parts) == 3 else 1
        await db.add_promo_code(code, amount, uses)
        await state.clear()
        await message.answer(
            f"✅ Промокод <b>{code}</b> создан!\n"
            f"💰 Сумма: ${amount:.2f}\n"
            f"🔢 Использований: {uses}",
            parse_mode="HTML",
            reply_markup=admin_kb(),
        )
    except Exception as exc:
        await message.answer(f"❌ Ошибка: {exc}", reply_markup=cancel_kb())


@router.callback_query(F.data == "admin_list_promos", lambda c: _is_admin(c.from_user.id))
async def cb_admin_list_promos(callback: types.CallbackQuery) -> None:
    promos = await db.get_all_promo_codes()
    if not promos:
        await callback.answer("Промокодов нет.", show_alert=True)
        return

    text = "🎁 <b>Промокоды:</b>\n\n"
    for p in promos:
        text += (
            f"<code>{p['code']}</code> | ${p['amount']:.2f} | осталось: {p['uses_left']}\n"
        )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("admin_menu"))


# ── Admin menu callback ────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_menu", lambda c: _is_admin(c.from_user.id))
async def cb_admin_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("🔐 <b>Панель администратора</b>", parse_mode="HTML", reply_markup=admin_kb())


# ── Cancel (admin context) ─────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_admin")
async def cb_cancel_admin(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text("🔐 <b>Панель администратора</b>", parse_mode="HTML", reply_markup=admin_kb())
