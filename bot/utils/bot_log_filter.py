"""Контекст child-бота в логах."""
import logging
from contextvars import ContextVar

_bot_label: ContextVar[str] = ContextVar("bot_label", default="master")


def set_bot_log_label(label: str) -> None:
    """Установить метку текущего бота для логов."""
    _bot_label.set(label)


class BotContextFilter(logging.Filter):
    """Добавляет префикс [bot_name] к сообщениям лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.bot_label = _bot_label.get()
        return True


class BotContextFormatter(logging.Formatter):
    """Форматтер с префиксом child-бота."""

    def format(self, record: logging.LogRecord) -> str:
        label = getattr(record, "bot_label", "master")
        original = record.msg
        record.msg = f"[{label}] {original}"
        try:
            return super().format(record)
        finally:
            record.msg = original
