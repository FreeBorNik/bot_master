"""Middleware: метка child-бота в contextvars для логов."""
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject

from bot.utils.bot_log_filter import set_bot_log_label


class BotLabelMiddleware(BaseMiddleware):
    """Устанавливает имя бота в contextvar перед обработкой апдейта."""

    def __init__(self, labels: dict[int, str]) -> None:
        self._labels = labels

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        bot: Bot | None = data.get("bot")
        if bot and bot.id in self._labels:
            set_bot_log_label(self._labels[bot.id])
        return await handler(event, data)
