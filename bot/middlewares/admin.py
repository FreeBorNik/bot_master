"""Middleware для проверки прав администратора."""
from typing import Callable, Dict, Any, Awaitable, Set

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database.db import Database
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class AdminMiddleware(BaseMiddleware):
    """Проверка прав по таблице admins в child SQLite."""

    def __init__(self) -> None:
        self._cache: dict[str, Set[int]] = {}

    async def _get_admin_ids(self, db: Database) -> Set[int]:
        cache_key = db.db_path
        if cache_key in self._cache:
            return self._cache[cache_key]

        rows = await db.fetchall("SELECT user_id FROM admins", ())
        admin_ids = {row["user_id"] for row in rows}
        self._cache[cache_key] = admin_ids
        return admin_ids

    def invalidate_cache(self, db_path: str) -> None:
        """Сброс кэша после изменения списка админов."""
        self._cache.pop(db_path, None)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if hasattr(event, "from_user"):
            user = event.from_user
        elif hasattr(event, "message") and event.message:
            user = event.message.from_user

        if not user:
            return await handler(event, data)

        db: Database | None = data.get("db")
        if db is None:
            logger.warning("AdminMiddleware: db не найдена в data")
            return

        admin_ids = await self._get_admin_ids(db)
        if user.id not in admin_ids:
            logger.warning(
                "Пользователь %s попытался получить доступ к админ-функциям",
                user.id,
            )
            if hasattr(event, "answer"):
                await event.answer("У вас нет прав администратора.")
            return

        return await handler(event, data)
