"""Клавиатуры control bot."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_control_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню control bot."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Обновить статус", callback_data="control_refresh")],
            [
                InlineKeyboardButton(
                    text="🔄 Перезапуск (скоро)",
                    callback_data="control_stub_restart",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏹ Остановить (скоро)",
                    callback_data="control_stub_stop",
                ),
                InlineKeyboardButton(
                    text="▶️ Запустить (скоро)",
                    callback_data="control_stub_start",
                ),
            ],
        ]
    )
