"""Точка входа multi-bot runner."""
import asyncio
import logging
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from aiogram import Bot, Dispatcher, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import ErrorEvent

from bot.config import RunnerConfig
from bot.database.db import Database
from bot.database.migrations import create_tables
from bot.database.repositories import UserRepository
from bot.handlers import admin_router, common_router, user_router
from bot.middlewares.action_logger import ActionLoggerMiddleware
from bot.middlewares.admin import AdminMiddleware
from bot.middlewares.bot_label import BotLabelMiddleware
from bot.middlewares.database import MultiDatabaseMiddleware
from bot.registry import BotRegistry
from bot.registry.models import BotInstance
from bot.services.scheduler import MailingScheduler
from bot.utils.bot_log_filter import BotContextFilter, BotContextFormatter
from bot.utils.logger import configure_root_logging, setup_logger

logger = setup_logger(__name__)

ALLOWED_UPDATES = ["callback_query", "chat_join_request", "message", "my_chat_member"]


def _setup_logging() -> None:
    """Логи с префиксом child-бота."""
    configure_root_logging(
        RunnerConfig.LOG_LEVEL,
        str(RunnerConfig.LOG_FILE),
    )
    root = logging.getLogger()
    for handler in root.handlers:
        handler.addFilter(BotContextFilter())
        handler.setFormatter(
            BotContextFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )


def _print_healthcheck(instances: list[BotInstance], db_map: dict[int, Database]) -> None:
    """Таблица загруженных ботов при старте."""
    print("\n=== bot_master healthcheck ===")
    print(f"{'Name':<30} {'Registry ID':<12} {'Telegram ID':<14} {'DB'}")
    print("-" * 90)
    for inst in instances:
        tg_id = inst.bot.id
        db_path = db_map[tg_id].db_path
        print(f"{inst.display_name:<30} {inst.registry_id:<12} {tg_id:<14} {db_path}")
    print(f"\nВсего активных ботов: {len(instances)}\n")


async def main() -> None:
    """Запуск multi-bot runner."""
    instances: list[BotInstance] = []
    db_map: dict[int, Database] = {}
    schedulers: list[MailingScheduler] = []

    try:
        RunnerConfig.validate()
        _setup_logging()

        instances = await BotRegistry.load()

        for inst in instances:
            db = Database(inst.db_path)
            await db.connect()
            await create_tables(db)
            db_map[inst.bot.id] = db

            scheduler = MailingScheduler(inst.bot, db)
            schedulers.append(scheduler)
            await scheduler.start()

        _print_healthcheck(instances, db_map)

        storage = MemoryStorage(
            key_builder=DefaultKeyBuilder(with_bot_id=True),
        )
        dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT)

        errors_router = Router(name="errors")

        @errors_router.error()
        async def on_bot_blocked_error(event: ErrorEvent, bot: Bot) -> None:
            exc = event.exception
            if not isinstance(exc, TelegramAPIError):
                raise exc
            msg = (getattr(exc, "message", None) or str(exc) or "").lower()
            if "blocked" not in msg and "forbidden" not in msg and "deactivated" not in msg:
                raise exc

            db = db_map.get(bot.id)
            if db is None:
                raise exc

            user_id = None
            update = event.update
            if update.message and update.message.chat.type == "private":
                user_id = update.message.chat.id
            elif update.callback_query and update.callback_query.message:
                user_id = update.callback_query.message.chat.id

            if user_id:
                try:
                    user_repo = UserRepository(db)
                    await user_repo.update_user_is_in_bot(user_id, False)
                    logger.info("Пользователь %s заблокировал бота, is_in_bot=0", user_id)
                except Exception as exc_inner:
                    logger.warning(
                        "Не удалось обновить is_in_bot для %s: %s",
                        user_id,
                        exc_inner,
                    )

        dp.include_router(errors_router)

        label_map = {inst.bot.id: inst.display_name for inst in instances}
        bot_label_middleware = BotLabelMiddleware(label_map)

        db_middleware = MultiDatabaseMiddleware(db_map)
        action_logger = ActionLoggerMiddleware()

        for middleware in (bot_label_middleware, db_middleware, action_logger):
            dp.message.middleware(middleware)
            dp.callback_query.middleware(middleware)
            dp.my_chat_member.middleware(middleware)
            dp.chat_join_request.middleware(middleware)

        dp.include_router(common_router.router)
        dp.include_router(user_router.router)

        admin_middleware = AdminMiddleware()
        admin_router.router.message.middleware(admin_middleware)
        admin_router.router.callback_query.middleware(admin_middleware)
        dp.include_router(admin_router.router)

        bots = [inst.bot for inst in instances]
        logger.info("bot_master запущен, polling %d ботов", len(bots))

        await dp.start_polling(*bots, allowed_updates=ALLOWED_UPDATES)

    except Exception as exc:
        logger.error("Критическая ошибка при запуске bot_master: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        for scheduler in schedulers:
            await scheduler.stop()
        for db in db_map.values():
            await db.disconnect()
        for inst in instances:
            await inst.bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("bot_master остановлен пользователем")
