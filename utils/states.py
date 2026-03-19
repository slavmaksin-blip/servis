from aiogram.fsm.state import State, StatesGroup


class SubscriptionCheck(StatesGroup):
    waiting = State()


class SMSModule(StatesGroup):
    choose_country = State()
    enter_phone = State()
    enter_sender = State()
    enter_text = State()


class MailModule(StatesGroup):
    enter_domain = State()
    confirm = State()
    view_inbox = State()


class ProductModule(StatesGroup):
    choose_category = State()
    choose_product = State()
    choose_quantity = State()


class ProfileModule(StatesGroup):
    choose_payment = State()
    enter_amount = State()
    choose_subscription = State()
    enter_promo = State()


class AdminModule(StatesGroup):
    ban_user = State()
    unban_user = State()
    broadcast_text = State()
    add_category = State()
    add_product = State()
    give_balance = State()
    take_balance = State()
    create_promo = State()
