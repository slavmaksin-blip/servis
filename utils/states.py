from aiogram.fsm.state import State, StatesGroup


class MenuStates(StatesGroup):
    main_menu = State()
    modules = State()
    shop = State()
    profile = State()


class SMSStates(StatesGroup):
    enter_phone = State()
    enter_message = State()
    confirm = State()


class MailStates(StatesGroup):
    viewing_mailbox = State()


class ShopStates(StatesGroup):
    browsing = State()
    confirm_purchase = State()


class AdminStates(StatesGroup):
    broadcast = State()
    add_balance = State()
    enter_user_id = State()
    enter_amount = State()
