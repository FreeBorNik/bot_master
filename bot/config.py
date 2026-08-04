"""Конфигурация multi-bot runner."""
import os
import re
from pathlib import Path

from dotenv import load_dotenv

# Корень репозитория (bot/config.py → ../), не зависеть от cwd systemd.
# override=True: .env побеждает EnvironmentFile — systemd обрезает значения на пробеле.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)


def _env_path(name: str) -> Path | None:
    """Путь из env; пустая строка → None (Path('') иначе становится '.')."""
    raw = os.getenv(name, "").strip().strip('"').strip("'")
    if not raw:
        return None
    return Path(raw)


def _parse_id_set(raw: str) -> frozenset[int]:
    """Telegram user_id из строки: '1, 2,3' или '1 2 3'."""
    return frozenset(int(x) for x in re.findall(r"\d+", raw or ""))


class RunnerConfig:
    """Настройки процесса bot_master (не per-bot)."""

    SENDER_DB_PATH: Path | None = _env_path("SENDER_DB_PATH")
    SENDER_ENCRYPTION_KEY: Path | None = _env_path("SENDER_ENCRYPTION_KEY")
    RECIPIENTS_DB_DIR: Path | None = _env_path("RECIPIENTS_DB_DIR")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Path = Path(os.getenv("LOG_FILE", "logs/bot_master.log"))
    MAILING_DELAY: float = float(os.getenv("MAILING_DELAY", "0.05"))

    CONTROL_BOT_TOKEN: str = os.getenv("CONTROL_BOT_TOKEN", "").strip()
    CONTROL_ADMIN_IDS: frozenset[int] = _parse_id_set(
        os.getenv("CONTROL_ADMIN_IDS", "")
    )
    ADMIN_IDS: frozenset[int] = _parse_id_set(os.getenv("ADMIN_IDS", ""))
    CONTROL_STATUS_INTERVAL: int = int(os.getenv("CONTROL_STATUS_INTERVAL", "300"))

    @classmethod
    def child_admin_ids(cls) -> frozenset[int]:
        """ID админов для таблицы admins в child SQLite (ADMIN_IDS ∪ CONTROL_ADMIN_IDS)."""
        return cls.ADMIN_IDS | cls.CONTROL_ADMIN_IDS

    @classmethod
    def control_bot_enabled(cls) -> bool:
        return bool(cls.CONTROL_BOT_TOKEN)

    @classmethod
    def validate(cls) -> None:
        """Проверка обязательных параметров runner."""
        if cls.SENDER_DB_PATH is None or not cls.SENDER_DB_PATH.is_file():
            raise ValueError(
                f"SENDER_DB_PATH не задан или это не файл: {cls.SENDER_DB_PATH!s}. "
                "Укажите абсолютный путь к bot_sender.db в .env"
            )
        if (
            cls.SENDER_ENCRYPTION_KEY is None
            or not cls.SENDER_ENCRYPTION_KEY.is_file()
        ):
            raise ValueError(
                f"SENDER_ENCRYPTION_KEY не задан или это не файл: "
                f"{cls.SENDER_ENCRYPTION_KEY!s}. "
                "Укажите абсолютный путь к encryption.key из bot_sender в .env"
            )

        if cls.CONTROL_BOT_TOKEN and not cls.CONTROL_ADMIN_IDS:
            raise ValueError(
                "CONTROL_BOT_TOKEN задан, но CONTROL_ADMIN_IDS пуст. "
                "Укажите Telegram user_id админов через запятую."
            )

        cls.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
