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

# Значение runner в recipient_bots: polling в этом процессе
RUNNER_BOT_MASTER = "bot_master"


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
    """Загрузка активных ботов из recipient_bots (runner=bot_master)."""

    @staticmethod
    async def load() -> RegistryLoadResult:
        """
        Загрузить активные child-боты с runner=bot_master.

        Боты с runner=external остаются в recipient_bots для рассылок
        bot_sender, но не поднимаются в polling.

        Returns:
            RegistryLoadResult с успешными экземплярами и списком ошибок
        """
        decryptor = TokenDecryptor(RunnerConfig.SENDER_ENCRYPTION_KEY)
        rows, skipped_external = await BotRegistry._fetch_active_rows()
        instances: list[BotInstance] = []
        errors: list[str] = []

        if skipped_external:
            logger.info(
                "Пропущено external-ботов (только рассылки): %d",
                skipped_external,
            )

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
                "Не загружено ни одного child-бота из %d кандидатов в recipient_bots",
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
    async def _has_runner_column(conn: aiosqlite.Connection) -> bool:
        cursor = await conn.execute("PRAGMA table_info(recipient_bots)")
        columns = await cursor.fetchall()
        return any(col[1] == "runner" for col in columns)

    @staticmethod
    async def _fetch_active_rows() -> tuple[list[aiosqlite.Row], int]:
        """
        Активные боты для polling.

        Returns:
            (rows, число пропущенных external при наличии колонки runner)
        """
        async with aiosqlite.connect(RunnerConfig.SENDER_DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            has_runner = await BotRegistry._has_runner_column(conn)

            if has_runner:
                skipped_cursor = await conn.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM recipient_bots
                    WHERE is_active = 1
                      AND LOWER(TRIM(COALESCE(runner, ''))) = 'external'
                    """
                )
                skipped_row = await skipped_cursor.fetchone()
                skipped_external = int(skipped_row["cnt"] if skipped_row else 0)

                cursor = await conn.execute(
                    """
                    SELECT id, bot_name, bot_token, db_path, first_name, runner
                    FROM recipient_bots
                    WHERE is_active = 1
                      AND LOWER(TRIM(COALESCE(runner, 'bot_master'))) = ?
                    ORDER BY bot_name
                    """,
                    (RUNNER_BOT_MASTER,),
                )
                rows = await cursor.fetchall()
                return rows, skipped_external

            logger.warning(
                "Колонка recipient_bots.runner отсутствует — "
                "загружаем всех is_active=1. "
                "Перезапустите bot_sender для миграции."
            )
            cursor = await conn.execute(
                """
                SELECT id, bot_name, bot_token, db_path, first_name
                FROM recipient_bots
                WHERE is_active = 1
                ORDER BY bot_name
                """
            )
            return await cursor.fetchall(), 0

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
