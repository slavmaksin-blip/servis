from aiogram.fsm.state import State, StatesGroup


class SMSStates(StatesGroup):
    country = State()
    phone = State()
    sender = State()
    message = State()


class ShopEmailStates(StatesGroup):
    domain_input = State()
    select_domain = State()


class ShopProductStates(StatesGroup):
    category = State()
    product = State()
    quantity = State()
    confirm = State()


class ProfileStates(StatesGroup):
    promo = State()
    topup_amount = State()


class AdminStates(StatesGroup):
    ban = State()
    unban = State()
    broadcast_text = State()
    broadcast_photo = State()
    add_category = State()
    del_category = State()
    add_product_category = State()
    add_product_name = State()
    add_product_description = State()
    add_product_price = State()
    del_product = State()
    upload_file_product = State()
    upload_file = State()
    give_balance_user = State()
    give_balance_amount = State()
    take_balance_user = State()
    take_balance_amount = State()
    create_promo_code = State()
    create_promo_amount = State()
    create_promo_limit = State()
