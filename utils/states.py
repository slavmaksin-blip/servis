"""
FSM states for the Telegram bot.
"""

from aiogram.fsm.state import State, StatesGroup


class SMSStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_message = State()
    waiting_for_confirm = State()


class ShopStates(StatesGroup):
    waiting_for_site = State()
    waiting_for_domain = State()
    waiting_for_message_poll = State()


class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()
    waiting_for_broadcast = State()
