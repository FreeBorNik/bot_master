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
from bot.registry.models import BotInstance, RegistryLoadResult

logger = logging.getLogger(__name__)


def _resolve_child_db_path(stored_path: str) -> Path:
    """Абсолютный или относительный путь к SQLite child-бота."""
    path = Path(stored_path)
    if path.is_absolute():
        return path
    if not RunnerConfig.RECIPIENTS_DB_DIR:
        raise ValueError(
            f"Относительный db_path '{stored_path}' в recipient_bots: "
            "укажите RECIPIENTS_DB_DIR в .env"
        )
    return RunnerConfig.RECIPIENTS_DB_DIR / path


class BotRegistry:
    """Загрузка активных ботов из recipient_bots."""

    @staticmethod
    async def load() -> RegistryLoadResult:
        """
        Загрузить все активные child-боты.

        Returns:
            RegistryLoadResult с успешными экземплярами и списком ошибок
        """
        decryptor = TokenDecryptor(RunnerConfig.SENDER_ENCRYPTION_KEY)
        rows = await BotRegistry._fetch_active_rows()
        instances: list[BotInstance] = []
        errors: list[str] = []

        for row in rows:
            instance, error = await BotRegistry._load_one(row, decryptor)
            if instance is not None:
                instances.append(instance)
            elif error:
                errors.append(error)

        if instances:
            logger.info("Загружено child-ботов: %d из %d", len(instances), len(rows))
        else:
            logger.error(
                "Не загружено ни одного child-бота из %d активных в recipient_bots",
                len(rows),
            )
            for error in errors:
                logger.error("  %s", error)

        return RegistryLoadResult(
            instances=instances,
            errors=errors,
            active_rows=len(rows),
        )

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
    ) -> tuple[Optional[BotInstance], Optional[str]]:
        registry_id = row["id"]
        name = row["bot_name"]
        label = f"{name} (id={registry_id})"

        try:
            db_path = _resolve_child_db_path(row["db_path"])
        except ValueError as exc:
            logger.error("Бот %s: %s", label, exc)
            return None, f"{label}: {exc}"

        if not db_path.exists():
            logger.warning(
                "Бот %s: файл БД будет создан при старте: %s",
                label,
                db_path,
            )

        try:
            token = decryptor.decrypt(row["bot_token"])
        except Exception as exc:
            logger.error("Бот %s: ошибка расшифровки токена: %s", label, exc)
            return None, f"{label}: ошибка расшифровки токена"

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
            logger.error("Бот %s: getMe() failed: %s", label, exc)
            await bot.session.close()
            return None, f"{label}: getMe() failed — {exc}"

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
        return instance, None
