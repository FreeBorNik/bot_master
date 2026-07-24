"""Реестр child-ботов из bot_sender."""
from bot.registry.loader import BotRegistry
from bot.registry.models import BotInstance, RegistryLoadResult

__all__ = ["BotInstance", "BotRegistry", "RegistryLoadResult"]
