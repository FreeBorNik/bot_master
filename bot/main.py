"""Точка входа multi-bot runner."""
import asyncio
import logging
import signal
import sys
from contextlib import suppress
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import ErrorEvent

try:
    from aiogram.client.default import DefaultBotProperties
except ModuleNotFoundError:
    DefaultBotProperties = None  # aiogram < 3.2

from bot.config import RunnerConfig
from bot.database.db import Database
from bot.database.migrations import create_tables
from bot.database.repositories import UserRepository
from bot.handlers import admin_router, common_router, control_router, user_router
from bot.middlewares.action_logger import ActionLoggerMiddleware
from bot.middlewares.admin import AdminMiddleware
from bot.middlewares.bot_label import BotLabelMiddleware
from bot.middlewares.control_admin import ControlAdminMiddleware
from bot.middlewares.control_data import ControlDataMiddleware
from bot.middlewares.database import MultiDatabaseMiddleware
from bot.registry import BotRegistry
from bot.registry.models import BotInstance
from bot.services.bot_status import BotStatusService
from bot.services.scheduler import MailingScheduler
from bot.utils.bot_log_filter import BotContextFilter, BotContextFormatter
from bot.utils.instance_lock import acquire_instance_lock, release_instance_lock
from bot.utils.logger import configure_root_logging, setup_logger

logger = setup_logger(__name__)

ALLOWED_UPDATES = ["callback_query", "chat_join_request", "message", "my_chat_member"]
CONTROL_ALLOWED_UPDATES = ["callback_query", "message"]


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


def _create_control_bot() -> Bot:
    """Создать Bot для control bot."""
    if DefaultBotProperties is not None:
        return Bot(
            token=RunnerConfig.CONTROL_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return Bot(token=RunnerConfig.CONTROL_BOT_TOKEN)


def _setup_control_dispatcher(status_service: BotStatusService) -> Dispatcher:
    """Dispatcher только для control bot (без child handlers)."""
    dp = Dispatcher(storage=MemoryStorage())
    admin_ids = set(RunnerConfig.CONTROL_ADMIN_IDS)

    for middleware in (
        ControlAdminMiddleware(admin_ids),
        ControlDataMiddleware(status_service),
    ):
        dp.message.middleware(middleware)
        dp.callback_query.middleware(middleware)

    dp.include_router(control_router.router)
    return dp


async def _status_monitor_loop(
    status_service: BotStatusService,
    control_bot: Bot,
    stop_event: asyncio.Event,
) -> None:
    """Периодическая проверка и уведомление при изменении статуса."""
    interval = RunnerConfig.CONTROL_STATUS_INTERVAL
    if interval <= 0:
        return

    admin_ids = set(RunnerConfig.CONTROL_ADMIN_IDS)
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            return
        except asyncio.TimeoutError:
            pass

        statuses, changed = await status_service.check_all()
        if not changed:
            continue

        text = status_service.format_report(statuses, title="⚠️ Изменение статуса")
        await status_service.notify_admins(control_bot, admin_ids, text)


async def _notify_startup(
    status_service: BotStatusService,
    control_bot: Bot,
) -> None:
    """Уведомить админов о запуске runner."""
    statuses, _ = await status_service.check_all()
    text = status_service.format_report(statuses, title="✅ bot_master запущен")
    await status_service.notify_admins(
        control_bot,
        set(RunnerConfig.CONTROL_ADMIN_IDS),
        text,
    )


async def _stop_dispatcher_polling(dispatcher: Dispatcher | None) -> None:
    """Корректно остановить polling одного Dispatcher."""
    if dispatcher is None:
        return
    try:
        await dispatcher.stop_polling()
    except RuntimeError:
        pass


async def _graceful_shutdown(
    *,
    stop_event: asyncio.Event,
    polling_tasks: list[asyncio.Task],
    dp: Dispatcher | None,
    dp_control: Dispatcher | None,
    schedulers: list[MailingScheduler],
    db_map: dict[int, Database],
    instances: list[BotInstance],
    control_bot: Bot | None,
) -> None:
    """Остановить polling, планировщики и закрыть соединения."""
    stop_event.set()
    logger.info("Остановка bot_master...")

    await _stop_dispatcher_polling(dp)
    await _stop_dispatcher_polling(dp_control)

    for task in polling_tasks:
        if not task.done():
            task.cancel()
    if polling_tasks:
        await asyncio.gather(*polling_tasks, return_exceptions=True)

    for scheduler in schedulers:
        await scheduler.stop()

    for db in db_map.values():
        await db.disconnect()

    for inst in instances:
        with suppress(Exception):
            await inst.bot.session.close()

    if control_bot is not None:
        with suppress(Exception):
            await control_bot.session.close()

    logger.info("bot_master остановлен")


def _register_shutdown_signals(shutdown_event: asyncio.Event) -> None:
    """Единый обработчик SIGINT/SIGTERM (Unix). На Windows — через KeyboardInterrupt."""
    loop = asyncio.get_running_loop()

    def _request_shutdown() -> None:
        logger.info("Получен сигнал остановки")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _request_shutdown)


async def main() -> None:
    """Запуск multi-bot runner."""
    instances: list[BotInstance] = []
    db_map: dict[int, Database] = {}
    schedulers: list[MailingScheduler] = []
    control_bot: Bot | None = None
    stop_event = asyncio.Event()
    shutdown_event = asyncio.Event()
    polling_tasks: list[asyncio.Task] = []
    dp: Dispatcher | None = None
    dp_control: Dispatcher | None = None

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

        storage = MemoryStorage()
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

        _register_shutdown_signals(shutdown_event)

        polling_tasks.append(
            asyncio.create_task(
                dp.start_polling(
                    *bots,
                    allowed_updates=ALLOWED_UPDATES,
                    handle_signals=False,
                    close_bot_session=False,
                ),
                name="child_polling",
            )
        )

        if RunnerConfig.control_bot_enabled():
            status_service = BotStatusService(instances=instances)
            control_bot = _create_control_bot()
            dp_control = _setup_control_dispatcher(status_service)

            await _notify_startup(status_service, control_bot)

            polling_tasks.append(
                asyncio.create_task(
                    dp_control.start_polling(
                        control_bot,
                        allowed_updates=CONTROL_ALLOWED_UPDATES,
                        handle_signals=False,
                        close_bot_session=False,
                    ),
                    name="control_polling",
                )
            )
            polling_tasks.append(
                asyncio.create_task(
                    _status_monitor_loop(status_service, control_bot, stop_event),
                    name="status_monitor",
                )
            )
            logger.info("Control bot включён, админов: %d", len(RunnerConfig.CONTROL_ADMIN_IDS))

        logger.info("bot_master запущен, polling %d child-ботов", len(bots))

        shutdown_waiter = asyncio.create_task(shutdown_event.wait(), name="shutdown_waiter")
        polling_tasks.append(shutdown_waiter)

        done, _ = await asyncio.wait(
            polling_tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            if task.cancelled():
                continue
            with suppress(asyncio.CancelledError):
                exc = task.exception()
                if exc is not None:
                    raise exc

    except asyncio.CancelledError:
        logger.info("Прерывание bot_master (Ctrl+C)")
        raise
    except Exception as exc:
        logger.error("Критическая ошибка при запуске bot_master: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        await _graceful_shutdown(
            stop_event=stop_event,
            polling_tasks=polling_tasks,
            dp=dp,
            dp_control=dp_control,
            schedulers=schedulers,
            db_map=db_map,
            instances=instances,
            control_bot=control_bot,
        )


if __name__ == "__main__":
    acquire_instance_lock()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        release_instance_lock()
