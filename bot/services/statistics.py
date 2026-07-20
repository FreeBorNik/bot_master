"""Сервис статистики."""
from typing import Dict, Any, List

from bot.database.db import Database
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


async def get_statistics(
    db: Database,
    date_from: str | None = None,
    date_to: str | None = None,
) -> Dict:
    """
    Получение статистики бота за период.
    
    Args:
        db: Экземпляр базы данных
        date_from: Дата начала периода (YYYY-MM-DD), опционально
        date_to: Дата конца периода (YYYY-MM-DD), опционально
    
    Returns:
        Словарь со статистикой
    """
    try:
        # Отправлено сообщений (рассылки) — фильтруем по sent_at в mailing_logs
        date_filter_messages = ""
        params_messages: List[Any] = []
        if date_from:
            date_filter_messages += " AND DATE(sent_at) >= ?"
            params_messages.append(date_from)
        if date_to:
            date_filter_messages += " AND DATE(sent_at) <= ?"
            params_messages.append(date_to)

        messages_sent_query = f"""
            SELECT COUNT(*) as count
            FROM mailing_logs
            WHERE status = 'sent' {date_filter_messages}
        """
        messages_sent_result = await db.fetchone(messages_sent_query, tuple(params_messages))
        messages_sent = messages_sent_result["count"] if messages_sent_result else 0

        # Если период НЕ задан — показываем общие значения из таблицы users
        if not date_from and not date_to:
            total_users_result = await db.fetchone("SELECT COUNT(*) as count FROM users")
            total_users = total_users_result["count"] if total_users_result else 0

            active_users_result = await db.fetchone(
                "SELECT COUNT(*) as count FROM users WHERE is_in_bot = 1"
            )
            active_users = active_users_result["count"] if active_users_result else 0

            blocked_users_result = await db.fetchone(
                "SELECT COUNT(*) as count FROM users WHERE is_in_bot = 0"
            )
            blocked_users = blocked_users_result["count"] if blocked_users_result else 0
        else:
            # Если период задан — считаем пользователей по активности в логах действий за период.
            # Это корректнее, чем фильтровать users.created_at (иначе будут нули, если нет новых пользователей).
            admin_rows = await db.fetchall("SELECT user_id FROM admins", ())
            admin_ids = [row["user_id"] for row in admin_rows]

            exclude_admins = ""
            params_actions: List[Any] = []
            if admin_ids:
                placeholders = ",".join(["?" for _ in admin_ids])
                exclude_admins = f" AND user_id NOT IN ({placeholders})"
                params_actions.extend(admin_ids)

            date_filter_actions = ""
            if date_from:
                date_filter_actions += " AND DATE(created_at) >= ?"
                params_actions.append(date_from)
            if date_to:
                date_filter_actions += " AND DATE(created_at) <= ?"
                params_actions.append(date_to)

            sub_where = f"1=1 {exclude_admins}{date_filter_actions}"
            subquery = f"SELECT DISTINCT user_id FROM user_actions_logs WHERE {sub_where}"

            total_users_row = await db.fetchone(
                f"SELECT COUNT(DISTINCT user_id) as count FROM user_actions_logs WHERE {sub_where}",
                tuple(params_actions),
            )
            total_users = total_users_row["count"] if total_users_row else 0

            active_users_row = await db.fetchone(
                f"SELECT COUNT(*) as count FROM users WHERE is_in_bot = 1 AND user_id IN ({subquery})",
                tuple(params_actions),
            )
            active_users = active_users_row["count"] if active_users_row else 0

            blocked_users_row = await db.fetchone(
                f"SELECT COUNT(*) as count FROM users WHERE is_in_bot = 0 AND user_id IN ({subquery})",
                tuple(params_actions),
            )
            blocked_users = blocked_users_row["count"] if blocked_users_row else 0

        # Для периода: считаем "Активировали бот" и "Заблокировали бот" за период
        activated_in_period = 0
        blocked_in_period = 0
        if date_from or date_to:
            admin_rows = await db.fetchall("SELECT user_id FROM admins", ())
            admin_ids = [row["user_id"] for row in admin_rows]

            exclude_admins = ""
            params_period: List[Any] = []
            if admin_ids:
                placeholders = ",".join(["?" for _ in admin_ids])
                exclude_admins = f" AND user_id NOT IN ({placeholders})"
                params_period.extend(admin_ids)

            date_filter_period = ""
            if date_from:
                date_filter_period += " AND DATE(created_at) >= ?"
                params_period.append(date_from)
            if date_to:
                date_filter_period += " AND DATE(created_at) <= ?"
                params_period.append(date_to)

            # Критерий «Активировали бота» из настроек:
            # bot_entry | questionnaire_started | questionnaire_completed | subscription_check_clicked
            from bot.database.repositories import SettingsRepository
            settings = await SettingsRepository(db).get_settings()
            action_type_activated = getattr(
                settings, "stats_activated_criterion", "bot_entry"
            )
            if action_type_activated not in (
                "bot_entry",
                "questionnaire_started",
                "questionnaire_completed",
                "subscription_check_clicked",
            ):
                action_type_activated = "bot_entry"
            activated_row = await db.fetchone(
                f"""SELECT COUNT(DISTINCT user_id) as count FROM user_actions_logs
                    WHERE action_type = ? {exclude_admins} {date_filter_period}""",
                (action_type_activated,) + tuple(params_period),
            )
            activated_in_period = activated_row["count"] if activated_row else 0

            # Заблокировали бот = action_type = 'bot_blocked'
            blocked_row = await db.fetchone(
                f"""SELECT COUNT(DISTINCT user_id) as count FROM user_actions_logs
                    WHERE action_type = 'bot_blocked' {exclude_admins} {date_filter_period}""",
                tuple(params_period),
            )
            blocked_in_period = blocked_row["count"] if blocked_row else 0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "messages_sent": messages_sent,
            "activated_in_period": activated_in_period,
            "blocked_in_period": blocked_in_period,
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return {
            "total_users": 0,
            "active_users": 0,
            "blocked_users": 0,
            "messages_sent": 0,
            "activated_in_period": 0,
            "blocked_in_period": 0,
        }
