"""Репозитории для работы с данными."""
import json
from typing import Optional
from datetime import datetime

from bot.database.db import Database
from bot.database.models import (
    User,
    StartMessage,
    WelcomeMessage,
    SimpleWelcomeMessage,
    ChannelsListMessage,
    NoQuestionnaireMessage,
    PostQuestionnaireMessage,
    ChainMessage,
    Channel,
    MailingMessage,
    Mailing,
    MailingLog,
    BotSettings,
)
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserRepository:
    """Репозиторий для работы с пользователями."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """
        Получение пользователя по ID.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Объект User или None
        """
        row = await self.db.fetchone(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        if row:
            is_in_bot = row["is_in_bot"] if "is_in_bot" in row.keys() else 1
            if is_in_bot is None:
                is_in_bot = 1  # старые записи без колонки считаем «в боте»
            return User(
                user_id=row["user_id"],
                username=row["username"],
                full_name=row["full_name"],
                age=row["age"],
                hours_per_day=row["hours_per_day"],
                has_other_job=bool(row["has_other_job"]) if row["has_other_job"] is not None else None,
                is_subscribed=bool(row["is_subscribed"]),
                is_in_bot=bool(is_in_bot),
                created_at=row["created_at"]
            )
        return None
    
    async def create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> User:
        """
        Создание нового пользователя.
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            full_name: Полное имя
        
        Returns:
            Созданный объект User
        """
        await self.db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, full_name, is_in_bot)
               VALUES (?, ?, ?, 1)""",
            (user_id, username, full_name)
        )

        # Обновление данных при каждом /start (в т.ч. возврат после блокировки — снова «в боте»)
        await self.db.execute(
            """UPDATE users SET username = ?, full_name = ?, is_in_bot = 1
               WHERE user_id = ?""",
            (username, full_name, user_id)
        )
        
        user = await self.get_user(user_id)
        if not user:
            raise RuntimeError("Не удалось создать пользователя")
        
        logger.info(f"Создан/обновлен пользователь {user_id}")
        return user
    
    async def update_user_questionnaire(
        self,
        user_id: int,
        age: str | int,
        hours_per_day: str | int,
        has_other_job: bool
    ) -> None:
        """
        Обновление данных анкеты пользователя.
        
        Args:
            user_id: ID пользователя
            age: Возраст (может быть строкой с диапазоном или числом)
            hours_per_day: Часов в день (может быть строкой с диапазоном или числом)
            has_other_job: Есть ли другая работа
        """
        await self.db.execute(
            """UPDATE users 
               SET age = ?, hours_per_day = ?, has_other_job = ?
               WHERE user_id = ?""",
            (str(age), str(hours_per_day), 1 if has_other_job else 0, user_id)
        )
        logger.info(f"Обновлена анкета пользователя {user_id}")

    async def clear_questionnaire(self, user_id: int) -> None:
        """
        Сброс данных анкеты (при повторном входе после блокировки — запуск алгоритма как для нового пользователя).
        """
        await self.db.execute(
            """UPDATE users SET age = NULL, hours_per_day = NULL, has_other_job = NULL
               WHERE user_id = ?""",
            (user_id,)
        )
        logger.info(f"Сброшена анкета пользователя {user_id} (повторный вход)")
    
    async def set_subscription_status(self, user_id: int, is_subscribed: bool) -> None:
        """
        Установка статуса подписки пользователя.
        
        Args:
            user_id: ID пользователя
            is_subscribed: Статус подписки
        """
        await self.db.execute(
            "UPDATE users SET is_subscribed = ? WHERE user_id = ?",
            (1 if is_subscribed else 0, user_id)
        )

    async def update_user_is_in_bot(self, user_id: int, is_in_bot: bool) -> None:
        """
        Установка статуса «пользователь в боте» (False — заблокировал бота).
        При повторном /start считаем вход как первый.
        """
        await self.db.execute(
            "UPDATE users SET is_in_bot = ? WHERE user_id = ?",
            (1 if is_in_bot else 0, user_id)
        )
        logger.info(f"Пользователь {user_id}: is_in_bot={is_in_bot}")

    async def get_all_users(self) -> list[User]:
        """
        Получение всех пользователей.
        
        Returns:
            Список пользователей
        """
        rows = await self.db.fetchall("SELECT * FROM users")
        
        users = []
        for row in rows:
            is_in_bot_val = row["is_in_bot"] if "is_in_bot" in row.keys() else 1
            users.append(User(
                user_id=row["user_id"],
                username=row["username"],
                full_name=row["full_name"],
                age=row["age"],
                hours_per_day=row["hours_per_day"],
                has_other_job=bool(row["has_other_job"]) if row["has_other_job"] is not None else None,
                is_subscribed=bool(row["is_subscribed"]),
                is_in_bot=bool(is_in_bot_val),
                created_at=row["created_at"]
            ))
        
        return users


class StartMessageRepository:
    """Репозиторий для работы с сообщениями после команды /start."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def get_start_message(self) -> Optional[StartMessage]:
        """
        Получение текущего активного сообщения после /start.
        Используется для отправки пользователям.
        
        Returns:
            Объект StartMessage или None
        """
        row = await self.db.fetchone(
            "SELECT * FROM start_messages WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        
        if row:
            is_active_value = row["is_active"] if "is_active" in row.keys() else 1
            return StartMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                is_active=bool(is_active_value),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return None
    
    async def get_latest_start_message(self) -> Optional[StartMessage]:
        """
        Получение последнего сообщения после /start независимо от статуса.
        Используется в админ-панели для управления.
        
        Returns:
            Объект StartMessage или None
        """
        row = await self.db.fetchone(
            "SELECT * FROM start_messages ORDER BY id DESC LIMIT 1"
        )
        
        if row:
            is_active_value = row["is_active"] if "is_active" in row.keys() else 1
            return StartMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                is_active=bool(is_active_value),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return None
    
    async def create_or_update_start_message(
        self,
        text: str,
        entities_json: Optional[str] = None
    ) -> StartMessage:
        """
        Создание нового сообщения после /start.
        Предыдущее активное сообщение деактивируется.
        
        Args:
            text: Текст сообщения
            entities_json: JSON строка с entities
        
        Returns:
            Созданный объект StartMessage
        """
        # Деактивируем все предыдущие активные сообщения
        await self.db.execute(
            "UPDATE start_messages SET is_active = 0 WHERE is_active = 1"
        )
        
        # Создаем новое активное сообщение
        await self.db.execute(
            """INSERT INTO start_messages (text, entities_json, is_active)
               VALUES (?, ?, 1)""",
            (text, entities_json)
        )
        logger.info("Создано новое активное сообщение после /start (предыдущие деактивированы)")
        
        return await self.get_start_message()
    
    async def toggle_active(self, is_active: bool) -> None:
        """
        Включение/отключение сообщения после /start.
        Обновляет последнее сообщение независимо от текущего статуса.
        
        Args:
            is_active: True для включения, False для отключения
        """
        # Если включаем, деактивируем все остальные активные сообщения
        if is_active:
            await self.db.execute(
                "UPDATE start_messages SET is_active = 0 WHERE is_active = 1"
            )
        
        # Обновляем последнее сообщение
        await self.db.execute(
            "UPDATE start_messages SET is_active = ? WHERE id = (SELECT id FROM start_messages ORDER BY id DESC LIMIT 1)",
            (1 if is_active else 0,)
        )
        logger.info(f"Сообщение после /start {'включено' if is_active else 'отключено'}")


class WelcomeMessageRepository:
    """Репозиторий для работы с приветственными сообщениями."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def get_welcome_message(self) -> Optional[WelcomeMessage]:
        """
        Получение текущего активного приветственного сообщения.
        
        Returns:
            Объект WelcomeMessage или None
        """
        row = await self.db.fetchone(
            "SELECT * FROM welcome_messages WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        
        if row:
            is_active_value = row["is_active"] if "is_active" in row.keys() else 1
            return WelcomeMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                is_active=bool(is_active_value),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return None
    
    async def get_active_welcome_message_id(self) -> Optional[int]:
        """
        Получение ID активного приветственного сообщения.
        
        Returns:
            ID активного сообщения или None
        """
        row = await self.db.fetchone(
            "SELECT id FROM welcome_messages WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        return row["id"] if row else None
    
    async def create_or_update_welcome_message(
        self,
        text: str,
        entities_json: Optional[str] = None
    ) -> WelcomeMessage:
        """
        Создание нового приветственного сообщения.
        Предыдущее активное сообщение деактивируется.
        
        Args:
            text: Текст сообщения
            entities_json: JSON строка с entities
        
        Returns:
            Созданный объект WelcomeMessage
        """
        # Деактивируем все предыдущие активные сообщения
        await self.db.execute(
            "UPDATE welcome_messages SET is_active = 0 WHERE is_active = 1"
        )
        
        # Создаем новое активное сообщение
        await self.db.execute(
            """INSERT INTO welcome_messages (text, entities_json, is_active)
               VALUES (?, ?, 1)""",
            (text, entities_json)
        )
        logger.info("Создано новое активное приветственное сообщение (предыдущие деактивированы)")
        
        return await self.get_welcome_message()


class SimpleWelcomeMessageRepository:
    """Приветствие в режиме «анкета первой» (текст + кнопка «Заполнить анкету»)."""

    def __init__(self, db: Database):
        self.db = db

    async def get_simple_welcome_message(self) -> Optional[SimpleWelcomeMessage]:
        row = await self.db.fetchone(
            "SELECT * FROM simple_welcome_messages WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        if row:
            return SimpleWelcomeMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                is_active=bool(row["is_active"] if "is_active" in row.keys() else 1),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        return None

    async def create_or_update(self, text: str, entities_json: Optional[str] = None) -> SimpleWelcomeMessage:
        await self.db.execute("UPDATE simple_welcome_messages SET is_active = 0 WHERE is_active = 1")
        await self.db.execute(
            """INSERT INTO simple_welcome_messages (text, entities_json, is_active)
               VALUES (?, ?, 1)""",
            (text, entities_json),
        )
        return (await self.get_simple_welcome_message()) or SimpleWelcomeMessage(text=text, entities_json=entities_json)


class ChannelsListMessageRepository:
    """Сообщение со списком каналов (после анкеты в режиме questionnaire_first)."""

    def __init__(self, db: Database):
        self.db = db

    async def get_channels_list_message(self) -> Optional[ChannelsListMessage]:
        row = await self.db.fetchone(
            "SELECT * FROM channels_list_messages WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        if row:
            return ChannelsListMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                is_active=bool(row["is_active"] if "is_active" in row.keys() else 1),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        return None

    async def create_or_update(self, text: str, entities_json: Optional[str] = None) -> ChannelsListMessage:
        await self.db.execute("UPDATE channels_list_messages SET is_active = 0 WHERE is_active = 1")
        await self.db.execute(
            """INSERT INTO channels_list_messages (text, entities_json, is_active)
               VALUES (?, ?, 1)""",
            (text, entities_json),
        )
        return (await self.get_channels_list_message()) or ChannelsListMessage(text=text, entities_json=entities_json)


class NoQuestionnaireMessageRepository:
    """Приветствие в режиме «без анкеты» (текст + кнопка «Проверить подписку»)."""

    def __init__(self, db: Database):
        self.db = db

    async def get_no_questionnaire_message(self) -> Optional[NoQuestionnaireMessage]:
        row = await self.db.fetchone(
            "SELECT * FROM no_questionnaire_messages WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        if row:
            return NoQuestionnaireMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                is_active=bool(row["is_active"] if "is_active" in row.keys() else 1),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        return None

    async def create_or_update(self, text: str, entities_json: Optional[str] = None) -> NoQuestionnaireMessage:
        await self.db.execute("UPDATE no_questionnaire_messages SET is_active = 0 WHERE is_active = 1")
        await self.db.execute(
            """INSERT INTO no_questionnaire_messages (text, entities_json, is_active)
               VALUES (?, ?, 1)""",
            (text, entities_json),
        )
        return (await self.get_no_questionnaire_message()) or NoQuestionnaireMessage(text=text, entities_json=entities_json)


class PostQuestionnaireMessageRepository:
    """Репозиторий для работы с сообщением после анкеты."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_post_questionnaire_message(self) -> Optional[PostQuestionnaireMessage]:
        """
        Получение текущего активного сообщения после анкеты.
        
        Returns:
            Объект PostQuestionnaireMessage или None
        """
        row = await self.db.fetchone(
            "SELECT * FROM post_questionnaire_messages WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        if row:
            is_active_val = row["is_active"] if "is_active" in row.keys() else 1
            return PostQuestionnaireMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                media_type=row["media_type"],
                media_file_id=row["media_file_id"],
                buttons_json=row["buttons_json"],
                is_active=bool(is_active_val),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return None

    async def get_latest_post_questionnaire_message(self) -> Optional[PostQuestionnaireMessage]:
        """
        Получение последнего сообщения после анкеты (для админки, с любым статусом).
        """
        row = await self.db.fetchone(
            "SELECT * FROM post_questionnaire_messages ORDER BY id DESC LIMIT 1"
        )
        if row:
            is_active_val = row["is_active"] if "is_active" in row.keys() else 1
            return PostQuestionnaireMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                media_type=row["media_type"],
                media_file_id=row["media_file_id"],
                buttons_json=row["buttons_json"],
                is_active=bool(is_active_val),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return None

    async def create_or_update_post_questionnaire_message(
        self,
        text: str,
        entities_json: Optional[str] = None,
        media_type: Optional[str] = None,
        media_file_id: Optional[str] = None,
        buttons_json: Optional[str] = None
    ) -> PostQuestionnaireMessage:
        """
        Создание нового сообщения после анкеты. Предыдущее активное деактивируется.
        """
        await self.db.execute(
            "UPDATE post_questionnaire_messages SET is_active = 0 WHERE is_active = 1"
        )
        await self.db.execute(
            """INSERT INTO post_questionnaire_messages
               (text, entities_json, media_type, media_file_id, buttons_json, is_active)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (text, entities_json, media_type, media_file_id, buttons_json)
        )
        logger.info("Создано новое активное сообщение после анкеты (предыдущие деактивированы)")
        return await self.get_post_questionnaire_message()

    async def toggle_post_questionnaire_status(self, message_id: int, is_active: bool) -> None:
        """Переключение статуса сообщения после анкеты."""
        if is_active:
            await self.db.execute(
                "UPDATE post_questionnaire_messages SET is_active = 0 WHERE is_active = 1"
            )
        await self.db.execute(
            "UPDATE post_questionnaire_messages SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, message_id)
        )
        logger.info(f"Сообщение после анкеты id={message_id} установлено is_active={is_active}")


class ChainMessageRepository:
    """Репозиторий для работы с цепочкой сообщений."""

    _DEFAULT_DELAYS = {1: 10, 2: 20, 3: 30}

    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def get_default_delay(message_number: int, existing_msg: Optional[ChainMessage] = None) -> int:
        """Дефолтный интервал для сообщения цепочки."""
        if existing_msg:
            return existing_msg.delay_minutes
        return ChainMessageRepository._DEFAULT_DELAYS.get(message_number, 10)

    async def get_chain_is_active(self) -> bool:
        """Цепочка в целом активна (отправлять сообщения) или нет."""
        try:
            row = await self.db.fetchone("SELECT is_active FROM chain_settings WHERE id = 1")
            if row is not None and "is_active" in row.keys():
                return bool(row["is_active"])
            return False  # нет строки — цепочка неактивна (безопасно по умолчанию)
        except Exception as e:
            logger.warning(f"Ошибка чтения chain_settings, цепочка считается неактивной: {e}")
            return False

    async def set_chain_is_active(self, is_active: bool) -> None:
        """Включить/выключить цепочку целиком."""
        await self.db.execute(
            "UPDATE chain_settings SET is_active = ? WHERE id = 1",
            (1 if is_active else 0,)
        )
        logger.info(f"Цепочка сообщений установлена is_active={is_active}")

    async def get_flow_order(self) -> list[int]:
        """
        Порядок типов сообщений: 1=Приветствие, 2=Старт анкеты, 3=Сообщение после анкеты, 4=Цепочка.
        Returns список из 4 элементов, например [1, 2, 3, 4].
        """
        try:
            row = await self.db.fetchone("SELECT flow_order FROM chain_settings WHERE id = 1")
            if row and "flow_order" in row.keys() and row["flow_order"]:
                order = json.loads(row["flow_order"])
                if isinstance(order, list) and len(order) == 4 and set(order) == {1, 2, 3, 4}:
                    return order
        except Exception as e:
            logger.warning(f"Ошибка чтения flow_order: {e}")
        return [1, 2, 3, 4]

    async def set_flow_order(self, order: list[int]) -> None:
        """Установить порядок типов сообщений (перестановка [1,2,3,4])."""
        if not (isinstance(order, list) and len(order) == 4 and set(order) == {1, 2, 3, 4}):
            raise ValueError("order должен быть перестановкой [1,2,3,4]")
        await self.db.execute(
            "UPDATE chain_settings SET flow_order = ? WHERE id = 1",
            (json.dumps(order),)
        )
        logger.info(f"Установлен порядок сообщений: {order}")

    async def get_all_chain_messages(self) -> list[ChainMessage]:
        """
        Получение всех сообщений цепочки, отсортированных по номеру.
        
        Returns:
            Список сообщений цепочки
        """
        rows = await self.db.fetchall(
            "SELECT * FROM chain_messages ORDER BY message_number ASC"
        )
        
        messages = []
        for row in rows:
            is_active_val = row["is_active"] if "is_active" in row.keys() else 1
            messages.append(ChainMessage(
                id=row["id"],
                message_number=row["message_number"],
                text=row["text"],
                entities_json=row["entities_json"],
                media_type=row["media_type"],
                media_file_id=row["media_file_id"],
                buttons_json=row["buttons_json"],
                delay_minutes=row["delay_minutes"],
                is_active=bool(is_active_val),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))
        return messages

    async def get_active_chain_messages(self) -> list[ChainMessage]:
        """
        Получение активных сообщений цепочки, отсортированных по номеру.
        
        Returns:
            Список активных сообщений цепочки
        """
        rows = await self.db.fetchall(
            "SELECT * FROM chain_messages WHERE is_active = 1 ORDER BY message_number ASC"
        )
        
        messages = []
        for row in rows:
            is_active_val = row["is_active"] if "is_active" in row.keys() else 1
            messages.append(ChainMessage(
                id=row["id"],
                message_number=row["message_number"],
                text=row["text"],
                entities_json=row["entities_json"],
                media_type=row["media_type"],
                media_file_id=row["media_file_id"],
                buttons_json=row["buttons_json"],
                delay_minutes=row["delay_minutes"],
                is_active=bool(is_active_val),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))
        return messages

    async def get_next_message_number(self) -> int:
        """Следующий номер сообщения в цепочке (max + 1 или 1)."""
        row = await self.db.fetchone("SELECT MAX(message_number) AS max_num FROM chain_messages")
        if row and row["max_num"] is not None:
            return int(row["max_num"]) + 1
        return 1

    async def delete_chain_message(self, message_number: int) -> bool:
        """Удаление сообщения цепочки с перенумерацией последующих."""
        existing = await self.get_chain_message(message_number)
        if not existing:
            return False
        await self.db.execute(
            "DELETE FROM chain_messages WHERE message_number = ?",
            (message_number,),
        )
        await self.db.execute(
            "UPDATE chain_messages SET message_number = message_number - 1 WHERE message_number > ?",
            (message_number,),
        )
        logger.info(f"Удалено сообщение цепочки #{message_number}, выполнена перенумерация")
        return True

    async def get_chain_message(self, message_number: int) -> Optional[ChainMessage]:
        """
        Получение сообщения цепочки по номеру.
        
        Args:
            message_number: Порядковый номер сообщения в цепочке
        
        Returns:
            Объект ChainMessage или None
        """
        row = await self.db.fetchone(
            "SELECT * FROM chain_messages WHERE message_number = ?",
            (message_number,)
        )
        
        if row:
            is_active_val = row["is_active"] if "is_active" in row.keys() else 1
            return ChainMessage(
                id=row["id"],
                message_number=row["message_number"],
                text=row["text"],
                entities_json=row["entities_json"],
                media_type=row["media_type"],
                media_file_id=row["media_file_id"],
                buttons_json=row["buttons_json"],
                delay_minutes=row["delay_minutes"],
                is_active=bool(is_active_val),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return None

    async def toggle_chain_message_status(self, message_number: int, is_active: bool) -> None:
        """Переключить статус сообщения цепочки (активно/неактивно)."""
        await self.db.execute(
            "UPDATE chain_messages SET is_active = ? WHERE message_number = ?",
            (1 if is_active else 0, message_number)
        )
        logger.info(f"Сообщение цепочки #{message_number} установлено is_active={is_active}")

    async def update_chain_message_delay(self, message_number: int, delay_minutes: int) -> None:
        """Обновить только интервал (delay_minutes) для сообщения цепочки."""
        await self.db.execute(
            "UPDATE chain_messages SET delay_minutes = ?, updated_at = CURRENT_TIMESTAMP WHERE message_number = ?",
            (delay_minutes, message_number)
        )
        logger.info(f"Обновлён интервал сообщения цепочки #{message_number}: {delay_minutes} мин.")

    async def create_or_update_chain_message(
        self,
        message_number: int,
        text: str,
        delay_minutes: int,
        entities_json: Optional[str] = None,
        media_type: Optional[str] = None,
        media_file_id: Optional[str] = None,
        buttons_json: Optional[str] = None,
        is_active: bool = True
    ) -> ChainMessage:
        """
        Создание или обновление сообщения цепочки.
        
        Args:
            message_number: Порядковый номер сообщения в цепочке
            text: Текст сообщения
            delay_minutes: Задержка в минутах после предыдущего сообщения
            entities_json: JSON строка с entities
            media_type: Тип медиа
            media_file_id: ID файла медиа
            buttons_json: JSON строка с кнопками
            is_active: Активно ли сообщение
        
        Returns:
            Созданный/обновленный объект ChainMessage
        """
        existing = await self.get_chain_message(message_number)
        
        if existing:
            # Обновляем существующее
            await self.db.execute(
                """UPDATE chain_messages 
                   SET text = ?, entities_json = ?, media_type = ?, 
                       media_file_id = ?, buttons_json = ?, delay_minutes = ?,
                       is_active = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE message_number = ?""",
                (text, entities_json, media_type, media_file_id, buttons_json,
                 delay_minutes, 1 if is_active else 0, message_number)
            )
            logger.info(f"Обновлено сообщение цепочки #{message_number}")
        else:
            # Создаем новое
            await self.db.execute(
                """INSERT INTO chain_messages 
                   (message_number, text, entities_json, media_type, media_file_id, 
                    buttons_json, delay_minutes, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (message_number, text, entities_json, media_type, media_file_id,
                 buttons_json, delay_minutes, 1 if is_active else 0)
            )
            logger.info(f"Создано сообщение цепочки #{message_number}")
        
        return await self.get_chain_message(message_number)


class ChannelRepository:
    """Репозиторий для работы с каналами."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def get_all_channels(self) -> list[Channel]:
        """
        Получение всех каналов для проверки подписки.
        
        Returns:
            Список каналов
        """
        rows = await self.db.fetchall("SELECT * FROM channels ORDER BY id")
        
        channels = []
        for row in rows:
            # Проверяем наличие поля check_subscription (для совместимости со старыми БД)
            check_subscription = 1
            if "check_subscription" in row.keys():
                check_subscription = row["check_subscription"]
            else:
                check_subscription = 1  # По умолчанию проверяем
            
            channels.append(Channel(
                id=row["id"],
                chat_id=row["chat_id"],
                username=row["username"],
                title=row["title"],
                type=row["type"],
                check_subscription=bool(check_subscription),
                created_at=row["created_at"]
            ))
        
        return channels
    
    async def add_channel(
        self,
        chat_id: Optional[str] = None,
        username: Optional[str] = None,
        title: Optional[str] = None,
        channel_type: str = "channel",
        check_subscription: bool = True
    ) -> Channel:
        """
        Добавление канала для проверки подписки.
        
        Args:
            chat_id: ID чата
            username: Username канала
            title: Название канала
            channel_type: Тип ('channel' или 'bot')
            check_subscription: Нужно ли проверять подписку на этот канал
        
        Returns:
            Созданный объект Channel
        """
        await self.db.execute(
            """INSERT OR IGNORE INTO channels (chat_id, username, title, type, check_subscription)
               VALUES (?, ?, ?, ?, ?)""",
            (chat_id, username, title, channel_type, 1 if check_subscription else 0)
        )
        
        # Получаем созданный канал
        if chat_id:
            row = await self.db.fetchone(
                "SELECT * FROM channels WHERE chat_id = ?",
                (chat_id,)
            )
        elif username:
            row = await self.db.fetchone(
                "SELECT * FROM channels WHERE username = ?",
                (username,)
            )
        else:
            raise ValueError("Необходимо указать chat_id или username")
        
        if row:
            logger.info(f"Добавлен канал: {username or chat_id} (проверка подписки: {check_subscription})")
            check_subscription_value = 1
            if "check_subscription" in row.keys():
                check_subscription_value = row["check_subscription"]
            return Channel(
                id=row["id"],
                chat_id=row["chat_id"],
                username=row["username"],
                title=row["title"],
                type=row["type"],
                check_subscription=bool(check_subscription_value),
                created_at=row["created_at"]
            )
        raise RuntimeError("Не удалось создать канал")
    
    async def update_channel_chat_id(self, channel_id: int, chat_id: str) -> None:
        """
        Обновление chat_id для канала.
        
        Args:
            channel_id: ID записи канала в БД
            chat_id: Новый chat_id канала
        """
        await self.db.execute(
            "UPDATE channels SET chat_id = ? WHERE id = ?",
            (chat_id, channel_id)
        )
        logger.info(f"Обновлён chat_id для канала {channel_id}: {chat_id}")
    
    async def update_channel_check_subscription(self, channel_id: int, check_subscription: bool) -> None:
        """
        Обновление флага проверки подписки для канала.
        
        Args:
            channel_id: ID записи канала в БД
            check_subscription: Нужно ли проверять подписку
        """
        await self.db.execute(
            "UPDATE channels SET check_subscription = ? WHERE id = ?",
            (1 if check_subscription else 0, channel_id)
        )
        logger.info(f"Обновлён флаг проверки подписки для канала {channel_id}: {check_subscription}")
    
    async def get_channels_for_check(self) -> list[Channel]:
        """
        Получение каналов, для которых нужно проверять подписку.
        
        Returns:
            Список каналов с check_subscription = True
        """
        rows = await self.db.fetchall(
            "SELECT * FROM channels WHERE check_subscription = 1 ORDER BY id"
        )
        
        channels = []
        for row in rows:
            channels.append(Channel(
                id=row["id"],
                chat_id=row["chat_id"],
                username=row["username"],
                title=row["title"],
                type=row["type"],
                check_subscription=True,
                created_at=row["created_at"]
            ))
        
        return channels
    
    async def delete_channel(self, channel_id: int) -> bool:
        """
        Удаление канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            True если удалено успешно
        """
        result = await self.db.execute(
            "DELETE FROM channels WHERE id = ?",
            (channel_id,)
        )
        logger.info(f"Удален канал (id={channel_id})")
        return True
    
    async def delete_channels_not_in_list(
        self,
        new_channel_data: list[tuple]
    ) -> int:
        """
        Удаление каналов, которых нет в предоставленном списке.
        
        Args:
            new_channel_data: Список кортежей (identifier, channel_type, chat_id, username, title)
        
        Returns:
            Количество удаленных каналов
        """
        if not new_channel_data:
            # Если список пуст, удаляем все каналы
            result = await self.db.execute("DELETE FROM channels")
            logger.info("Удалены все каналы (новый список пуст)")
            return result.rowcount if hasattr(result, 'rowcount') else 0
        
        # Формируем множества идентификаторов для сравнения
        usernames_to_keep = set()
        chat_ids_to_keep = set()
        
        for item in new_channel_data:
            # item может быть кортежем (identifier, type) или (identifier, type, chat_id, username, title)
            if len(item) >= 5:
                _, _, chat_id, username, _ = item
                if chat_id:
                    chat_ids_to_keep.add(str(chat_id))
                if username:
                    usernames_to_keep.add(username)
            elif len(item) >= 2:
                identifier, channel_type = item[0], item[1]
                if channel_type == "channel_invite":
                    # Для invite-ссылок сохраняем как username
                    usernames_to_keep.add(identifier)
                elif identifier.startswith("@"):
                    usernames_to_keep.add(identifier[1:])
                else:
                    # Может быть chat_id или username без @
                    usernames_to_keep.add(identifier)
                    # Также может быть числовой chat_id
                    if identifier.isdigit() or identifier.startswith("-"):
                        chat_ids_to_keep.add(identifier)
        
        # Получаем все существующие каналы
        all_channels = await self.get_all_channels()
        deleted_count = 0
        
        for channel in all_channels:
            should_delete = True
            
            # Проверяем по username
            if channel.username and channel.username in usernames_to_keep:
                should_delete = False
            
            # Проверяем по chat_id
            if channel.chat_id and str(channel.chat_id) in chat_ids_to_keep:
                should_delete = False
            
            # Также проверяем, если username совпадает с chat_id в списке
            if channel.username and str(channel.username) in chat_ids_to_keep:
                should_delete = False
            
            if should_delete:
                await self.delete_channel(channel.id)
                deleted_count += 1
        
        logger.info(f"Удалено каналов, отсутствующих в новом сообщении: {deleted_count}")
        return deleted_count


class MailingMessageRepository:
    """Репозиторий для работы с сообщениями для рассылки."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def create_mailing_message(
        self,
        text: Optional[str] = None,
        entities_json: Optional[str] = None,
        media_type: Optional[str] = None,
        media_file_id: Optional[str] = None,
        buttons_json: Optional[str] = None
    ) -> MailingMessage:
        """
        Создание сообщения для рассылки.
        
        Args:
            text: Текст сообщения
            entities_json: JSON строка с entities
            media_type: Тип медиа
            media_file_id: ID файла медиа
            buttons_json: JSON строка с кнопками
        
        Returns:
            Созданный объект MailingMessage
        """
        await self.db.execute(
            """INSERT INTO mailing_messages 
               (text, entities_json, media_type, media_file_id, buttons_json)
               VALUES (?, ?, ?, ?, ?)""",
            (text, entities_json, media_type, media_file_id, buttons_json)
        )
        
        # Получаем созданное сообщение
        row = await self.db.fetchone(
            "SELECT * FROM mailing_messages ORDER BY id DESC LIMIT 1"
        )
        
        if row:
            logger.info(f"Создано сообщение для рассылки (id={row['id']})")
            return MailingMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                media_type=row["media_type"],
                media_file_id=row["media_file_id"],
                buttons_json=row["buttons_json"],
                created_at=row["created_at"]
            )
        raise RuntimeError("Не удалось создать сообщение для рассылки")
    
    async def get_mailing_message(self, message_id: int) -> Optional[MailingMessage]:
        """
        Получение сообщения для рассылки по ID.
        
        Args:
            message_id: ID сообщения
        
        Returns:
            Объект MailingMessage или None
        """
        row = await self.db.fetchone(
            "SELECT * FROM mailing_messages WHERE id = ?",
            (message_id,)
        )
        
        if row:
            return MailingMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                media_type=row["media_type"],
                media_file_id=row["media_file_id"],
                buttons_json=row["buttons_json"],
                created_at=row["created_at"]
            )
        return None
    
    async def get_all_mailing_messages(self) -> list[MailingMessage]:
        """
        Получение всех сообщений для рассылки.
        
        Returns:
            Список сообщений
        """
        rows = await self.db.fetchall(
            "SELECT * FROM mailing_messages ORDER BY id DESC"
        )
        
        messages = []
        for row in rows:
            messages.append(MailingMessage(
                id=row["id"],
                text=row["text"],
                entities_json=row["entities_json"],
                media_type=row["media_type"],
                media_file_id=row["media_file_id"],
                buttons_json=row["buttons_json"],
                created_at=row["created_at"]
            ))
        
        return messages
    
    async def delete_mailing_message(self, message_id: int) -> bool:
        """
        Удаление сообщения для рассылки.
        
        Args:
            message_id: ID сообщения
        
        Returns:
            True если удалено успешно
        """
        await self.db.execute(
            "DELETE FROM mailing_messages WHERE id = ?",
            (message_id,)
        )
        logger.info(f"Удалено сообщение для рассылки (id={message_id})")
        return True


class MailingRepository:
    """Репозиторий для работы с рассылками."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def create_mailing(
        self, 
        message_id: int, 
        scheduled_time: Optional[str] = None
    ) -> Mailing:
        """
        Создание записи о рассылке.
        
        Args:
            message_id: ID сообщения для рассылки
            scheduled_time: Запланированное время рассылки (опционально)
        
        Returns:
            Созданный объект Mailing
        """
        status = "scheduled" if scheduled_time else "pending"
        
        await self.db.execute(
            "INSERT INTO mailings (message_id, scheduled_time, status) VALUES (?, ?, ?)",
            (message_id, scheduled_time, status)
        )
        
        row = await self.db.fetchone(
            "SELECT * FROM mailings ORDER BY id DESC LIMIT 1"
        )
        
        if row:
            return Mailing(
                id=row["id"],
                message_id=row["message_id"],
                sent_count=row["sent_count"],
                failed_count=row["failed_count"],
                scheduled_time=row["scheduled_time"] if "scheduled_time" in row.keys() else None,
                status=row["status"] if "status" in row.keys() else "pending",
                created_at=row["created_at"]
            )
        raise RuntimeError("Не удалось создать рассылку")
    
    async def get_scheduled_mailings(self) -> list[Mailing]:
        """
        Получение всех запланированных рассылок, которые нужно запустить.
        
        Returns:
            Список рассылок для запуска
        """
        from datetime import datetime
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        rows = await self.db.fetchall(
            """SELECT * FROM mailings 
               WHERE status = 'scheduled' 
               AND scheduled_time <= ?
               ORDER BY scheduled_time ASC""",
            (current_time,)
        )
        
        mailings = []
        for row in rows:
            mailings.append(Mailing(
                id=row["id"],
                message_id=row["message_id"],
                sent_count=row["sent_count"],
                failed_count=row["failed_count"],
                scheduled_time=row["scheduled_time"] if "scheduled_time" in row.keys() else None,
                status=row["status"] if "status" in row.keys() else "pending",
                created_at=row["created_at"]
            ))
        
        return mailings
    
    async def update_mailing_status(self, mailing_id: int, status: str) -> None:
        """
        Обновление статуса рассылки.
        
        Args:
            mailing_id: ID рассылки
            status: Новый статус
        """
        await self.db.execute(
            "UPDATE mailings SET status = ? WHERE id = ?",
            (status, mailing_id)
        )
    
    async def update_mailing_stats(
        self,
        mailing_id: int,
        sent_count: int = 0,
        failed_count: int = 0
    ) -> None:
        """
        Обновление статистики рассылки.
        
        Args:
            mailing_id: ID рассылки
            sent_count: Количество отправленных
            failed_count: Количество неудачных
        """
        await self.db.execute(
            """UPDATE mailings 
               SET sent_count = sent_count + ?, failed_count = failed_count + ?
               WHERE id = ?""",
            (sent_count, failed_count, mailing_id)
        )
    
    async def get_mailing(self, mailing_id: int) -> Optional[Mailing]:
        """
        Получение рассылки по ID.
        
        Args:
            mailing_id: ID рассылки
        
        Returns:
            Объект Mailing или None
        """
        row = await self.db.fetchone(
            "SELECT * FROM mailings WHERE id = ?",
            (mailing_id,)
        )
        
        if row:
            return Mailing(
                id=row["id"],
                message_id=row["message_id"],
                sent_count=row["sent_count"],
                failed_count=row["failed_count"],
                scheduled_time=row["scheduled_time"] if "scheduled_time" in row.keys() else None,
                status=row["status"] if "status" in row.keys() else "pending",
                created_at=row["created_at"]
            )
        return None
    
    async def get_all_mailings(self) -> list[Mailing]:
        """
        Получение всех рассылок.
        
        Returns:
            Список рассылок
        """
        rows = await self.db.fetchall(
            "SELECT * FROM mailings ORDER BY id DESC LIMIT 50"
        )
        
        mailings = []
        for row in rows:
            mailings.append(Mailing(
                id=row["id"],
                message_id=row["message_id"],
                sent_count=row["sent_count"],
                failed_count=row["failed_count"],
                scheduled_time=row["scheduled_time"] if "scheduled_time" in row.keys() else None,
                status=row["status"] if "status" in row.keys() else "pending",
                created_at=row["created_at"]
            ))
        
        return mailings


class MailingLogRepository:
    """Репозиторий для работы с логами рассылок."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def create_log(
        self,
        mailing_id: int,
        user_id: int,
        status: str,
        error_text: Optional[str] = None
    ) -> None:
        """
        Создание лога рассылки.
        
        Args:
            mailing_id: ID рассылки
            user_id: ID пользователя
            status: Статус ('sent' или 'failed')
            error_text: Текст ошибки (если есть)
        """
        await self.db.execute(
            """INSERT INTO mailing_logs (mailing_id, user_id, status, error_text)
               VALUES (?, ?, ?, ?)""",
            (mailing_id, user_id, status, error_text)
        )


class SettingsRepository:
    """Репозиторий для работы с настройками бота."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def get_settings(self) -> BotSettings:
        """
        Получение текущих настроек бота.
        
        Returns:
            Объект BotSettings
        """
        row = await self.db.fetchone(
            "SELECT * FROM bot_settings ORDER BY id DESC LIMIT 1"
        )
        
        if row:
            try:
                completed_percent = row["completed_percent"]
            except (KeyError, IndexError):
                completed_percent = None
            if completed_percent is not None:
                try:
                    completed_percent = float(completed_percent)
                    if completed_percent < 0:
                        completed_percent = None
                except (TypeError, ValueError):
                    completed_percent = None
            try:
                welcome_mode = (row["welcome_mode"] or "subscription_first").strip()
            except (KeyError, IndexError, TypeError):
                welcome_mode = "subscription_first"
            if welcome_mode not in ("subscription_first", "questionnaire_first", "no_questionnaire"):
                welcome_mode = "subscription_first"
            try:
                stats_criterion = (row["stats_activated_criterion"] or "bot_entry").strip()
            except (KeyError, IndexError, TypeError):
                stats_criterion = "bot_entry"
            if stats_criterion not in (
                "bot_entry",
                "questionnaire_started",
                "questionnaire_completed",
                "subscription_check_clicked",
            ):
                stats_criterion = "bot_entry"
            return BotSettings(
                id=row["id"],
                adjustment_percent=row["adjustment_percent"] or 0.0,
                completed_percent=completed_percent,
                welcome_mode=welcome_mode,
                stats_activated_criterion=stats_criterion,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return BotSettings(adjustment_percent=0.0)
    
    async def update_adjustment_percent(self, percent: float) -> BotSettings:
        """
        Обновление процента корректировки статистики.
        
        Args:
            percent: Процент корректировки (-100 до +100)
        
        Returns:
            Обновленный объект BotSettings
        """
        # Проверка диапазона
        if percent < -100 or percent > 100:
            raise ValueError("Процент должен быть в диапазоне от -100 до +100")
        
        # Проверяем, есть ли уже настройки
        existing = await self.db.fetchone("SELECT id FROM bot_settings LIMIT 1")
        
        if existing:
            await self.db.execute(
                """UPDATE bot_settings 
                   SET adjustment_percent = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (percent, existing["id"])
            )
            logger.info(f"Обновлен процент корректировки: {percent}%")
        else:
            await self.db.execute(
                """INSERT INTO bot_settings (adjustment_percent) 
                   VALUES (?)""",
                (percent,)
            )
            logger.info(f"Создан процент корректировки: {percent}%")
        
        return await self.get_settings()

    async def get_welcome_mode(self) -> str:
        """Режим приветствия: subscription_first | questionnaire_first."""
        s = await self.get_settings()
        return s.welcome_mode

    async def set_welcome_mode(self, mode: str) -> "BotSettings":
        """Установить режим приветствия."""
        if mode not in ("subscription_first", "questionnaire_first", "no_questionnaire"):
            raise ValueError("welcome_mode должен быть subscription_first, questionnaire_first или no_questionnaire")
        existing = await self.db.fetchone("SELECT id FROM bot_settings LIMIT 1")
        try:
            await self.db.execute(
                "UPDATE bot_settings SET welcome_mode = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (mode, existing["id"]),
            )
        except Exception:
            await self.db.execute(
                "INSERT INTO bot_settings (adjustment_percent, welcome_mode) VALUES (0.0, ?)",
                (mode,),
            )
        logger.info(f"Установлен режим приветствия: {mode}")
        return await self.get_settings()

    async def set_stats_activated_criterion(self, criterion: str) -> "BotSettings":
        """Установить критерий «Активировали бота» в блоке Статистика."""
        if criterion not in (
            "bot_entry",
            "questionnaire_started",
            "questionnaire_completed",
            "subscription_check_clicked",
        ):
            raise ValueError(
                "criterion должен быть bot_entry, questionnaire_started, "
                "questionnaire_completed или subscription_check_clicked"
            )
        existing = await self.db.fetchone("SELECT id FROM bot_settings LIMIT 1")
        try:
            await self.db.execute(
                "UPDATE bot_settings SET stats_activated_criterion = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (criterion, existing["id"]),
            )
        except Exception:
            await self.db.execute(
                "INSERT INTO bot_settings (adjustment_percent, stats_activated_criterion) VALUES (0.0, ?)",
                (criterion,),
            )
        logger.info(f"Установлен критерий «Активировали бота» в статистике: {criterion}")
        return await self.get_settings()
    
    async def update_completed_percent(self, percent: Optional[float]) -> "BotSettings":
        """
        Установка «Заполнили анкету» как % от «Активировали бота».
        None = показывать по факту из логов; 0–100 = заданный процент от активировавших.

        Args:
            percent: None = по факту, 0–100 = процент от активировавших

        Returns:
            Обновленный объект BotSettings
        """
        if percent is not None and (percent < 0 or percent > 100):
            raise ValueError("Процент должен быть в диапазоне от 0 до 100 или None")
        existing = await self.db.fetchone("SELECT id FROM bot_settings LIMIT 1")
        if existing:
            await self.db.execute(
                """UPDATE bot_settings
                   SET completed_percent = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (percent, existing["id"])
            )
            logger.info(f"Установлен процент «Заполнили анкету» от «Активировали»: {percent}")
        else:
            await self.db.execute(
                """INSERT INTO bot_settings (adjustment_percent, completed_percent)
                   VALUES (0.0, ?)""",
                (percent,)
            )
            logger.info(f"Созданы настройки, процент «Заполнили»: {percent}")
        return await self.get_settings()
