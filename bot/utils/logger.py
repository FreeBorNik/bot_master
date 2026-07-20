"""Настройка логирования."""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

_DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def setup_logger(
    name: str = "bot",
    log_file: Optional[str] = None,
    level: Optional[str] = None,
) -> logging.Logger:
    """
    Настройка логгера.

    Args:
        name: Имя логгера
        log_file: Путь к файлу логов (опционально)
        level: Уровень логирования (опционально)

    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    log_level = level or _DEFAULT_LEVEL
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def configure_root_logging(level: str, log_file: Optional[str] = None) -> None:
    """Единая настройка root-логгера при старте runner."""
    global _DEFAULT_LEVEL
    _DEFAULT_LEVEL = level
    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))
    if root.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
