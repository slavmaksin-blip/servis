from __future__ import annotations

import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.keyboards import countries_kb, main_menu_kb
from app.services.prank_pdf import generate_prank_bank_pdf
from app.states import PdfFlow

router = Router()


# ---------------------------------------------------------------------------
# Entry point — "PDF Kontoauszug" button in platform menu
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("pdf:start:"))
async def pdf_entry(call: CallbackQuery, state: FSMContext) -> None:
    country = call.data.split(":")[-1]
    await state.clear()
    await state.update_data(country=country)
    await state.set_state(PdfFlow.account_holder)
    await call.message.edit_text(
        "📄 <b>Фейковая PDF-выписка из банка</b>\n\n"
        "Мне нужно несколько данных для документа.\n\n"
        "<b>Шаг 1/4 — Владелец счёта:</b>\n"
        "Введи имя и фамилию владельца (например: <i>Max Mustermann</i>):",
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Back navigation from PDF flow → country selection
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "pdf:back:countries")
async def pdf_back_countries(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("Выбери страну:", reply_markup=countries_kb())
    await call.answer()


# ---------------------------------------------------------------------------
# FSM step 1: account holder name
# ---------------------------------------------------------------------------

@router.message(PdfFlow.account_holder)
async def pdf_input_holder(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) < 2:
        await message.answer("❌ Введи корректное имя (минимум 2 символа):")
        return
    if len(name) > 60:
        await message.answer("❌ Имя слишком длинное (максимум 60 символов). Сократи:")
        return
    await state.update_data(account_holder=name)
    await state.set_state(PdfFlow.iban_suffix)
    await message.answer(
        "<b>Шаг 2/4 — Последние 4 цифры IBAN:</b>\n"
        "Введи последние 4 цифры IBAN (например: <i>7809</i>).\n"
        "В документе IBAN будет отображён как <code>CH** **** **** **** **XXXX</code>.",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# FSM step 2: last 4 digits of IBAN
# ---------------------------------------------------------------------------

@router.message(PdfFlow.iban_suffix)
async def pdf_input_iban(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    digits = raw.replace(" ", "")
    if not digits.isdigit() or len(digits) < 1:
        await message.answer(
            "❌ Введи 1–4 цифры (последние символы IBAN):"
        )
        return
    await state.update_data(iban_suffix=digits[-4:])
    await state.set_state(PdfFlow.service_name)
    await message.answer(
        "<b>Шаг 3/4 — Получатель платежа:</b>\n"
        "Как называется сервис или компания, которой ушёл платёж?\n"
        "(например: <i>Netflix</i>, <i>Spotify</i>, <i>Amazon</i>)",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# FSM step 3: service / payee name
# ---------------------------------------------------------------------------

@router.message(PdfFlow.service_name)
async def pdf_input_service(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Название не должно быть пустым. Введи ещё раз:")
        return
    if len(name) > 50:
        await message.answer("❌ Название слишком длинное (максимум 50 символов):")
        return
    await state.update_data(service_name=name)
    await state.set_state(PdfFlow.amount)
    await message.answer(
        "<b>Шаг 4/4 — Сумма в CHF:</b>\n"
        "Введи сумму, например: <b>49.90</b>",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# FSM step 4: amount → generate and send PDF
# ---------------------------------------------------------------------------

@router.message(PdfFlow.amount)
async def pdf_input_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError("non-positive")
        if amount > 999_999:
            raise ValueError("too large")
    except ValueError:
        await message.answer(
            "❌ Неверная сумма. Введи положительное число, например: <b>49.90</b>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    account_holder = data.get("account_holder", "Max Mustermann")
    iban_suffix    = data.get("iban_suffix", "0000")
    service_name   = data.get("service_name", "Service")

    await message.answer("⏳ Генерирую PDF, подожди секунду...")

    pdf_bytes = generate_prank_bank_pdf(
        account_holder=account_holder,
        iban_suffix=iban_suffix,
        service_name=service_name,
        amount_chf=amount,
    )

    caption = (
        "📄 <b>Фейковая банковская выписка</b>\n"
        "⚠️ Это <b>фейковый</b> документ, созданный в развлекательных целях.\n"
        "Не является настоящим банковским документом."
    )
    safe_name = re.sub(r"[^\w\-]", "_", service_name[:20])
    filename = f"kontoauszug_{safe_name}.pdf"
    await message.answer_document(
        document=BufferedInputFile(pdf_bytes, filename=filename),
        caption=caption,
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await state.clear()
