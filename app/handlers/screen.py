from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.keyboards import countries_kb, main_menu_kb, platforms_kb
from app.services.prank_image import generate_prank_bank_screen
from app.states import ScreenFlow

router = Router()


# ---------------------------------------------------------------------------
# Entry point — "Screen" button in main menu
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "menu:screen")
async def screen_entry(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ScreenFlow.country)
    await call.message.edit_text("Выбери страну:", reply_markup=countries_kb())
    await call.answer()


# ---------------------------------------------------------------------------
# Back navigation
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "screen:back:countries")
async def back_to_countries(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ScreenFlow.country)
    await call.message.edit_text("Выбери страну:", reply_markup=countries_kb())
    await call.answer()


# ---------------------------------------------------------------------------
# Country selection
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("screen:country:"))
async def pick_country(call: CallbackQuery, state: FSMContext) -> None:
    country = call.data.split(":")[-1]
    await state.update_data(country=country)
    await state.set_state(ScreenFlow.platform)
    await call.message.edit_text("Выбери платформу:", reply_markup=platforms_kb(country))
    await call.answer()


# ---------------------------------------------------------------------------
# Platform selection
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("screen:platform:"))
async def pick_platform(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split(":")        # screen : platform : ch : bank
    country = parts[2] if len(parts) > 2 else "ch"
    platform = parts[3] if len(parts) > 3 else "bank"
    await state.update_data(country=country, platform=platform)
    await state.set_state(ScreenFlow.service_name)
    await call.message.edit_text(
        "Введи название сервиса (например: <b>Netflix</b>):",
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# FSM: service name input
# ---------------------------------------------------------------------------

@router.message(ScreenFlow.service_name)
async def input_service(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Название не должно быть пустым. Введи ещё раз:")
        return
    if len(name) > 40:
        await message.answer("❌ Слишком длинное название (максимум 40 символов). Попробуй короче:")
        return
    await state.update_data(service_name=name)
    await state.set_state(ScreenFlow.amount)
    await message.answer("Введи сумму списания (CHF), например: <b>12.50</b>", parse_mode="HTML")


# ---------------------------------------------------------------------------
# FSM: amount input → generate and send image
# ---------------------------------------------------------------------------

@router.message(ScreenFlow.amount)
async def input_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError("non-positive")
        if amount > 999_999:
            raise ValueError("too large")
    except ValueError:
        await message.answer("❌ Неверная сумма. Введи число больше 0, например: <b>49.90</b>", parse_mode="HTML")
        return

    data = await state.get_data()
    service_name = data.get("service_name", "Service")

    await message.answer("⏳ Генерирую скрин, подожди секунду...")

    now = datetime.now(timezone.utc)
    png_bytes = generate_prank_bank_screen(
        service_name=service_name,
        amount_chf=amount,
        now=now,
    )

    caption = (
        "🃏 <b>Шуточный скрин</b>\n"
        "На изображении видимый водяной знак «РОЗЫГРЫШ / FAKE».\n"
        "Не является настоящим банковским документом."
    )
    await message.answer_photo(
        photo=BufferedInputFile(png_bytes, filename="prank_screen.png"),
        caption=caption,
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await state.clear()
