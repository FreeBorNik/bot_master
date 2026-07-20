"""Модели реестра child-ботов."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aiogram import Bot


@dataclass
class BotInstance:
    """Один child-бот в multi-bot runner."""

    registry_id: int
    name: str
    token: str
    db_path: Path
    bot: Bot
    first_name: Optional[str] = None
    username: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Имя для логов и healthcheck."""
        if self.username:
            return f"{self.name} (@{self.username})"
        if self.first_name:
            return f"{self.name} ({self.first_name})"
        return self.name
