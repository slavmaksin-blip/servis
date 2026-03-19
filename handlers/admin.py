import os
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    get_user,
    ban_user,
    unban_user,
    get_all_users,
    get_all_balances,
    update_user_balance,
    get_categories,
    add_category,
    delete_category,
    get_products,
    add_product,
    delete_product,
    update_product_file,
    create_promo,
)
from handlers.states import AdminStates
from utils.keyboards import (
    admin_keyboard,
    admin_categories_keyboard,
    admin_products_keyboard,
    cancel_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()

_SELECTED_CATEGORY: dict[int, int] = {}

# Maximum number of balances to display in a single message (prevents overflow)
MAX_DISPLAYED_BALANCES = 30


def _get_admin_id() -> int:
    return int(os.getenv("ADMIN_ID", "0"))


def _is_admin(user_id: int) -> bool:
    return user_id == _get_admin_id()


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🔐 <b>Панель администратора</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "🔐 <b>Панель администратора</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── BAN / UNBAN ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:ban")
async def admin_ban_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "🚫 Введите ID или @username пользователя для бана:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.ban)
    await callback.answer()


@router.message(AdminStates.ban)
async def admin_ban_execute(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🔐 <b>Панель администратора</b>",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )
        return

    target = message.text.strip()
    user_id = await _resolve_user(bot, target)
    if not user_id:
        await message.answer(f"❌ Пользователь не найден: {target}", reply_markup=cancel_keyboard())
        return

    await ban_user(user_id)
    await state.clear()
    await message.answer(
        f"✅ Пользователь <code>{user_id}</code> заблокирован.",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )
    try:
        await bot.send_message(user_id, "🚫 Вы заблокированы в боте.")
    except Exception:
        pass


@router.callback_query(F.data == "admin:unban")
async def admin_unban_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "✅ Введите ID или @username пользователя для разбана:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.unban)
    await callback.answer()


@router.message(AdminStates.unban)
async def admin_unban_execute(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🔐 <b>Панель администратора</b>",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )
        return

    target = message.text.strip()
    user_id = await _resolve_user(bot, target)
    if not user_id:
        await message.answer(f"❌ Пользователь не найден: {target}", reply_markup=cancel_keyboard())
        return

    await unban_user(user_id)
    await state.clear()
    await message.answer(
        f"✅ Пользователь <code>{user_id}</code> разблокирован.",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )
    try:
        await bot.send_message(user_id, "✅ Вы разблокированы в боте.")
    except Exception:
        pass


# ─── BROADCAST ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте текст или фото с подписью для рассылки:\n"
        "(используйте кнопку «❌ Отмена» для отмены)",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.broadcast_text)
    await callback.answer()


@router.message(AdminStates.broadcast_text)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🔐 <b>Панель администратора</b>",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )
        return

    users = await get_all_users()
    success = 0
    failed = 0
    for user in users:
        uid = user["user_id"]
        if user.get("is_banned"):
            continue
        try:
            if message.photo:
                await bot.send_photo(
                    uid,
                    photo=message.photo[-1].file_id,
                    caption=message.caption or "",
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(uid, message.text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"📢 <b>Рассылка завершена!</b>\n\n✅ Отправлено: {success}\n❌ Не доставлено: {failed}",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# ─── CATEGORIES ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:categories")
async def admin_categories(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    categories = await get_categories()
    await callback.message.edit_text(
        "📁 <b>Категории товаров</b>\n\nНажмите на категорию чтобы удалить её:",
        reply_markup=admin_categories_keyboard(categories),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_cat:"))
async def admin_delete_category(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    cat_id = int(callback.data.split(":")[1])
    await delete_category(cat_id)
    categories = await get_categories()
    await callback.message.edit_text(
        "📁 <b>Категории товаров</b>\n\nКатегория удалена. Нажмите на категорию чтобы удалить её:",
        reply_markup=admin_categories_keyboard(categories),
        parse_mode="HTML",
    )
    await callback.answer("🗑 Категория удалена.")


@router.callback_query(F.data == "admin:add_category")
async def admin_add_category_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "📁 Введите название новой категории:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.add_category)
    await callback.answer()


@router.message(AdminStates.add_category)
async def admin_add_category_save(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "🔐 <b>Панель администратора</b>",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )
        return
    name = message.text.strip()
    await add_category(name)
    await state.clear()
    categories = await get_categories()
    await message.answer(
        f"✅ Категория «{name}» добавлена!",
        reply_markup=admin_categories_keyboard(categories),
        parse_mode="HTML",
    )


# ─── PRODUCTS ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:products")
async def admin_products(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    categories = await get_categories()
    if not categories:
        await callback.answer("❌ Сначала создайте категорию.", show_alert=True)
        return

    all_products = []
    for cat in categories:
        prods = await get_products(cat["id"])
        for p in prods:
            p["category_name"] = cat["name"]
        all_products.extend(prods)

    await callback.message.edit_text(
        "📦 <b>Товары</b>\n\nНажмите для удаления:",
        reply_markup=admin_products_keyboard(all_products),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_prod:"))
async def admin_delete_product(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    product_id = int(callback.data.split(":")[1])
    await delete_product(product_id)

    categories = await get_categories()
    all_products = []
    for cat in categories:
        prods = await get_products(cat["id"])
        for p in prods:
            p["category_name"] = cat["name"]
        all_products.extend(prods)

    await callback.message.edit_text(
        "📦 <b>Товары</b>\n\nТовар удалён. Нажмите для удаления:",
        reply_markup=admin_products_keyboard(all_products),
        parse_mode="HTML",
    )
    await callback.answer("🗑 Товар удалён.")


@router.callback_query(F.data == "admin:add_product")
async def admin_add_product_category(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    categories = await get_categories()
    if not categories:
        await callback.answer("❌ Сначала создайте категорию.", show_alert=True)
        return
    lines = "\n".join([f"  {c['id']}. {c['name']}" for c in categories])
    await callback.message.answer(
        f"📦 Введите ID категории для товара:\n\n{lines}",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.add_product_category)
    await callback.answer()


@router.message(AdminStates.add_product_category)
async def admin_add_product_name(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    try:
        cat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (ID категории):", reply_markup=cancel_keyboard())
        return
    await state.update_data(product_category_id=cat_id)
    await message.answer("📦 Введите название товара:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.add_product_name)


@router.message(AdminStates.add_product_name)
async def admin_add_product_description(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    await state.update_data(product_name=message.text.strip())
    await message.answer("📦 Введите описание товара:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.add_product_description)


@router.message(AdminStates.add_product_description)
async def admin_add_product_price(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    await state.update_data(product_description=message.text.strip())
    await message.answer("📦 Введите цену товара в USD:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.add_product_price)


@router.message(AdminStates.add_product_price)
async def admin_add_product_save(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    try:
        price = float(message.text.strip().replace(",", "."))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную цену:", reply_markup=cancel_keyboard())
        return
    data = await state.get_data()
    product_id = await add_product(
        data["product_category_id"],
        data["product_name"],
        data["product_description"],
        price,
    )
    await state.clear()
    await message.answer(
        f"✅ Товар «{data['product_name']}» добавлен! (ID: {product_id})\n\n"
        f"Загрузите файл товара через «📎 Загрузить файл».",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# ─── UPLOAD FILE ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:upload_file")
async def admin_upload_file_product(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "📎 Введите ID товара для загрузки файла:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.upload_file_product)
    await callback.answer()


@router.message(AdminStates.upload_file_product)
async def admin_upload_file_ask_file(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    try:
        product_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (ID товара):", reply_markup=cancel_keyboard())
        return
    await state.update_data(upload_product_id=product_id)
    await message.answer(
        f"📎 Отправьте файл для товара ID {product_id}:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.upload_file)


@router.message(AdminStates.upload_file)
async def admin_upload_file_save(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return

    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.video:
        file_id = message.video.file_id

    if not file_id:
        await message.answer("❌ Отправьте файл (документ, фото, аудио или видео):")
        return

    data = await state.get_data()
    product_id = data["upload_product_id"]
    await update_product_file(product_id, file_id)
    await state.clear()
    await message.answer(
        f"✅ Файл для товара ID {product_id} сохранён!",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# ─── BALANCE MANAGEMENT ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:give_balance")
async def admin_give_balance_user(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "💸 Введите ID или @username пользователя для начисления баланса:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.give_balance_user)
    await callback.answer()


@router.message(AdminStates.give_balance_user)
async def admin_give_balance_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    target = message.text.strip()
    user_id = await _resolve_user(bot, target)
    if not user_id:
        await message.answer(f"❌ Пользователь не найден: {target}", reply_markup=cancel_keyboard())
        return
    await state.update_data(target_user_id=user_id)
    await message.answer(
        f"💸 Начислить баланс пользователю <code>{user_id}</code>.\nВведите сумму в USD:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.give_balance_amount)


@router.message(AdminStates.give_balance_amount)
async def admin_give_balance_execute(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    try:
        amount = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("❌ Введите корректную сумму:", reply_markup=cancel_keyboard())
        return
    data = await state.get_data()
    target_id = data["target_user_id"]
    new_balance = await update_user_balance(target_id, amount)
    await state.clear()
    await message.answer(
        f"✅ Начислено <b>${amount:.2f}</b> пользователю <code>{target_id}</code>.\n"
        f"💰 Новый баланс: <b>${new_balance:.2f}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )
    try:
        await bot.send_message(
            target_id,
            f"💰 <b>Ваш баланс пополнен на ${amount:.2f}!</b>\n"
            f"💵 Текущий баланс: ${new_balance:.2f}",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data == "admin:take_balance")
async def admin_take_balance_user(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "💰 Введите ID или @username пользователя для списания баланса:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.take_balance_user)
    await callback.answer()


@router.message(AdminStates.take_balance_user)
async def admin_take_balance_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    target = message.text.strip()
    user_id = await _resolve_user(bot, target)
    if not user_id:
        await message.answer(f"❌ Пользователь не найден: {target}", reply_markup=cancel_keyboard())
        return
    await state.update_data(target_user_id=user_id)
    await message.answer(
        f"💰 Списать баланс пользователя <code>{user_id}</code>.\nВведите сумму в USD:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.take_balance_amount)


@router.message(AdminStates.take_balance_amount)
async def admin_take_balance_execute(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную сумму:", reply_markup=cancel_keyboard())
        return
    data = await state.get_data()
    target_id = data["target_user_id"]
    new_balance = await update_user_balance(target_id, -amount)
    await state.clear()
    await message.answer(
        f"✅ Списано <b>${amount:.2f}</b> у пользователя <code>{target_id}</code>.\n"
        f"💰 Новый баланс: <b>${new_balance:.2f}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:balances")
async def admin_balances(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    balances = await get_all_balances()
    if not balances:
        await callback.answer("📊 Нет пользователей.", show_alert=True)
        return
    lines = []
    for u in balances[:MAX_DISPLAYED_BALANCES]:
        name = f"@{u['username']}" if u["username"] else u.get("first_name") or str(u["user_id"])
        lines.append(f"  {name}: <b>${u['balance']:.2f}</b>")
    text = "📊 <b>Балансы пользователей:</b>\n\n" + "\n".join(lines)
    if len(balances) > MAX_DISPLAYED_BALANCES:
        text += f"\n\n<i>...и ещё {len(balances) - MAX_DISPLAYED_BALANCES} пользователей</i>"
    await callback.message.answer(text, reply_markup=admin_keyboard(), parse_mode="HTML")
    await callback.answer()


# ─── PROMO CODES ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:promo")
async def admin_promo_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "🎁 Создание промокода.\nВведите код (текст):",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.create_promo_code)
    await callback.answer()


@router.message(AdminStates.create_promo_code)
async def admin_promo_code(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    code = message.text.strip()
    await state.update_data(promo_code=code)
    await message.answer("🎁 Введите сумму в USD для начисления:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.create_promo_amount)


@router.message(AdminStates.create_promo_amount)
async def admin_promo_amount(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную сумму:", reply_markup=cancel_keyboard())
        return
    await state.update_data(promo_amount=amount)
    await message.answer(
        "🎁 Введите лимит использований (сколько раз можно активировать):",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminStates.create_promo_limit)


@router.message(AdminStates.create_promo_limit)
async def admin_promo_limit(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text == "❌ Отмена":
        await _admin_cancel(message, state)
        return
    try:
        limit = int(message.text.strip())
        if limit <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное число:", reply_markup=cancel_keyboard())
        return
    data = await state.get_data()
    code = data["promo_code"]
    amount = data["promo_amount"]
    try:
        await create_promo(code, amount, limit)
        await state.clear()
        await message.answer(
            f"✅ Промокод <code>{code}</code> создан!\n"
            f"💵 Сумма: ${amount:.2f}\n"
            f"🔢 Лимит: {limit} активаций",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )
    except Exception as exc:
        await state.clear()
        await message.answer(
            f"❌ Ошибка создания промокода: {exc}",
            reply_markup=admin_keyboard(),
        )


# ─── HELPERS ────────────────────────────────────────────────────────────────────

async def _resolve_user(bot: Bot, target: str) -> int | None:
    if target.startswith("@"):
        username = target.lstrip("@")
        users = await get_all_users()
        for u in users:
            if u.get("username") and u["username"].lower() == username.lower():
                return u["user_id"]
        return None
    try:
        return int(target)
    except ValueError:
        return None


async def _admin_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🔐 <b>Панель администратора</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )
