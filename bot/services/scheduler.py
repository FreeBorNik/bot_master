"""Планировщик для автоматического запуска рассылок."""
import asyncio
from datetime import datetime
from typing import Optional

from aiogram import Bot

from bot.database.db import Database
from bot.database.repositories import MailingRepository
from bot.services.mailing import send_mailing_to_all_users
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class MailingScheduler:
    """Планировщик рассылок."""
    
    def __init__(self, bot: Bot, db: Database):
        """
        Инициализация планировщика.
        
        Args:
            bot: Экземпляр бота
            db: База данных
        """
        self.bot = bot
        self.db = db
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Запуск планировщика."""
        if self._running:
            logger.warning("Планировщик уже запущен")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Планировщик рассылок запущен")
    
    async def stop(self) -> None:
        """Остановка планировщика."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Планировщик рассылок остановлен")
    
    async def _scheduler_loop(self) -> None:
        """Основной цикл планировщика."""
        while self._running:
            try:
                await self._check_and_run_scheduled_mailings()
                # Проверяем каждую минуту
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _check_and_run_scheduled_mailings(self) -> None:
        """Проверка и запуск запланированных рассылок."""
        try:
            mailing_repo = MailingRepository(self.db)
            scheduled_mailings = await mailing_repo.get_scheduled_mailings()
            
            if not scheduled_mailings:
                return
            
            logger.info(f"Найдено {len(scheduled_mailings)} запланированных рассылок для запуска")
            
            for mailing in scheduled_mailings:
                try:
                    # Обновляем статус на "sending"
                    await mailing_repo.update_mailing_status(mailing.id, "sending")
                    
                    logger.info(f"Запуск запланированной рассылки {mailing.id}")
                    
                    # Запускаем рассылку
                    result = await send_mailing_to_all_users(
                        bot=self.bot,
                        db=self.db,
                        mailing_message_id=mailing.message_id,
                        scheduled_time=None  # Уже запланировано
                    )
                    
                    if "error" in result:
                        await mailing_repo.update_mailing_status(mailing.id, "failed")
                        logger.error(f"Ошибка при выполнении запланированной рассылки {mailing.id}: {result['error']}")
                    else:
                        logger.info(
                            f"Запланированная рассылка {mailing.id} завершена: "
                            f"отправлено {result['sent']}, ошибок {result['failed']}"
                        )
                    
                except Exception as e:
                    logger.error(f"Ошибка при выполнении запланированной рассылки {mailing.id}: {e}")
                    await mailing_repo.update_mailing_status(mailing.id, "failed")
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке запланированных рассылок: {e}")
