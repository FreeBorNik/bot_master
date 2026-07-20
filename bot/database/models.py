"""Модели данных для базы данных."""
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class User:
    """Модель пользователя."""
    user_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None
    age: Optional[int] = None
    hours_per_day: Optional[int] = None
    has_other_job: Optional[bool] = None
    is_subscribed: bool = False
    is_in_bot: bool = True  # False — пользователь заблокировал бота; при повторном /start считаем как первый вход
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)


@dataclass
class Admin:
    """Модель администратора."""
    user_id: int
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)


@dataclass
class StartMessage:
    """Модель сообщения после команды /start (отправляется самым первым, если включено)."""
    id: Optional[int] = None
    text: Optional[str] = None
    entities_json: Optional[str] = None
    is_active: bool = True  # Статус активности сообщения
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)
    
    def get_entities(self) -> Optional[list]:
        """Получение entities из JSON."""
        if self.entities_json:
            return json.loads(self.entities_json)
        return None


@dataclass
class WelcomeMessage:
    """Модель приветственного сообщения."""
    id: Optional[int] = None
    text: Optional[str] = None
    entities_json: Optional[str] = None
    is_active: bool = True  # Статус активности сообщения
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)
    
    def get_entities(self) -> Optional[list]:
        """Получение entities из JSON."""
        if self.entities_json:
            return json.loads(self.entities_json)
        return None


@dataclass
class PostQuestionnaireMessage:
    """Модель сообщения после анкеты (отправляется сразу после заполнения анкеты)."""
    id: Optional[int] = None
    text: Optional[str] = None
    entities_json: Optional[str] = None
    media_type: Optional[str] = None  # 'photo', 'video', None
    media_file_id: Optional[str] = None
    buttons_json: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)
    
    def get_entities(self) -> Optional[list]:
        """Получение entities из JSON."""
        if self.entities_json:
            return json.loads(self.entities_json)
        return None
    
    def get_buttons(self) -> Optional[list]:
        """Получение кнопок из JSON."""
        if self.buttons_json:
            return json.loads(self.buttons_json)
        return None


@dataclass
class ChainMessage:
    """Модель сообщения из цепочки (отправляется после 'Сообщения после подписки')."""
    id: Optional[int] = None
    message_number: int = 1  # Порядковый номер сообщения в цепочке
    text: Optional[str] = None
    entities_json: Optional[str] = None
    media_type: Optional[str] = None  # 'photo', 'video', None
    media_file_id: Optional[str] = None
    buttons_json: Optional[str] = None
    delay_minutes: int = 10  # Задержка в минутах после предыдущего сообщения
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)
    
    def get_entities(self) -> Optional[list]:
        """Получение entities из JSON."""
        if self.entities_json:
            return json.loads(self.entities_json)
        return None
    
    def get_buttons(self) -> Optional[list]:
        """Получение кнопок из JSON."""
        if self.buttons_json:
            return json.loads(self.buttons_json)
        return None


@dataclass
class Channel:
    """Модель канала/бота для проверки подписки."""
    id: Optional[int] = None
    chat_id: Optional[str] = None
    username: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None  # 'channel' или 'bot'
    check_subscription: bool = True  # Нужно ли проверять подписку на этот канал
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)


@dataclass
class MailingMessage:
    """Модель сообщения для рассылки."""
    id: Optional[int] = None
    text: Optional[str] = None
    entities_json: Optional[str] = None
    media_type: Optional[str] = None  # 'photo', 'video', None
    media_file_id: Optional[str] = None
    buttons_json: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)
    
    def get_entities(self) -> Optional[list]:
        """Получение entities из JSON."""
        if self.entities_json:
            return json.loads(self.entities_json)
        return None
    
    def get_buttons(self) -> Optional[list]:
        """Получение кнопок из JSON."""
        if self.buttons_json:
            return json.loads(self.buttons_json)
        return None


@dataclass
class Mailing:
    """Модель рассылки."""
    id: Optional[int] = None
    message_id: Optional[int] = None
    sent_count: int = 0
    failed_count: int = 0
    scheduled_time: Optional[str] = None  # Время запланированной рассылки
    status: str = "pending"  # pending, scheduled, sent, failed
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)


@dataclass
class MailingLog:
    """Модель лога рассылки."""
    id: Optional[int] = None
    mailing_id: Optional[int] = None
    user_id: Optional[int] = None
    status: Optional[str] = None  # 'sent', 'failed'
    error_text: Optional[str] = None
    sent_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)


@dataclass
class Statistics:
    """Модель статистики."""
    id: Optional[int] = None
    date: Optional[str] = None
    total_users: int = 0
    active_users: int = 0
    messages_sent: int = 0
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)


@dataclass
class UserActionLog:
    """Модель лога действия пользователя."""
    id: Optional[int] = None
    user_id: Optional[int] = None
    action_type: Optional[str] = None  # command, message, callback, button_click и т.д.
    action_data: Optional[str] = None  # JSON с дополнительными данными
    message_text: Optional[str] = None
    callback_data: Optional[str] = None
    welcome_message_id: Optional[int] = None  # ID активного приветственного сообщения на момент действия
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)


@dataclass
class SimpleWelcomeMessage:
    """Приветствие в режиме «анкета первой» (текст + кнопка «Заполнить анкету»)."""
    id: Optional[int] = None
    text: Optional[str] = None
    entities_json: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def get_entities(self) -> Optional[list]:
        if self.entities_json:
            return json.loads(self.entities_json)
        return None


@dataclass
class ChannelsListMessage:
    """Сообщение со списком каналов (после анкеты в режиме questionnaire_first). Текст может содержать {channels_list}."""
    id: Optional[int] = None
    text: Optional[str] = None
    entities_json: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def get_entities(self) -> Optional[list]:
        if self.entities_json:
            return json.loads(self.entities_json)
        return None


@dataclass
class NoQuestionnaireMessage:
    """Приветствие в режиме «без анкеты» (текст + кнопка «Проверить подписку»)."""
    id: Optional[int] = None
    text: Optional[str] = None
    entities_json: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def get_entities(self) -> Optional[list]:
        if self.entities_json:
            return json.loads(self.entities_json)
        return None


@dataclass
class BotSettings:
    """Модель настроек бота."""
    id: Optional[int] = None
    adjustment_percent: float = 0.0  # Процент корректировки статистики (-100 до +100)
    completed_percent: Optional[float] = None  # «Заполнили анкету» как % от «Активировали» (None = по факту, 0–100 = заданный %)
    welcome_mode: str = "subscription_first"  # subscription_first | questionnaire_first | no_questionnaire
    stats_activated_criterion: str = "bot_entry"  # bot_entry | questionnaire_started | questionnaire_completed
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)
