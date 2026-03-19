"""
Menu handler — text button navigation from the main reply keyboard.
"""

import logging

from aiogram import F, Router
from aiogram.types import Message

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "📱 SMS модуль")
async def menu_sms(message: Message) -> None:
    # Handled by modules.py; this stub prevents "unhandled" warnings
    pass


@router.message(F.text == "📧 Магазин почты")
async def menu_shop(message: Message) -> None:
    # Handled by shop.py; this stub prevents "unhandled" warnings
    pass


@router.message(F.text == "👤 Профиль")
async def menu_profile(message: Message) -> None:
    # Handled by profile.py; this stub prevents "unhandled" warnings
    pass
