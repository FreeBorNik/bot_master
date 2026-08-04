"""Расшифровка токенов из bot_sender (read-only)."""
import base64
import logging
from pathlib import Path

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class TokenDecryptor:
    """Расшифровка токенов по ключу bot_sender."""

    def __init__(self, key_file: Path) -> None:
        if not key_file.is_file():
            raise FileNotFoundError(
                f"Ключ шифрования не найден или это не файл: {key_file}"
            )
        key = key_file.read_bytes()
        self._cipher = Fernet(key)
        logger.info("Ключ шифрования загружен из %s", key_file)

    def decrypt(self, encrypted_token: str) -> str:
        """Расшифровка токена из recipient_bots.bot_token."""
        encrypted_bytes = base64.b64decode(encrypted_token.encode("utf-8"))
        return self._cipher.decrypt(encrypted_bytes).decode("utf-8")
