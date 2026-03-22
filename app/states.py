from aiogram.fsm.state import State, StatesGroup


class ScreenFlow(StatesGroup):
    country = State()
    platform = State()
    service_name = State()
    amount = State()


class PdfFlow(StatesGroup):
    account_holder = State()   # Name des Kontoinhabers
    iban_suffix = State()      # Letzte 4 Ziffern der IBAN
    service_name = State()     # Zahlungsempfänger
    amount = State()           # Betrag in CHF
