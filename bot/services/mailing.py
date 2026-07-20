"""Сервис рассылок."""
import asyncio
from typing import List, Optional
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import json

from bot.config import RunnerConfig
from bot.utils.helpers import parse_entities_from_json
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


async def send_mailing_message(
    bot: Bot,
    user_id: int,
    text: Optional[str] = None,
    media_type: Optional[str] = None,
    media_file_id: Optional[str] = None,
    entities_json: Optional[str] = None,
    buttons_json: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Отправка сообщения рассылки пользователю.
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        text: Текст сообщения
        media_type: Тип медиа ('photo', 'video')
        media_file_id: ID файла медиа
        entities_json: JSON строка с entities
        buttons_json: JSON строка с кнопками
    
    Returns:
        Кортеж (успех, текст ошибки)
    """
    try:
        # Парсим entities
        entities = parse_entities_from_json(entities_json)
        
        # Парсим кнопки
        reply_markup = None
        if buttons_json:
            try:
                buttons_data = json.loads(buttons_json)
                keyboard = []
                for row in buttons_data:
                    keyboard_row = []
                    for button_data in row:
                        if button_data.get("url"):
                            keyboard_row.append(
                                InlineKeyboardButton(
                                    text=button_data["text"],
                                    url=button_data["url"]
                                )
                            )
                        elif button_data.get("callback_data"):
                            keyboard_row.append(
                                InlineKeyboardButton(
                                    text=button_data["text"],
                                    callback_data=button_data["callback_data"]
                                )
                            )
                    if keyboard_row:
                        keyboard.append(keyboard_row)
                
                if keyboard:
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            except Exception as e:
                logger.warning(f"Ошибка парсинга кнопок: {e}")
        
        # Отправляем сообщение
        if media_type == "photo" and media_file_id:
            await bot.send_photo(
                chat_id=user_id,
                photo=media_file_id,
                caption=text,
                caption_entities=entities,
                reply_markup=reply_markup,
                parse_mode=None if entities else ParseMode.HTML
            )
        elif media_type == "video" and media_file_id:
            await bot.send_video(
                chat_id=user_id,
                video=media_file_id,
                caption=text,
                caption_entities=entities,
                reply_markup=reply_markup,
                parse_mode=None if entities else ParseMode.HTML
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=text or "Сообщение",
                entities=entities,
                reply_markup=reply_markup,
                parse_mode=None if entities else ParseMode.HTML,
                disable_web_page_preview=True
            )
        
        return True, None
        
    except Exception as e:
        error_text = str(e)
        error_lower = error_text.lower()
        
        # Проверяем, заблокирован ли бот пользователем
        is_blocked = (
            "bot was blocked" in error_lower or
            "user is deactivated" in error_lower or
            "chat not found" in error_lower or
            "forbidden" in error_lower
        )
        
        if is_blocked:
            # Логируем блокировку бота
            try:
                from bot.database.action_logs_repository import UserActionLogRepository
                from bot.database.db import Database
                # Получаем db из контекста или создаем новый экземпляр
                # В данном случае db передается в send_mailing_to_all_users
                # Но здесь мы не имеем доступа к db напрямую
                # Поэтому логирование блокировки будет в send_mailing_to_all_users
                pass
            except Exception:
                pass
        
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        return False, error_text


async def send_mailing_to_all_users(
    bot: Bot,
    db,
    mailing_message_id: int,
    delay: Optional[float] = None,
    scheduled_time: Optional[str] = None
) -> dict:
    """
    Отправка рассылки всем пользователям.
    
    Args:
        bot: Экземпляр бота
        db: База данных
        mailing_message_id: ID сообщения для рассылки
        delay: Задержка между сообщениями в секундах
    
    Returns:
        Словарь со статистикой рассылки
    """
    from bot.database.repositories import (
        MailingMessageRepository,
        MailingRepository,
        MailingLogRepository,
        UserRepository
    )
    
    delay = delay if delay is not None else RunnerConfig.MAILING_DELAY
    
    # Получаем сообщение для рассылки
    message_repo = MailingMessageRepository(db)
    mailing_message = await message_repo.get_mailing_message(mailing_message_id)
    
    if not mailing_message:
        return {"error": "Сообщение не найдено"}
    
    # Создаем запись о рассылке
    mailing_repo = MailingRepository(db)
    mailing = await mailing_repo.create_mailing(mailing_message_id, scheduled_time)
    
    # Получаем всех пользователей
    user_repo = UserRepository(db)
    users = await user_repo.get_all_users()
    
    log_repo = MailingLogRepository(db)
    
    sent_count = 0
    failed_count = 0
    
    # Репозиторий для логирования действий пользователей
    from bot.database.action_logs_repository import UserActionLogRepository
    action_log_repo = UserActionLogRepository(db)
    
    for user in users:
        try:
            success, error = await send_mailing_message(
                bot=bot,
                user_id=user.user_id,
                text=mailing_message.text,
                media_type=mailing_message.media_type,
                media_file_id=mailing_message.media_file_id,
                entities_json=mailing_message.entities_json,
                buttons_json=mailing_message.buttons_json
            )
            
            if success:
                sent_count += 1
                await log_repo.create_log(mailing.id, user.user_id, "sent")
            else:
                failed_count += 1
                await log_repo.create_log(mailing.id, user.user_id, "failed", error)
                
                # Проверяем, заблокирован ли бот
                if error:
                    error_lower = error.lower()
                    is_blocked = (
                        "bot was blocked" in error_lower or
                        "user is deactivated" in error_lower or
                        "chat not found" in error_lower or
                        "forbidden" in error_lower
                    )
                    
                    if is_blocked:
                        await user_repo.update_user_is_in_bot(user.user_id, False)
                        await action_log_repo.create_log(
                            user_id=user.user_id,
                            action_type="bot_blocked",
                            message_text="Заблокировал бота",
                            action_data={
                                "error": error,
                                "mailing_id": mailing.id,
                                "reason": "blocked_by_user"
                            }
                        )
            
            # Задержка между сообщениями
            await asyncio.sleep(delay)
            
        except Exception as e:
            failed_count += 1
            error_text = str(e)
            await log_repo.create_log(mailing.id, user.user_id, "failed", error_text)
            logger.error(f"Ошибка при отправке рассылки пользователю {user.user_id}: {e}")
    
    # Обновляем статистику рассылки
    await mailing_repo.update_mailing_stats(mailing.id, sent_count, failed_count)
    
    # Обновляем статус рассылки на "sent"
    await mailing_repo.update_mailing_status(mailing.id, "sent")
    
    return {
        "mailing_id": mailing.id,
        "sent": sent_count,
        "failed": failed_count,
        "total": len(users)
    }
