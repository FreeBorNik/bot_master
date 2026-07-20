"""Загрузка child-ботов из БД bot_sender."""
import logging
from pathlib import Path
from typing import Optional

import aiosqlite
from aiogram import Bot
from aiogram.enums import ParseMode

try:
    from aiogram.client.default import DefaultBotProperties
except ModuleNotFoundError:
    DefaultBotProperties = None  # aiogram < 3.2

from bot.config import RunnerConfig
from bot.registry.crypto import TokenDecryptor
from bot.registry.models import BotInstance

logger = logging.getLogger(__name__)


def _resolve_child_db_path(stored_path: str) -> Path:
    """Абсолютный или относительный путь к SQLite child-бота."""
    path = Path(stored_path)
    if path.is_absolute():
        return path
    return RunnerConfig.RECIPIENTS_DB_DIR / path


class BotRegistry:
    """Загрузка активных ботов из recipient_bots."""

    @staticmethod
    async def load() -> list[BotInstance]:
        """
        Загрузить все активные child-боты.

        Returns:
            Список успешно инициализированных BotInstance
        """
        decryptor = TokenDecryptor(RunnerConfig.SENDER_ENCRYPTION_KEY)
        rows = await BotRegistry._fetch_active_rows()
        instances: list[BotInstance] = []

        for row in rows:
            instance = await BotRegistry._load_one(row, decryptor)
            if instance is not None:
                instances.append(instance)

        if not instances:
            raise RuntimeError(
                "Не удалось загрузить ни одного child-бота. "
                "Проверьте recipient_bots и пути к БД."
            )

        logger.info("Загружено child-ботов: %d", len(instances))
        return instances

    @staticmethod
    async def _fetch_active_rows() -> list[aiosqlite.Row]:
        async with aiosqlite.connect(RunnerConfig.SENDER_DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT id, bot_name, bot_token, db_path, first_name
                FROM recipient_bots
                WHERE is_active = 1
                ORDER BY bot_name
                """
            )
            return await cursor.fetchall()

    @staticmethod
    async def _load_one(
        row: aiosqlite.Row,
        decryptor: TokenDecryptor,
    ) -> Optional[BotInstance]:
        registry_id = row["id"]
        name = row["bot_name"]
        db_path = _resolve_child_db_path(row["db_path"])

        if not db_path.exists():
            logger.error(
                "Бот %s (id=%s): файл БД не найден: %s",
                name,
                registry_id,
                db_path,
            )
            return None

        try:
            token = decryptor.decrypt(row["bot_token"])
        except Exception as exc:
            logger.error(
                "Бот %s (id=%s): ошибка расшифровки токена: %s",
                name,
                registry_id,
                exc,
            )
            return None

        if DefaultBotProperties is not None:
            bot = Bot(
                token=token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
        else:
            bot = Bot(token=token)

        try:
            me = await bot.get_me()
        except Exception as exc:
            logger.error(
                "Бот %s (id=%s): getMe() failed: %s",
                name,
                registry_id,
                exc,
            )
            await bot.session.close()
            return None

        instance = BotInstance(
            registry_id=registry_id,
            name=name,
            token=token,
            db_path=db_path,
            bot=bot,
            first_name=me.first_name,
            username=me.username,
        )
        logger.info(
            "OK: %s | registry_id=%s | telegram_id=%s | db=%s",
            instance.display_name,
            registry_id,
            me.id,
            db_path,
        )
        return instance
