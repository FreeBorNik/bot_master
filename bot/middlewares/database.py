"""Middleware для передачи базы данных в контекст (multi-bot)."""
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject

from bot.database.db import Database


class MultiDatabaseMiddleware(BaseMiddleware):
    """Выбор SQLite по telegram bot.id."""

    def __init__(self, db_map: dict[int, Database]) -> None:
        """
        Args:
            db_map: telegram bot.id -> Database child-бота
        """
        self._db_map = db_map

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        bot: Bot | None = data.get("bot")
        if bot is None:
            raise RuntimeError("MultiDatabaseMiddleware: bot не найден в data")

        db = self._db_map.get(bot.id)
        if db is None:
            raise RuntimeError(f"MultiDatabaseMiddleware: нет БД для bot.id={bot.id}")

        data["db"] = db
        return await handler(event, data)
