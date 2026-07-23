"""Control bot: мониторинг и управление runner (v1 — только статус)."""
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards.control_kb import get_control_main_keyboard
from bot.services.bot_status import BotStatusService
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)

router = Router(name="control")

_STATUS_SERVICE_KEY = "status_service"


def _get_status_service(data: dict) -> BotStatusService:
    service = data.get(_STATUS_SERVICE_KEY)
    if service is None:
        raise RuntimeError("BotStatusService не передан в data")
    return service


async def _send_status(message: Message, service: BotStatusService, title: str) -> None:
    statuses, _ = await service.check_all()
    text = service.format_report(statuses, title=title)
    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_control_main_keyboard(),
    )


@router.message(Command("start"))
async def cmd_start(message: Message, **data) -> None:
    """Приветствие и меню control bot."""
    service = _get_status_service(data)
    await message.answer(
        "🤖 <b>bot_master control</b>\n\n"
        "Мониторинг child-ботов runner'а.\n\n"
        "Команды:\n"
        "/status — статус всех ботов\n"
        "/ping — быстрая проверка\n"
        "/help — справка",
        parse_mode=ParseMode.HTML,
        reply_markup=get_control_main_keyboard(),
    )
    await _send_status(message, service, title="📊 Статус при старте")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>bot_master control</b>\n\n"
        "/status — полный статус child-ботов\n"
        "/ping — быстрая проверка доступности\n\n"
        "Автоуведомления приходят при старте runner и при "
        "изменении статуса бота.\n\n"
        "Управление (запуск/остановка/перезапуск) — в разработке.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_control_main_keyboard(),
    )


@router.message(Command("status"))
async def cmd_status(message: Message, **data) -> None:
    service = _get_status_service(data)
    await _send_status(message, service, title="📊 Статус child-ботов")


@router.message(Command("ping"))
async def cmd_ping(message: Message, **data) -> None:
    service = _get_status_service(data)
    statuses, _ = await service.check_all()
    online = sum(1 for s in statuses if s.is_online)
    total = len(statuses)
    icon = "🟢" if online == total and total > 0 else "🟡" if online > 0 else "🔴"
    await message.answer(
        f"{icon} Runner OK | ботов онлайн: <b>{online}/{total}</b>",
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "control_refresh")
async def cb_refresh(callback: CallbackQuery, **data) -> None:
    service = _get_status_service(data)
    statuses, _ = await service.check_all()
    text = service.format_report(statuses, title="📊 Статус child-ботов")
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_control_main_keyboard(),
    )
    await callback.answer("Обновлено")


@router.callback_query(F.data.startswith("control_stub_"))
async def cb_stub_action(callback: CallbackQuery) -> None:
    await callback.answer(
        "Управление ботами будет доступно в следующей версии.",
        show_alert=True,
    )
