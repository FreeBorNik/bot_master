"""Middleware: прокидывает BotStatusService в data control bot."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.services.bot_status import BotStatusService


class ControlDataMiddleware(BaseMiddleware):
    """Добавляет status_service в data handlers."""

    def __init__(self, status_service: BotStatusService) -> None:
        self._status_service = status_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["status_service"] = self._status_service
        return await handler(event, data)
