"""Подключение к базе данных."""
import aiosqlite
from typing import Optional
from pathlib import Path

from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class Database:
    """Класс для работы с базой данных SQLite."""

    def __init__(self, db_path: str | Path):
        """
        Инициализация подключения к БД.

        Args:
            db_path: Путь к файлу БД (обязателен)
        """
        self.db_path = str(db_path)
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Подключение к базе данных."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA busy_timeout=5000")
        logger.info("Подключение к БД установлено: %s", self.db_path)

    async def disconnect(self) -> None:
        """Закрытие подключения к базе данных."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Подключение к БД закрыто: %s", self.db_path)

    async def execute(self, query: str, parameters: tuple = ()) -> aiosqlite.Cursor:
        """Выполнение SQL запроса."""
        if not self._connection:
            await self.connect()

        cursor = await self._connection.execute(query, parameters)
        await self._connection.commit()
        return cursor

    async def executemany(self, query: str, parameters: list) -> aiosqlite.Cursor:
        """Выполнение SQL запроса с множественными параметрами."""
        if not self._connection:
            await self.connect()

        cursor = await self._connection.executemany(query, parameters)
        await self._connection.commit()
        return cursor

    async def fetchone(self, query: str, parameters: tuple = ()) -> Optional[aiosqlite.Row]:
        """Получение одной строки результата."""
        cursor = await self.execute(query, parameters)
        return await cursor.fetchone()

    async def fetchall(self, query: str, parameters: tuple = ()) -> list:
        """Получение всех строк результата."""
        cursor = await self.execute(query, parameters)
        return await cursor.fetchall()

    @property
    def connection(self) -> aiosqlite.Connection:
        """Получение объекта подключения."""
        if not self._connection:
            raise RuntimeError("База данных не подключена. Вызовите await db.connect()")
        return self._connection
