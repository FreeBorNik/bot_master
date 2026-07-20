"""Репозиторий для работы с логами действий пользователей."""
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from bot.database.db import Database
from bot.database.models import UserActionLog
from bot.database.repositories import WelcomeMessageRepository
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserActionLogRepository:
    """Репозиторий для работы с логами действий пользователей."""
    
    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: Экземпляр базы данных
        """
        self.db = db
    
    async def create_log(
        self,
        user_id: int,
        action_type: str,
        message_text: Optional[str] = None,
        callback_data: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None,
        welcome_message_id: Optional[int] = None
    ) -> None:
        """
        Создание лога действия пользователя.
        
        Args:
            user_id: ID пользователя
            action_type: Тип действия (command, message, callback и т.д.)
            message_text: Текст сообщения (если есть)
            callback_data: Данные callback (если есть)
            action_data: Дополнительные данные в виде словаря
            welcome_message_id: ID активного приветственного сообщения на момент действия (если None, будет получен автоматически)
        """
        try:
            # Если welcome_message_id не указан, получаем ID активного приветственного сообщения
            if welcome_message_id is None:
                welcome_repo = WelcomeMessageRepository(self.db)
                welcome_message_id = await welcome_repo.get_active_welcome_message_id()
            
            action_data_json = json.dumps(action_data, ensure_ascii=False) if action_data else None
            
            await self.db.execute(
                """INSERT INTO user_actions_logs 
                   (user_id, action_type, action_data, message_text, callback_data, welcome_message_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, action_type, action_data_json, message_text, callback_data, welcome_message_id)
            )
        except Exception as e:
            logger.error(f"Ошибка при создании лога действия пользователя {user_id}: {e}")
    
    async def get_user_logs(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserActionLog]:
        """
        Получение логов действий конкретного пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Лимит записей
            offset: Смещение
        
        Returns:
            Список логов действий
        """
        rows = await self.db.fetchall(
            """SELECT * FROM user_actions_logs 
               WHERE user_id = ? 
               ORDER BY created_at DESC 
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset)
        )
        
        logs = []
        for row in rows:
            welcome_message_id = None
            if "welcome_message_id" in row.keys():
                welcome_message_id = row["welcome_message_id"]
            
            logs.append(UserActionLog(
                id=row["id"],
                user_id=row["user_id"],
                action_type=row["action_type"],
                action_data=row["action_data"],
                message_text=row["message_text"],
                callback_data=row["callback_data"],
                welcome_message_id=welcome_message_id,
                created_at=row["created_at"]
            ))
        
        return logs
    
    async def get_all_logs(
        self,
        limit: int = 1000,
        offset: int = 0,
        action_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[UserActionLog]:
        """
        Получение всех логов действий с фильтрацией.
        
        Args:
            limit: Лимит записей
            offset: Смещение
            action_type: Фильтр по типу действия
            date_from: Дата начала периода (YYYY-MM-DD)
            date_to: Дата конца периода (YYYY-MM-DD)
        
        Returns:
            Список логов действий
        """
        query = "SELECT * FROM user_actions_logs WHERE 1=1"
        params = []
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = await self.db.fetchall(query, tuple(params))
        
        logs = []
        for row in rows:
            welcome_message_id = None
            if "welcome_message_id" in row.keys():
                welcome_message_id = row["welcome_message_id"]
            
            logs.append(UserActionLog(
                id=row["id"],
                user_id=row["user_id"],
                action_type=row["action_type"],
                action_data=row["action_data"],
                message_text=row["message_text"],
                callback_data=row["callback_data"],
                welcome_message_id=welcome_message_id,
                created_at=row["created_at"]
            ))
        
        return logs
    
    async def get_user_activity_stats(
        self,
        user_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получение статистики активности пользователей.
        
        Args:
            user_id: ID пользователя (опционально, для конкретного пользователя)
            date_from: Дата начала периода
            date_to: Дата конца периода
        
        Returns:
            Словарь со статистикой
        """
        query = "SELECT action_type, COUNT(*) as count FROM user_actions_logs WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        query += " GROUP BY action_type"
        
        rows = await self.db.fetchall(query, tuple(params))
        
        stats = {}
        total = 0
        for row in rows:
            stats[row["action_type"]] = row["count"]
            total += row["count"]
        
        stats["total"] = total
        
        return stats
    
    async def get_users_activity_summary(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Получение сводки активности пользователей.
        
        Args:
            limit: Количество пользователей
        
        Returns:
            Список словарей с информацией о пользователях и их активности
        """
        rows = await self.db.fetchall(
            """SELECT 
                   u.user_id,
                   u.username,
                   u.full_name,
                   COUNT(l.id) as actions_count,
                   MAX(l.created_at) as last_action
               FROM users u
               LEFT JOIN user_actions_logs l ON u.user_id = l.user_id
               GROUP BY u.user_id, u.username, u.full_name
               ORDER BY actions_count DESC, last_action DESC
               LIMIT ?""",
            (limit,)
        )
        
        summary = []
        for row in rows:
            summary.append({
                "user_id": row["user_id"],
                "username": row["username"],
                "full_name": row["full_name"],
                "actions_count": row["actions_count"] or 0,
                "last_action": row["last_action"]
            })
        
        return summary
    
    async def get_unique_actions_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получение статистики уникальных действий за период.
        
        Args:
            date_from: Дата начала периода (YYYY-MM-DD)
            date_to: Дата конца периода (YYYY-MM-DD)
        
        Returns:
            Словарь с типами действий и количеством уникальных пользователей
        """
        query = """
            SELECT 
                action_type,
                COUNT(DISTINCT user_id) as unique_users_count,
                COUNT(*) as total_actions_count
            FROM user_actions_logs
            WHERE 1=1
        """
        params = []
        
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        query += " GROUP BY action_type ORDER BY unique_users_count DESC"
        
        rows = await self.db.fetchall(query, tuple(params))
        
        stats = {}
        for row in rows:
            action_type = row["action_type"]
            stats[action_type] = {
                "unique_users": row["unique_users_count"],
                "total_actions": row["total_actions_count"]
            }
        
        return stats

    async def get_questionnaire_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        activated_action_type: str = "bot_entry",
    ) -> Dict[str, int]:
        """
        Статистика по анкете: «активировали» по тому же критерию, что блок «Статистика»
        (настройка stats_activated_criterion), и заполнения (questionnaire_completed).
        Исключает администраторов.

        Args:
            date_from: Дата начала периода (YYYY-MM-DD), опционально.
            date_to: Дата конца периода (YYYY-MM-DD), опционально.
            activated_action_type: user_actions_logs.action_type для метрики активаций.

        Returns:
            Словарь: activated_count, completed_count
        """
        if activated_action_type not in (
            "bot_entry",
            "questionnaire_started",
            "questionnaire_completed",
            "subscription_check_clicked",
        ):
            activated_action_type = "bot_entry"

        admin_rows = await self.db.fetchall("SELECT user_id FROM admins", ())
        admin_ids = [row["user_id"] for row in admin_rows]
        exclude = ""
        params: List[Any] = []
        if admin_ids:
            placeholders = ",".join(["?" for _ in admin_ids])
            exclude = f" AND user_id NOT IN ({placeholders})"
            params = list(admin_ids)

        date_filter = ""
        if date_from:
            date_filter += " AND DATE(created_at) >= ?"
            params.append(date_from)
        if date_to:
            date_filter += " AND DATE(created_at) <= ?"
            params.append(date_to)

        activated_row = await self.db.fetchone(
            f"""SELECT COUNT(DISTINCT user_id) as cnt FROM user_actions_logs
                WHERE action_type = ? {exclude} {date_filter}""",
            (activated_action_type,) + tuple(params),
        )
        # Параметры для второго запроса (без date_*, т.к. params уже дополнены)
        params_completed = list(params)
        completed_row = await self.db.fetchone(
            f"""SELECT COUNT(DISTINCT user_id) as cnt FROM user_actions_logs
                WHERE action_type = 'questionnaire_completed' {exclude} {date_filter}""",
            tuple(params_completed),
        )
        return {
            "activated_count": activated_row["cnt"] if activated_row else 0,
            "completed_count": completed_row["cnt"] if completed_row else 0,
        }
    
    async def get_action_descriptions(
        self,
        action_types: List[str],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Получение описаний действий из логов.
        
        Args:
            action_types: Список типов действий
            date_from: Дата начала периода
            date_to: Дата конца периода
        
        Returns:
            Словарь {action_type: description}
        """
        if not action_types:
            return {}
        
        placeholders = ",".join(["?" for _ in action_types])
        query = f"""
            SELECT DISTINCT action_type, message_text
            FROM user_actions_logs
            WHERE action_type IN ({placeholders})
        """
        params = list(action_types)
        
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        query += " AND message_text IS NOT NULL ORDER BY action_type, created_at DESC"
        
        rows = await self.db.fetchall(query, tuple(params))
        
        descriptions = {}
        for row in rows:
            action_type = row["action_type"]
            if action_type not in descriptions:
                descriptions[action_type] = row["message_text"]
        
        return descriptions
    
    async def get_simplified_actions_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получение упрощённой статистики по конкретным типам действий.
        Исключает действия администраторов.
        
        Args:
            date_from: Дата начала периода (YYYY-MM-DD)
            date_to: Дата конца периода (YYYY-MM-DD)
        
        Returns:
            Словарь с типами действий и статистикой
        """
        # Получаем список администраторов для исключения
        admin_rows = await self.db.fetchall("SELECT user_id FROM admins", ())
        admin_ids = [row["user_id"] for row in admin_rows]
        
        # Формируем условие для исключения администраторов
        exclude_admins = ""
        if admin_ids:
            placeholders = ",".join(["?" for _ in admin_ids])
            exclude_admins = f" AND user_id NOT IN ({placeholders})"
        
        stats = {}
        
        # 1. Зашёл в бот
        query = f"""
            SELECT 
                COUNT(DISTINCT user_id) as unique_users_count,
                COUNT(*) as total_actions_count
            FROM user_actions_logs
            WHERE action_type = 'bot_entry'
            {exclude_admins}
        """
        params = list(admin_ids) if admin_ids else []
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        row = await self.db.fetchone(query, tuple(params))
        if row and row["total_actions_count"] > 0:
            stats["bot_entry"] = {
                "name": "Зашёл в бот",
                "unique_users": row["unique_users_count"],
                "total_actions": row["total_actions_count"]
            }
        
        # 2. Активировали бота (увидели анкету)
        query = f"""
            SELECT 
                COUNT(DISTINCT user_id) as unique_users_count,
                COUNT(*) as total_actions_count
            FROM user_actions_logs
            WHERE action_type = 'questionnaire_started'
            {exclude_admins}
        """
        params = list(admin_ids) if admin_ids else []
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        row = await self.db.fetchone(query, tuple(params))
        if row and row["total_actions_count"] > 0:
            stats["questionnaire_started"] = {
                "name": "Активировали бота",
                "unique_users": row["unique_users_count"],
                "total_actions": row["total_actions_count"]
            }
        
        # 3. Заблокировал бот
        query = f"""
            SELECT 
                COUNT(DISTINCT user_id) as unique_users_count,
                COUNT(*) as total_actions_count
            FROM user_actions_logs
            WHERE action_type = 'bot_blocked'
            {exclude_admins}
        """
        params = list(admin_ids) if admin_ids else []
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        row = await self.db.fetchone(query, tuple(params))
        if row and row["total_actions_count"] > 0:
            stats["bot_blocked"] = {
                "name": "Заблокировал бот",
                "unique_users": row["unique_users_count"],
                "total_actions": row["total_actions_count"]
            }
        
        # 4. Заполнил анкету
        query = f"""
            SELECT 
                COUNT(DISTINCT user_id) as unique_users_count,
                COUNT(*) as total_actions_count
            FROM user_actions_logs
            WHERE action_type = 'questionnaire_completed'
            {exclude_admins}
        """
        params = list(admin_ids) if admin_ids else []
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        row = await self.db.fetchone(query, tuple(params))
        if row and row["total_actions_count"] > 0:
            stats["questionnaire_completed"] = {
                "name": "Заполнил анкету",
                "unique_users": row["unique_users_count"],
                "total_actions": row["total_actions_count"]
            }
        
        # 5. Написал текст
        query = f"""
            SELECT 
                COUNT(DISTINCT user_id) as unique_users_count,
                COUNT(*) as total_actions_count
            FROM user_actions_logs
            WHERE action_type = 'text_message'
            {exclude_admins}
        """
        params = list(admin_ids) if admin_ids else []
        if date_from:
            query += " AND DATE(created_at) >= ?"
            params.append(date_from)
        if date_to:
            query += " AND DATE(created_at) <= ?"
            params.append(date_to)
        
        row = await self.db.fetchone(query, tuple(params))
        if row and row["total_actions_count"] > 0:
            stats["text_message"] = {
                "name": "Написал текст",
                "unique_users": row["unique_users_count"],
                "total_actions": row["total_actions_count"]
            }
        
        # 6. Нажал кнопку (группируем по callback_data и message_text)
        # Исключаем админские кнопки (начинающиеся с "admin_")
        button_query = f"""
            SELECT 
                CASE 
                    WHEN callback_data IS NOT NULL THEN callback_data
                    ELSE message_text
                END as button_identifier,
                COUNT(DISTINCT user_id) as unique_users_count,
                COUNT(*) as total_actions_count
            FROM user_actions_logs
            WHERE action_type IN ('button_click', 'callback', 'subscription_check_button')
            AND (callback_data IS NOT NULL OR message_text IS NOT NULL)
            AND (callback_data IS NULL OR callback_data NOT LIKE 'admin_%')
            AND action_type != 'admin_action'
            {exclude_admins}
        """
        button_params = list(admin_ids) if admin_ids else []
        if date_from:
            button_query += " AND DATE(created_at) >= ?"
            button_params.append(date_from)
        if date_to:
            button_query += " AND DATE(created_at) <= ?"
            button_params.append(date_to)
        
        button_query += " GROUP BY button_identifier ORDER BY total_actions_count DESC"
        
        button_rows = await self.db.fetchall(button_query, tuple(button_params))
        
        for row in button_rows:
            button_identifier = row["button_identifier"]
            if not button_identifier:
                continue
            
            # Пропускаем админские кнопки
            if button_identifier.startswith("admin_"):
                continue
            
            # Формируем читаемое название кнопки
            if button_identifier == "check_subscription":
                button_name = "Нажал кнопку 'Проверить подписку'"
            else:
                # Пытаемся сделать читаемое название из callback_data
                button_name = button_identifier.replace("_", " ").replace("-", " ")
                # Делаем первую букву заглавной
                button_name = button_name.title()
                button_name = f"Нажал кнопку '{button_name}'"
            
            stats[f"button_{button_identifier}"] = {
                "name": button_name,
                "unique_users": row["unique_users_count"],
                "total_actions": row["total_actions_count"]
            }
        
        return stats
