"""Мониторинг статуса child-ботов для control bot."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.registry.models import BotInstance

logger = logging.getLogger(__name__)


@dataclass
class BotHealthStatus:
    """Результат проверки одного child-бота."""

    instance: BotInstance
    is_online: bool
    checked_at: datetime
    error: Optional[str] = None
    db_exists: bool = True


@dataclass
class BotStatusService:
    """Сервис проверки и форматирования статуса child-ботов."""

    instances: list[BotInstance]
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _last_statuses: dict[int, BotHealthStatus] = field(default_factory=dict)

    async def check_one(self, instance: BotInstance) -> BotHealthStatus:
        """Проверить один бот через getMe()."""
        now = datetime.now(timezone.utc)
        db_exists = instance.db_path.exists()

        if not db_exists:
            return BotHealthStatus(
                instance=instance,
                is_online=False,
                checked_at=now,
                error="Файл БД не найден",
                db_exists=False,
            )

        try:
            me = await instance.bot.get_me()
            instance.first_name = me.first_name
            instance.username = me.username
            return BotHealthStatus(
                instance=instance,
                is_online=True,
                checked_at=now,
            )
        except TelegramAPIError as exc:
            return BotHealthStatus(
                instance=instance,
                is_online=False,
                checked_at=now,
                error=str(exc),
                db_exists=db_exists,
            )
        except Exception as exc:
            logger.exception(
                "Ошибка проверки бота %s",
                instance.display_name,
            )
            return BotHealthStatus(
                instance=instance,
                is_online=False,
                checked_at=now,
                error=str(exc),
                db_exists=db_exists,
            )

    async def check_all(self) -> tuple[list[BotHealthStatus], bool]:
        """Проверить все боты. Возвращает (статусы, были_ли_изменения)."""
        results: list[BotHealthStatus] = []
        changed = False

        for instance in self.instances:
            prev = self._last_statuses.get(instance.bot.id)
            status = await self.check_one(instance)

            if prev is None or prev.is_online != status.is_online or prev.error != status.error:
                changed = True

            results.append(status)
            self._last_statuses[instance.bot.id] = status

        return results, changed

    def format_report(
        self,
        statuses: list[BotHealthStatus],
        *,
        title: str = "Статус child-ботов",
    ) -> str:
        """HTML-отчёт для Telegram."""
        online = sum(1 for s in statuses if s.is_online)
        total = len(statuses)
        uptime = datetime.now(timezone.utc) - self.started_at
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)

        lines = [
            f"<b>{title}</b>",
            "",
            f"🟢 Онлайн: <b>{online}</b> / {total}",
            f"⏱ Uptime runner: <b>{hours}ч {minutes}м</b>",
            f"🕐 Проверка: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            "",
        ]

        if not statuses:
            lines.append("⚠️ Нет загруженных child-ботов.")
            return "\n".join(lines)

        for status in statuses:
            inst = status.instance
            icon = "🟢" if status.is_online else "🔴"
            lines.append(f"{icon} <b>{inst.display_name}</b>")
            lines.append(f"   ID: {inst.bot.id} | registry: {inst.registry_id}")

            db_icon = "✅" if status.db_exists else "❌"
            lines.append(f"   БД: {db_icon} <code>{inst.db_path}</code>")

            if status.is_online:
                lines.append("   Telegram: OK")
            elif status.error:
                lines.append(f"   Ошибка: {status.error}")
            lines.append("")

        lines.append("<i>Управление (старт/стоп/перезапуск) — в разработке.</i>")
        return "\n".join(lines)

    async def notify_admins(
        self,
        bot: Bot,
        admin_ids: set[int],
        text: str,
    ) -> None:
        """Отправить сообщение всем админам control bot."""
        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except TelegramAPIError as exc:
                logger.warning(
                    "Не удалось отправить статус админу %s: %s",
                    admin_id,
                    exc,
                )
