"""Middleware: доступ только для админов control bot."""
from typing import Any, Awaitable, Callable, Set

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class ControlAdminMiddleware(BaseMiddleware):
    """Проверка user_id по CONTROL_ADMIN_IDS."""

    def __init__(self, admin_ids: Set[int]) -> None:
        self._admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return await handler(event, data)

        if user.id not in self._admin_ids:
            logger.warning(
                "Control bot: отказ в доступе user_id=%s",
                user.id,
            )
            if isinstance(event, CallbackQuery):
                await event.answer("Нет доступа.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⛔ Нет доступа к control bot.")
            return

        return await handler(event, data)
