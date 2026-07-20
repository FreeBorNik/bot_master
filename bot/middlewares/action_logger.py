"""Middleware для логирования действий пользователей."""
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from bot.database.db import Database
from bot.database.action_logs_repository import UserActionLogRepository
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class ActionLoggerMiddleware(BaseMiddleware):
    """Middleware для логирования всех действий пользователей."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        db: Database | None = data.get("db")
        if db is None:
            return await handler(event, data)

        log_repo = UserActionLogRepository(db)
        user = None
        user_id = None

        if isinstance(event, Message):
            user = event.from_user
            user_id = user.id if user else None

            if user_id:
                action_data = {
                    "message_id": event.message_id,
                    "chat_id": event.chat.id,
                    "chat_type": event.chat.type,
                    "has_photo": bool(event.photo),
                    "has_video": bool(event.video),
                    "has_document": bool(event.document),
                }

                if event.text:
                    if event.text.startswith("/"):
                        command = event.text.split()[0] if event.text else None
                        action_type = "command"
                        action_data["command"] = command

                        if command == "/start":
                            await handler(event, data)
                            return
                        if command == "/help":
                            action_type = "help_request"
                            action_data["description"] = "Запросил помощь"
                        elif command == "/cancel":
                            action_type = "cancel_action"
                            action_data["description"] = "Отменил действие"
                        else:
                            action_data["description"] = f"Выполнил команду {command}"
                    else:
                        action_type = "text_message"
                        action_data["description"] = "Написал сообщение"
                elif event.photo or event.video or event.document:
                    action_type = "media_message"
                    if event.photo:
                        action_data["description"] = "Отправил фото"
                    elif event.video:
                        action_data["description"] = "Отправил видео"
                    elif event.document:
                        action_data["description"] = "Отправил документ"
                else:
                    action_type = "message"
                    action_data["description"] = "Отправил сообщение"

                await log_repo.create_log(
                    user_id=user_id,
                    action_type=action_type,
                    message_text=event.text or event.caption,
                    action_data=action_data,
                )

        elif isinstance(event, CallbackQuery):
            user = event.from_user
            user_id = user.id if user else None

            if user_id:
                callback_data = event.data
                action_type = "button_click"
                action_description = None

                if callback_data == "check_subscription":
                    action_type = "subscription_check_button"
                    action_description = "Нажал кнопку 'Проверить подписку'"
                elif callback_data and callback_data.startswith("admin_"):
                    action_type = "admin_action"
                    action_description = f"Админ действие: {callback_data}"
                else:
                    action_description = f"Нажал кнопку: {callback_data}"

                action_data = {
                    "message_id": event.message.message_id if event.message else None,
                    "chat_id": event.message.chat.id if event.message else None,
                    "callback_data": callback_data,
                    "description": action_description,
                }

                await log_repo.create_log(
                    user_id=user_id,
                    action_type=action_type,
                    callback_data=callback_data,
                    message_text=action_description,
                    action_data=action_data,
                )

        return await handler(event, data)
