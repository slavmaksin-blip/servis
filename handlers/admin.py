import os

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID
from states.states import AdminStates
from utils.keyboards import (
    admin_kb, admin_products_kb, admin_balance_kb,
    back_to_main_kb, cancel_kb,
)

router = Router()

START_IMAGE = "start.png"


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🛠 <b>Панель администратора</b>\n\nВыберите действие:",
        reply_markup=admin_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin")
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.answer(
        "🛠 <b>Панель администратора</b>\n\nВыберите действие:",
        reply_markup=admin_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────── BAN / UNBAN ───────────────────────

@router.callback_query(F.data == "admin_ban")
async def admin_ban_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.ban_input)
    await callback.message.answer(
        "🚫 Введите ID или @username пользователя для бана:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.ban_input)
async def admin_ban_user(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    user = None
    if query.startswith("@"):
        user = await db.get_user_by_username(query)
    else:
        try:
            user = await db.get_user(int(query))
        except ValueError:
            pass

    if not user:
        await message.answer("❌ Пользователь не найден.", reply_markup=cancel_kb())
        return

    await db.ban_user(user["tg_id"])
    await state.clear()
    await message.answer(
        f"✅ Пользователь {user['tg_id']} (@{user.get('username', '—')}) заблокирован.",
        reply_markup=admin_kb(),
    )


@router.callback_query(F.data == "admin_unban")
async def admin_unban_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.unban_input)
    await callback.message.answer(
        "✅ Введите ID или @username для разблокировки:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.unban_input)
async def admin_unban_user(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    user = None
    if query.startswith("@"):
        user = await db.get_user_by_username(query)
    else:
        try:
            user = await db.get_user(int(query))
        except ValueError:
            pass

    if not user:
        await message.answer("❌ Пользователь не найден.", reply_markup=cancel_kb())
        return

    await db.unban_user(user["tg_id"])
    await state.clear()
    await message.answer(
        f"✅ Пользователь {user['tg_id']} (@{user.get('username', '—')}) разблокирован.",
        reply_markup=admin_kb(),
    )


# ─────────────────────── BROADCAST ───────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.answer(
        "📢 Введите текст рассылки (или отправьте фото с подписью):",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.broadcast_text)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot) -> None:
    users = await db.get_all_users()
    success = 0
    fail = 0
    for user in users:
        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=user["tg_id"],
                    photo=message.photo[-1].file_id,
                    caption=message.caption or "",
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=user["tg_id"],
                    text=message.text or "",
                    parse_mode="HTML",
                )
            success += 1
        except Exception:
            fail += 1

    await state.clear()
    await message.answer(
        f"📢 Рассылка завершена!\n✅ Успешно: {success}\n❌ Ошибок: {fail}",
        reply_markup=admin_kb(),
    )


# ─────────────────────── PRODUCTS MANAGEMENT ───────────────────────

@router.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.answer(
        "📦 <b>Управление товарами</b>",
        reply_markup=admin_products_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_category")
async def admin_add_category_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.add_category)
    await callback.message.answer("📂 Введите название категории:", reply_markup=cancel_kb())
    await callback.answer()


@router.message(AdminStates.add_category)
async def admin_add_category_save(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Введите название:", reply_markup=cancel_kb())
        return
    await db.add_category(name)
    await state.clear()
    await message.answer(f"✅ Категория «{name}» добавлена.", reply_markup=admin_products_kb())


@router.callback_query(F.data == "admin_add_product")
async def admin_add_product_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    categories = await db.get_categories()
    if not categories:
        await callback.answer("❌ Сначала создайте категорию.", show_alert=True)
        return

    await state.set_state(AdminStates.select_category_for_product)
    buttons = [[InlineKeyboardButton(
        text=cat["name"], callback_data=f"admin_prod_cat:{cat['id']}"
    )] for cat in categories]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("📂 Выберите категорию для товара:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_cat:"), AdminStates.select_category_for_product)
async def admin_prod_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminStates.add_product_name)
    await callback.message.answer("📝 Введите название товара:", reply_markup=cancel_kb())
    await callback.answer()


@router.message(AdminStates.add_product_name)
async def admin_product_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Введите название:", reply_markup=cancel_kb())
        return
    await state.update_data(product_name=name)
    await state.set_state(AdminStates.add_product_desc)
    await message.answer("📄 Введите описание товара:", reply_markup=cancel_kb())


@router.message(AdminStates.add_product_desc)
async def admin_product_desc(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip()
    await state.update_data(product_desc=desc)
    await state.set_state(AdminStates.add_product_price)
    await message.answer("💰 Введите цену товара в USD:", reply_markup=cancel_kb())


@router.message(AdminStates.add_product_price)
async def admin_product_price(message: Message, state: FSMContext) -> None:
    try:
        price = float((message.text or "").strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную цену:", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    product_id = await db.add_product(
        category_id=data["category_id"],
        name=data["product_name"],
        description=data.get("product_desc", ""),
        price=price,
    )
    await state.update_data(new_product_id=product_id)
    await state.set_state(AdminStates.add_product_files)
    await message.answer(
        f"✅ Товар создан! (ID: {product_id})\n\n"
        "📂 Теперь отправьте файлы для стока (каждый файл — 1 единица товара).\n"
        "Когда закончите, напишите /done",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.add_product_files)
async def admin_product_files(message: Message, state: FSMContext) -> None:
    if message.text and message.text.strip() == "/done":
        data = await state.get_data()
        count = data.get("files_added", 0)
        await state.clear()
        await message.answer(
            f"✅ Загрузка завершена. Добавлено файлов: {count}",
            reply_markup=admin_products_kb(),
        )
        return

    if message.document:
        data = await state.get_data()
        product_id = data.get("new_product_id")
        if product_id:
            await db.add_stock_item(
                product_id=product_id,
                file_id=message.document.file_id,
                file_name=message.document.file_name or "file",
            )
            count = data.get("files_added", 0) + 1
            await state.update_data(files_added=count)
            await message.answer(f"✅ Файл {count} добавлен. Отправьте ещё или напишите /done")
    else:
        await message.answer("❌ Отправьте файл (документ) или напишите /done")


@router.callback_query(F.data == "admin_upload_stock")
async def admin_upload_stock_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    categories = await db.get_categories()
    if not categories:
        await callback.answer("❌ Нет категорий.", show_alert=True)
        return

    products_with_cats = []
    for cat in categories:
        prods = await db.get_products(cat["id"])
        products_with_cats.extend(prods)

    if not products_with_cats:
        await callback.answer("❌ Нет товаров.", show_alert=True)
        return

    await state.set_state(AdminStates.select_product_for_stock)
    buttons = [[InlineKeyboardButton(
        text=p["name"], callback_data=f"admin_stock_prod:{p['id']}"
    )] for p in products_with_cats]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("📦 Выберите товар для загрузки файлов:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_stock_prod:"), AdminStates.select_product_for_stock)
async def admin_stock_product_selected(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[1])
    await state.update_data(new_product_id=product_id, files_added=0)
    await state.set_state(AdminStates.upload_stock_files)
    await callback.message.answer(
        "📂 Отправьте файлы (каждый файл — 1 единица стока). Напишите /done когда закончите.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.upload_stock_files)
async def admin_upload_stock_file(message: Message, state: FSMContext) -> None:
    if message.text and message.text.strip() == "/done":
        data = await state.get_data()
        count = data.get("files_added", 0)
        await state.clear()
        await message.answer(
            f"✅ Загрузка завершена. Добавлено файлов: {count}",
            reply_markup=admin_products_kb(),
        )
        return

    if message.document:
        data = await state.get_data()
        product_id = data.get("new_product_id")
        if product_id:
            await db.add_stock_item(
                product_id=product_id,
                file_id=message.document.file_id,
                file_name=message.document.file_name or "file",
            )
            count = data.get("files_added", 0) + 1
            await state.update_data(files_added=count)
            await message.answer(f"✅ Файл {count} добавлен.")
    else:
        await message.answer("❌ Отправьте файл (документ) или напишите /done")


@router.callback_query(F.data == "admin_delete_product")
async def admin_delete_product_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    categories = await db.get_categories()
    products_all = []
    for cat in categories:
        prods = await db.get_products(cat["id"])
        products_all.extend(prods)

    if not products_all:
        await callback.answer("❌ Нет товаров.", show_alert=True)
        return

    buttons = [[InlineKeyboardButton(
        text=f"🗑 {p['name']}", callback_data=f"admin_del_prod:{p['id']}"
    )] for p in products_all]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_products")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("🗑 Выберите товар для удаления:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_prod:"))
async def admin_delete_product(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return
    await db.delete_product(product_id)
    await callback.answer(f"✅ Товар «{product['name']}» удалён.")
    await callback.message.answer("✅ Товар удалён.", reply_markup=admin_products_kb())


# ─────────────────────── BALANCE MANAGEMENT ───────────────────────

@router.callback_query(F.data == "admin_balance")
async def admin_balance_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.answer(
        "💰 <b>Управление балансом</b>",
        reply_markup=admin_balance_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.in_({"admin_give_balance", "admin_take_balance"}))
async def admin_balance_action(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    action = "give" if callback.data == "admin_give_balance" else "take"
    await state.update_data(balance_action=action)
    await state.set_state(AdminStates.balance_user)
    await callback.message.answer(
        "👤 Введите ID или @username пользователя:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.balance_user)
async def admin_balance_user(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    user = None
    if query.startswith("@"):
        user = await db.get_user_by_username(query)
    else:
        try:
            user = await db.get_user(int(query))
        except ValueError:
            pass

    if not user:
        await message.answer("❌ Пользователь не найден.", reply_markup=cancel_kb())
        return

    await state.update_data(target_user=user)
    await state.set_state(AdminStates.balance_amount)
    data = await state.get_data()
    action_label = "выдать" if data.get("balance_action") == "give" else "списать"
    await message.answer(
        f"💰 Введите сумму для {action_label} (в USD):",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.balance_amount)
async def admin_balance_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = float((message.text or "").strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную сумму:", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    user = data["target_user"]
    action = data["balance_action"]

    if action == "give":
        await db.update_balance(user["tg_id"], amount)
        msg = f"✅ Выдано {amount}$ пользователю {user['tg_id']}"
    else:
        await db.update_balance(user["tg_id"], -amount)
        msg = f"✅ Списано {amount}$ у пользователя {user['tg_id']}"

    await state.clear()
    await message.answer(msg, reply_markup=admin_kb())


# ─────────────────────── USER BALANCES LIST ───────────────────────

@router.callback_query(F.data == "admin_balances")
async def admin_balances(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    users = await db.get_active_users()
    if not users:
        await callback.answer("❌ Нет активных пользователей.", show_alert=True)
        return

    lines = []
    for u in users[:50]:
        uname = f"@{u['username']}" if u.get("username") else "—"
        sub = "✅" if u.get("sub_end") else "❌"
        lines.append(f"{uname} | ID: {u['tg_id']} | 💰 {u['balance']}$ | {sub}")

    text = "👥 <b>Активные пользователи:</b>\n\n" + "\n".join(lines)
    await callback.message.answer(text[:4096], reply_markup=admin_kb(), parse_mode="HTML")
    await callback.answer()


# ─────────────────────── PROMO CODES ───────────────────────

@router.callback_query(F.data == "admin_promos")
async def admin_promos(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    promos = await db.get_all_promos()
    text = "🎁 <b>Промокоды:</b>\n\n"
    if promos:
        for p in promos:
            text += f"• <code>{p['code']}</code> — {p['amount']}$ — {p['used_count']}/{p['max_uses']}\n"
    else:
        text += "Нет промокодов."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin")],
    ])
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_create_promo")
async def admin_create_promo_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.promo_code)
    await callback.message.answer("🎁 Введите код промокода:", reply_markup=cancel_kb())
    await callback.answer()


@router.message(AdminStates.promo_code)
async def admin_promo_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    if not code:
        await message.answer("❌ Введите код:", reply_markup=cancel_kb())
        return
    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.promo_amount)
    await message.answer("💰 Введите сумму (USD):", reply_markup=cancel_kb())


@router.message(AdminStates.promo_amount)
async def admin_promo_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = float((message.text or "").strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную сумму:", reply_markup=cancel_kb())
        return
    await state.update_data(promo_amount=amount)
    await state.set_state(AdminStates.promo_uses)
    await message.answer("🔢 Введите количество активаций:", reply_markup=cancel_kb())


@router.message(AdminStates.promo_uses)
async def admin_promo_uses(message: Message, state: FSMContext) -> None:
    try:
        uses = int((message.text or "").strip())
        if uses <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное число:", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    await db.create_promo(data["promo_code"], data["promo_amount"], uses)
    await state.clear()
    await message.answer(
        f"✅ Промокод <code>{data['promo_code']}</code> создан!\n"
        f"💰 Сумма: {data['promo_amount']}$\n"
        f"🔢 Активаций: {uses}",
        reply_markup=admin_kb(),
        parse_mode="HTML",
    )
