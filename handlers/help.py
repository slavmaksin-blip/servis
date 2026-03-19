import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)
router = Router()

HELP_TEXT = (
    "❓ <b>Помощь</b>\n\n"
    "<b>🔧 Модули:</b>\n"
    "  • <b>SMS</b> — отправка SMS на любой номер\n"
    "  • <b>Mailer</b> — email рассылка (в разработке)\n"
    "  • <b>Screen</b> — скриншоты (в разработке)\n"
    "  • <b>Proxy</b> — прокси (в разработке)\n\n"
    "<b>🛒 Магазин:</b>\n"
    "  • <b>Купить почту</b> — покупка email аккаунтов\n"
    "  • <b>Товары</b> — цифровые товары по категориям\n\n"
    "<b>👤 Профиль:</b>\n"
    "  • Пополнение баланса (CryptoBot / xRocket)\n"
    "  • Покупка подписки (1 / 3 / 15 дней)\n"
    "  • Активация промокода\n\n"
    "<b>📌 Команды:</b>\n"
    "  • /start — главное меню\n"
    "  • /admin — панель администратора (только для админа)\n\n"
    "<i>По всем вопросам: @support</i>"
)


@router.callback_query(F.data == "menu:help")
async def show_help(callback: CallbackQuery) -> None:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back"))
    try:
        await callback.message.edit_text(
            HELP_TEXT,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            HELP_TEXT,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    await callback.answer()
