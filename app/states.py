from aiogram.fsm.state import State, StatesGroup


class ScreenFlow(StatesGroup):
    country = State()
    platform = State()
    service_name = State()
    amount = State()
