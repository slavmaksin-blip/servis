from aiogram.fsm.state import State, StatesGroup


class MailerStates(StatesGroup):
    sender_name = State()
    recipient_email = State()
    subject = State()
    template = State()


class SmtpStates(StatesGroup):
    host = State()
    port = State()
    use_ssl = State()
    user = State()
    password = State()
    confirm = State()
