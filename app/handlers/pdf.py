from __future__ import annotations

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
        "📄 <b>Fake-PDF: Kontoauszug / Belastungsanzeige</b>\n\n"
        "Ich benötige einige Angaben für das Dokument.\n\n"
        "<b>Schritt 1/4 — Kontoinhaber:</b>\n"
        "Gib den Namen des Kontoinhabers ein (z. B. <i>Max Mustermann</i>):",
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Back navigation from PDF flow → country selection
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "pdf:back:countries")
async def pdf_back_countries(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("Wähle ein Land:", reply_markup=countries_kb())
    await call.answer()


# ---------------------------------------------------------------------------
# FSM step 1: account holder name
# ---------------------------------------------------------------------------

@router.message(PdfFlow.account_holder)
async def pdf_input_holder(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) < 2:
        await message.answer("❌ Bitte gib einen gültigen Namen ein:")
        return
    if len(name) > 60:
        await message.answer("❌ Name zu lang (max. 60 Zeichen). Bitte kürzen:")
        return
    await state.update_data(account_holder=name)
    await state.set_state(PdfFlow.iban_suffix)
    await message.answer(
        "<b>Schritt 2/4 — Letzte 4 Ziffern der IBAN:</b>\n"
        "Gib die letzten 4 Ziffern deiner IBAN ein (z. B. <i>7809</i>).\n"
        "Die IBAN wird im Dokument als <code>CH** **** **** **** **XXXX</code> angezeigt.",
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
            "❌ Bitte gib 1–4 Ziffern ein (die letzten Stellen deiner IBAN):"
        )
        return
    await state.update_data(iban_suffix=digits[-4:])
    await state.set_state(PdfFlow.service_name)
    await message.answer(
        "<b>Schritt 3/4 — Zahlungsempfänger:</b>\n"
        "Wie heißt der Dienst oder das Unternehmen, an das die Zahlung ging?\n"
        "(z. B. <i>Netflix</i>, <i>Spotify</i>, <i>Amazon</i>)",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# FSM step 3: service / payee name
# ---------------------------------------------------------------------------

@router.message(PdfFlow.service_name)
async def pdf_input_service(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Der Name darf nicht leer sein. Bitte eingeben:")
        return
    if len(name) > 50:
        await message.answer("❌ Name zu lang (max. 50 Zeichen):")
        return
    await state.update_data(service_name=name)
    await state.set_state(PdfFlow.amount)
    await message.answer(
        "<b>Schritt 4/4 — Betrag in CHF:</b>\n"
        "Gib den Betrag ein, z. B. <b>49.90</b>",
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
            "❌ Ungültiger Betrag. Bitte eine positive Zahl eingeben, z. B. <b>49.90</b>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    account_holder = data.get("account_holder", "Max Mustermann")
    iban_suffix    = data.get("iban_suffix", "0000")
    service_name   = data.get("service_name", "Service")

    await message.answer("⏳ Generiere PDF, bitte warten…")

    pdf_bytes = generate_prank_bank_pdf(
        account_holder=account_holder,
        iban_suffix=iban_suffix,
        service_name=service_name,
        amount_chf=amount,
    )

    caption = (
        "📄 <b>Fake-Kontoauszug (ATTRAPPE)</b>\n"
        "Das Dokument enthält einen deutlichen Hinweis: «ATTRAPPE / FAKE».\n"
        "Es handelt sich um <b>kein echtes Bankdokument</b>."
    )
    filename = f"kontoauszug_{service_name[:20].replace(' ', '_')}.pdf"
    await message.answer_document(
        document=BufferedInputFile(pdf_bytes, filename=filename),
        caption=caption,
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await state.clear()
