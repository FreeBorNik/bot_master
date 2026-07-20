"""Сервис проверки подписки."""
from typing import List, Tuple, Optional
from aiogram import Bot

from bot.database.db import Database
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


async def check_user_subscription(
    bot: Bot,
    user_id: int,
    channels: List[Tuple[str, str]],
    db: Optional[Database] = None
) -> bool:
    """
    Проверка подписки пользователя на каналы/боты.
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        channels: Список кортежей (chat_id/username, type)
        db: База данных (опционально, для проверки подтверждённых подписок через chat_join_request)
    
    Returns:
        True если пользователь подписан на все каналы, иначе False
    """
    if not channels:
        return True
    
    # Получаем список приватных каналов, на которые пользователь подписался через chat_join_request
    private_subscriptions = set()
    confirmed_channels = {}  # {chat_id: invite_link или identifier}
    logs = []  # Логи для дополнительной проверки
    
    if db:
        try:
            from bot.database.action_logs_repository import UserActionLogRepository
            log_repo = UserActionLogRepository(db)
            
            # Ищем логи с типом "private_subscription_confirmed" для этого пользователя
            logs = await log_repo.get_user_logs(user_id, limit=1000)
            logger.debug(f"Найдено {len(logs)} логов для пользователя {user_id}")
            
            # Подсчитываем логи подтверждения подписки
            confirmed_count = sum(1 for log in logs if log.action_type == "private_subscription_confirmed")
            logger.debug(f"Найдено {confirmed_count} подтверждений подписки для пользователя {user_id}")
            for log in logs:
                if log.action_type == "private_subscription_confirmed" and log.action_data:
                    import json
                    try:
                        data = json.loads(log.action_data)
                        # Поддерживаем разные форматы данных
                        channel_id = data.get("channel_id")
                        channel_invite = data.get("channel_invite")
                        channel_identifier = data.get("channel_identifier")
                        invite_link = data.get("invite_link")
                        
                        # Сохраняем информацию о канале
                        logger.debug(f"Обработка лога подтверждения: channel_id={channel_id}, channel_invite={channel_invite}, channel_identifier={channel_identifier}, invite_link={invite_link}")
                        
                        if channel_id:
                            # Используем invite_link или channel_identifier для идентификации
                            identifier = channel_invite or channel_identifier or invite_link
                            if identifier:
                                confirmed_channels[channel_id] = identifier
                                logger.debug(f"Добавлено в confirmed_channels: {channel_id} -> {identifier}")
                                if identifier.startswith("+"):
                                    private_subscriptions.add(identifier)
                                    logger.debug(f"Добавлено в private_subscriptions: {identifier}")
                        elif channel_invite:
                            private_subscriptions.add(channel_invite)
                            logger.debug(f"Добавлено в private_subscriptions (channel_invite): {channel_invite}")
                        elif channel_identifier and (channel_identifier.startswith("+") or channel_identifier.startswith("@")):
                            private_subscriptions.add(channel_identifier)
                            logger.debug(f"Добавлено в private_subscriptions (channel_identifier): {channel_identifier}")
                        elif invite_link and invite_link.startswith("+"):
                            private_subscriptions.add(invite_link)
                            logger.debug(f"Добавлено в private_subscriptions (invite_link): {invite_link}")
                    except Exception as e:
                        logger.error(f"Ошибка при парсинге action_data: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке приватных подписок: {e}")
    
    for chat_id_or_username, channel_type in channels:
        try:
            # Если это invite-ссылка (начинается с +), проверяем подтверждение подписки
            if chat_id_or_username.startswith("+"):
                logger.debug(
                    f"Проверка приватного канала {chat_id_or_username}: "
                    f"private_subscriptions={list(private_subscriptions)}, "
                    f"confirmed_channels={list(confirmed_channels.keys())}"
                )

                # Проверяем, есть ли подтверждение подписки через chat_join_request
                if chat_id_or_username in private_subscriptions:
                    logger.info(
                        f"✅ Пользователь {user_id} подписан на приватный канал {chat_id_or_username} "
                        f"(подтверждено через запрос на вступление, найдено по invite-ссылке)"
                    )
                    continue

                # Также проверяем по chat_id, если он есть в логах
                try:
                    chat = await bot.get_chat(chat_id_or_username)
                    chat_id_str = str(chat.id)

                    logger.debug(
                        f"Проверка подписки для канала {chat_id_or_username}: "
                        f"chat_id={chat_id_str}, confirmed_channels={list(confirmed_channels.keys())}"
                    )

                    if chat_id_str in confirmed_channels:
                        logger.info(
                            f"Пользователь {user_id} подписан на приватный канал {chat_id_or_username} "
                            f"(подтверждено через chat_join_request, chat_id: {chat_id_str})"
                        )
                        continue

                    found_in_logs = False
                    for log in logs:
                        if log.action_type == "private_subscription_confirmed" and log.action_data:
                            import json
                            try:
                                data = json.loads(log.action_data)
                                if data.get("channel_id") == chat_id_str:
                                    logger.info(
                                        f"Пользователь {user_id} подписан на приватный канал {chat_id_or_username} "
                                        f"(подтверждено через chat_join_request, найден по chat_id: {chat_id_str})"
                                    )
                                    found_in_logs = True
                                    break
                            except Exception:
                                pass

                    if found_in_logs:
                        continue
                except Exception as e:
                    logger.debug(f"Не удалось получить chat_id для {chat_id_or_username}: {e}")

                logger.info(
                    f"Пользователь {user_id} не подтвердил подписку на приватный канал {chat_id_or_username}"
                )
                return False
            
            # Формируем правильный идентификатор
            chat_identifier = chat_id_or_username
            if not chat_id_or_username.startswith("@") and not chat_id_or_username.startswith("-"):
                # Если это username без @, добавляем @
                if not chat_id_or_username.isdigit():
                    chat_identifier = f"@{chat_id_or_username}"
            
            member = await bot.get_chat_member(
                chat_id=chat_identifier,
                user_id=user_id
            )
            
            # Проверка статуса подписки
            if member.status in ["left", "kicked"]:
                logger.info(
                    f"Пользователь {user_id} не подписан на {chat_id_or_username}"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Ошибка при проверке подписки на {chat_id_or_username}: {e}"
            )
            # Для приватных каналов или если бот не админ, возвращаем False
            return False
    
    return True
