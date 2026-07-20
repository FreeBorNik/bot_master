"""Реестр child-ботов из bot_sender."""
from bot.registry.loader import BotRegistry
from bot.registry.models import BotInstance

__all__ = ["BotInstance", "BotRegistry"]
