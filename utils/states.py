from aiogram.fsm.state import State, StatesGroup


class MailerStates(StatesGroup):
    sender_name = State()
    recipient_email = State()
    subject = State()
    template = State()
