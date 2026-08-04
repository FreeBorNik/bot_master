"""Миграции базы данных."""
from bot.config import RunnerConfig
from bot.database.db import Database
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


async def create_tables(db: Database) -> None:
    """
    Создание всех таблиц в базе данных.
    
    Args:
        db: Экземпляр базы данных
    """
    # Подключение уже должно быть установлено в main.py
    
    # Таблица пользователей
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            age INTEGER,
            hours_per_day INTEGER,
            has_other_job INTEGER,
            is_subscribed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        await db.execute("ALTER TABLE users ADD COLUMN is_in_bot INTEGER DEFAULT 1")
    except Exception:
        pass  # колонка уже есть

    # Таблица администраторов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица сообщений после команды /start (отправляется самым первым, если включено)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS start_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            entities_json TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица приветственных сообщений
    await db.execute("""
        CREATE TABLE IF NOT EXISTS welcome_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            entities_json TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Добавляем поле is_active, если таблица уже существует без него
    try:
        await db.execute("ALTER TABLE welcome_messages ADD COLUMN is_active INTEGER DEFAULT 1")
    except Exception:
        pass  # Поле уже существует
    
    # Таблица сообщений после анкеты (отправляется после заполнения анкеты)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS post_questionnaire_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            entities_json TEXT,
            media_type TEXT,
            media_file_id TEXT,
            buttons_json TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        await db.execute("ALTER TABLE post_questionnaire_messages ADD COLUMN is_active INTEGER DEFAULT 1")
    except Exception:
        pass  # Поле уже существует

    # Таблица цепочки сообщений (отправляются после "Сообщения после подписки")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS chain_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_number INTEGER NOT NULL UNIQUE,
            text TEXT NOT NULL,
            entities_json TEXT,
            media_type TEXT,
            media_file_id TEXT,
            buttons_json TEXT,
            delay_minutes INTEGER NOT NULL DEFAULT 10,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Инициализация цепочки сообщений по умолчанию (если их еще нет)
    existing_chain = await db.fetchone("SELECT COUNT(*) as count FROM chain_messages")
    if existing_chain and existing_chain["count"] == 0:
        # Создаем 3 сообщения по умолчанию
        default_messages = [
            (1, "Сообщение 1", 10),
            (2, "Сообщение 2", 20),
            (3, "Сообщение 3", 30)
        ]
        for msg_num, text, delay in default_messages:
            await db.execute(
                """INSERT INTO chain_messages (message_number, text, delay_minutes, is_active)
                   VALUES (?, ?, ?, 1)""",
                (msg_num, text, delay)
            )
        logger.info("Создана цепочка сообщений по умолчанию")

    # Настройки цепочки (одна запись: цепочка активна/неактивна; по умолчанию неактивна до настройки админом)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS chain_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            is_active INTEGER DEFAULT 0
        )
    """)
    existing_settings = await db.fetchone("SELECT COUNT(*) as count FROM chain_settings")
    if existing_settings and existing_settings["count"] == 0:
        await db.execute("INSERT INTO chain_settings (id, is_active) VALUES (1, 0)")
        logger.info("Созданы настройки цепочки по умолчанию (цепочка неактивна)")

    try:
        await db.execute("ALTER TABLE chain_settings ADD COLUMN flow_order TEXT DEFAULT '[1,2,3,4]'")
        await db.execute("UPDATE chain_settings SET flow_order = '[1,2,3,4]' WHERE id = 1 AND flow_order IS NULL")
    except Exception:
        pass  # колонка уже есть

    # Таблица каналов для проверки подписки
    await db.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            username TEXT,
            title TEXT,
            type TEXT NOT NULL,
            check_subscription INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, username)
        )
    """)
    
    # Добавляем поле check_subscription, если таблица уже существует без него
    try:
        await db.execute("ALTER TABLE channels ADD COLUMN check_subscription INTEGER DEFAULT 1")
    except Exception:
        pass  # Поле уже существует
    
    # Таблица сообщений для рассылки
    await db.execute("""
        CREATE TABLE IF NOT EXISTS mailing_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            entities_json TEXT,
            media_type TEXT,
            media_file_id TEXT,
            buttons_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица рассылок
    await db.execute("""
        CREATE TABLE IF NOT EXISTS mailings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            scheduled_time TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES mailing_messages(id)
        )
    """)
    
    # Добавляем поля для планирования, если таблица уже существует
    try:
        await db.execute("ALTER TABLE mailings ADD COLUMN scheduled_time TEXT")
    except Exception:
        pass  # Поле уже существует
    
    try:
        await db.execute("ALTER TABLE mailings ADD COLUMN status TEXT DEFAULT 'pending'")
    except Exception:
        pass  # Поле уже существует
    
    # Таблица логов рассылок
    await db.execute("""
        CREATE TABLE IF NOT EXISTS mailing_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mailing_id INTEGER,
            user_id INTEGER,
            status TEXT NOT NULL,
            error_text TEXT,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mailing_id) REFERENCES mailings(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица статистики
    await db.execute("""
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            total_users INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            messages_sent INTEGER DEFAULT 0
        )
    """)
    
    # Таблица логов действий пользователей
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_actions_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            action_data TEXT,
            message_text TEXT,
            callback_data TEXT,
            welcome_message_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (welcome_message_id) REFERENCES welcome_messages(id)
        )
    """)
    
    # Добавляем поле welcome_message_id, если таблица уже существует без него
    try:
        await db.execute("ALTER TABLE user_actions_logs ADD COLUMN welcome_message_id INTEGER")
    except Exception:
        pass  # Поле уже существует
    
    # Таблица настроек бота
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            adjustment_percent REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Инициализация настроек по умолчанию (если их еще нет)
    existing_settings = await db.fetchone("SELECT COUNT(*) as count FROM bot_settings")
    if existing_settings and existing_settings["count"] == 0:
        await db.execute(
            "INSERT INTO bot_settings (adjustment_percent) VALUES (?)",
            (0.0,)
        )
    
    # Поле «Заполнили анкету» как % от «Активировали» (NULL = по факту, 0–100 = заданный %)
    try:
        await db.execute("ALTER TABLE bot_settings ADD COLUMN completed_percent REAL")
    except Exception:
        pass  # Поле уже существует

    # Режим приветствия: subscription_first | questionnaire_first | no_questionnaire
    try:
        await db.execute("ALTER TABLE bot_settings ADD COLUMN welcome_mode TEXT DEFAULT 'subscription_first'")
    except Exception:
        pass

    # Критерий «Активировали бота» в блоке Статистика: bot_entry | questionnaire_started | questionnaire_completed
    try:
        await db.execute("ALTER TABLE bot_settings ADD COLUMN stats_activated_criterion TEXT DEFAULT 'bot_entry'")
    except Exception:
        pass

    # Приветствие в режиме «анкета первой» (текст + кнопка «Заполнить анкету»)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS simple_welcome_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            entities_json TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Сообщение со списком каналов (после анкеты в режиме questionnaire_first), плейсхолдер {channels_list}
    await db.execute("""
        CREATE TABLE IF NOT EXISTS channels_list_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            entities_json TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Приветствие в режиме «без анкеты» (текст + кнопка «Проверить подписку»)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS no_questionnaire_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            entities_json TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Создаем индексы для быстрого поиска
    try:
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_actions_user_id ON user_actions_logs(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_actions_created_at ON user_actions_logs(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_actions_type ON user_actions_logs(action_type)")
    except Exception:
        pass  # Индексы уже существуют
    
    logger.info("Таблицы базы данных созданы успешно")

    await init_admins(db)


async def init_admins(db: Database) -> None:
    """Добавить админов из env в таблицу admins (INSERT IF NOT EXISTS)."""
    admin_ids = RunnerConfig.child_admin_ids()
    if not admin_ids:
        logger.warning(
            "Список админов пуст (ADMIN_IDS/CONTROL_ADMIN_IDS) — пропуск для %s",
            db.db_path,
        )
        return

    added = 0
    for admin_id in admin_ids:
        try:
            existing = await db.fetchone(
                "SELECT user_id FROM admins WHERE user_id = ?",
                (admin_id,),
            )
            if not existing:
                await db.execute(
                    "INSERT INTO admins (user_id) VALUES (?)",
                    (admin_id,),
                )
                added += 1
                logger.info("Администратор %s добавлен в БД %s", admin_id, db.db_path)
        except Exception as exc:
            logger.error(
                "Ошибка при добавлении администратора %s в %s: %s",
                admin_id,
                db.db_path,
                exc,
            )

    if added == 0:
        logger.debug(
            "Админы уже синхронизированы (%d id) в %s",
            len(admin_ids),
            db.db_path,
        )
