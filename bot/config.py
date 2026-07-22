"""Конфигурация multi-bot runner."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class RunnerConfig:
    """Настройки процесса bot_master (не per-bot)."""

    SENDER_DB_PATH: Path = Path(os.getenv("SENDER_DB_PATH", ""))
    SENDER_ENCRYPTION_KEY: Path = Path(os.getenv("SENDER_ENCRYPTION_KEY", ""))
    _recipients_db_dir: str = os.getenv("RECIPIENTS_DB_DIR", "").strip()
    RECIPIENTS_DB_DIR: Path | None = (
        Path(_recipients_db_dir) if _recipients_db_dir else None
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Path = Path(os.getenv("LOG_FILE", "logs/bot_master.log"))
    MAILING_DELAY: float = float(os.getenv("MAILING_DELAY", "0.05"))

    @classmethod
    def validate(cls) -> None:
        """Проверка обязательных параметров runner."""
        if not cls.SENDER_DB_PATH or not cls.SENDER_DB_PATH.exists():
            raise ValueError(
                f"SENDER_DB_PATH не найден: {cls.SENDER_DB_PATH}. "
                "Укажите путь к bot_sender.db"
            )
        if not cls.SENDER_ENCRYPTION_KEY or not cls.SENDER_ENCRYPTION_KEY.exists():
            raise ValueError(
                f"SENDER_ENCRYPTION_KEY не найден: {cls.SENDER_ENCRYPTION_KEY}. "
                "Укажите путь к encryption.key из bot_sender"
            )

        cls.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
