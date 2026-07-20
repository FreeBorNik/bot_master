"""FSM состояния для администраторов."""
from aiogram.fsm.state import State, StatesGroup


class StartMessageStates(StatesGroup):
    """Состояния для создания/редактирования сообщения после /start."""
    text = State()


class WelcomeMessageStates(StatesGroup):
    """Состояния для создания/редактирования приветственного сообщения."""
    text = State()
    media = State()
    buttons = State()
    waiting_for_channel_check = State()  # Выбор проверки подписки для каналов из приветственного сообщения


class SimpleWelcomeMessageStates(StatesGroup):
    """Состояния для приветствия в режиме «анкета первой» (текст + кнопка «Заполнить анкету»)."""
    text = State()


class ChannelsListMessageStates(StatesGroup):
    """Состояния для сообщения со списком каналов (плейсхолдер {channels_list})."""
    text = State()


class NoQuestionnaireMessageStates(StatesGroup):
    """Состояния для приветствия в режиме «без анкеты»."""
    text = State()


class PostQuestionnaireMessageStates(StatesGroup):
    """Состояния для создания/редактирования сообщения после анкеты."""
    text = State()
    media = State()
    buttons = State()
    waiting_for_buttons = State()


class ChainMessageStates(StatesGroup):
    """Состояния для управления цепочкой сообщений."""
    select_message = State()  # Выбор номера сообщения для редактирования
    text = State()  # Редактирование текста
    media = State()  # Редактирование медиа
    buttons = State()  # Редактирование кнопок
    waiting_for_buttons = State()  # Ожидание кнопок
    delay_minutes = State()  # Настройка интервала времени


class ChainIntervalOnlyStates(StatesGroup):
    """Состояния для изменения только интервалов в меню «Настройка интервалов»."""
    delay_minutes = State()


class MailingMessageStates(StatesGroup):
    """Состояния для создания сообщения для рассылки."""
    text = State()
    media = State()
    buttons = State()
    waiting_for_buttons = State()  # Ожидание сообщения с кнопками


class ChannelAddStates(StatesGroup):
    """Состояния для добавления канала."""
    waiting_for_channel = State()
    waiting_for_check_subscription = State()  # Выбор: проверять подписку или нет


class MailingScheduleStates(StatesGroup):
    """Состояния для планирования рассылки."""
    waiting_for_time = State()


class ReportStates(StatesGroup):
    """Состояния для просмотра отчётов."""
    waiting_for_user_id = State()


class SettingsStates(StatesGroup):
    """Состояния для настройки процента корректировки статистики."""
    waiting_for_percent = State()
    waiting_for_completed_percent = State()


class StatisticsCustomPeriodStates(StatesGroup):
    """Состояния для ввода своего периода в меню Статистика."""
    date_from = State()
    date_to = State()


class QuestionnaireCustomPeriodStates(StatesGroup):
    """Состояния для своего периода в Детальной аналитике."""
    date_from = State()
    date_to = State()


class ActionsCustomPeriodStates(StatesGroup):
    """Состояния для своего периода в Отчёте по действиям."""
    date_from = State()
    date_to = State()
