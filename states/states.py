from aiogram.fsm.state import State, StatesGroup


class SubscriptionCheck(StatesGroup):
    waiting = State()


class SmsStates(StatesGroup):
    country = State()
    phone = State()
    sender = State()
    message = State()


class MailStates(StatesGroup):
    domain_input = State()
    selecting_domain = State()
    confirm = State()


class ShopStates(StatesGroup):
    category = State()
    product = State()
    quantity = State()
    confirm = State()


class ProfileStates(StatesGroup):
    payment_system = State()
    amount = State()
    checking = State()
    promo = State()


class AdminStates(StatesGroup):
    main = State()
    ban_input = State()
    unban_input = State()
    broadcast_text = State()
    broadcast_photo = State()
    # categories
    add_category = State()
    # products
    select_category_for_product = State()
    add_product_name = State()
    add_product_desc = State()
    add_product_price = State()
    add_product_files = State()
    # stock upload
    select_product_for_stock = State()
    upload_stock_files = State()
    # balance
    balance_action = State()
    balance_user = State()
    balance_amount = State()
    # promo
    promo_code = State()
    promo_amount = State()
    promo_uses = State()
