"""Клавиатуры для администраторов."""
from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """
    Главная клавиатура админ-панели: разделы по режимам + статистика, отчёты, настройки.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Режим «С подпиской»", callback_data="admin_section_subscription")],
            [InlineKeyboardButton(text="📋 Режим «Анкета первой»", callback_data="admin_section_questionnaire")],
            [InlineKeyboardButton(text='🚀 Режим "Без анкеты"', callback_data="admin_section_no_questionnaire")],
            [InlineKeyboardButton(text="🔗 Цепочка сообщений", callback_data="admin_chain")],
            [InlineKeyboardButton(text="📤 Рассылки", callback_data="admin_section_mailings")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_statistics")],
            [InlineKeyboardButton(text="📋 Отчёты о действиях", callback_data="admin_reports")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")]
        ]
    )


def get_admin_section_start_keyboard() -> InlineKeyboardMarkup:
    """Подменю: сообщения после /start (одно сообщение + цепочка)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Сообщение после /start", callback_data="admin_start_message")],
            [InlineKeyboardButton(text="🔗 Цепочка сообщений", callback_data="admin_chain")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )


def get_admin_section_subscription_keyboard() -> InlineKeyboardMarkup:
    """Подменю: режим «С подпиской» — приветствие и каналы для проверки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Приветственное сообщение", callback_data="admin_welcome")],
            [InlineKeyboardButton(text="📢 Каналы для проверки", callback_data="admin_channels")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )


def get_admin_section_questionnaire_keyboard() -> InlineKeyboardMarkup:
    """Подменю: режим «Анкета первой» — приветствие, список каналов, сообщение после анкеты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Приветствие (анкета первой)", callback_data="admin_simple_welcome")],
            [InlineKeyboardButton(text="📋 Сообщение после анкеты", callback_data="admin_post_questionnaire")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )


def get_admin_section_no_questionnaire_keyboard() -> InlineKeyboardMarkup:
    """Подменю: режим «Без анкеты» — сообщение после /start (редактирование и просмотр)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Сообщение после /start", callback_data="admin_no_questionnaire_welcome")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )


def get_admin_section_mailings_keyboard() -> InlineKeyboardMarkup:
    """Подменю: рассылки — шаблоны сообщений и запуск рассылок."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Сообщения для рассылки", callback_data="admin_messages")],
            [InlineKeyboardButton(text="📤 Рассылки", callback_data="admin_mailings")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )


def get_back_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Назад".
    
    Returns:
        InlineKeyboardMarkup с кнопкой назад
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )
    return keyboard


def get_start_message_manage_keyboard(is_active: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура управления сообщением после /start.
    
    Args:
        is_active: Статус активности сообщения
    
    Returns:
        InlineKeyboardMarkup с кнопками управления
    """
    toggle_text = "🔴 Отключить" if is_active else "🟢 Включить"
    toggle_data = "admin_start_message_disable" if is_active else "admin_start_message_enable"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin_start_message_edit")],
            [InlineKeyboardButton(text="📤 Переслать сообщение", callback_data="admin_start_message_forward")],
            [InlineKeyboardButton(text="👁️ Просмотреть", callback_data="admin_start_message_view")],
            [InlineKeyboardButton(text=toggle_text, callback_data=toggle_data)],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_start")]
        ]
    )
    return keyboard


def get_welcome_manage_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура управления приветственным сообщением.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin_welcome_edit")],
            [InlineKeyboardButton(text="📤 Переслать сообщение", callback_data="admin_welcome_forward")],
            [InlineKeyboardButton(text="👁️ Просмотреть", callback_data="admin_welcome_view")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_subscription")]
        ]
    )
    return keyboard


def get_simple_welcome_manage_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления приветствием в режиме «анкета первой» (текст + кнопка «Заполнить анкету»)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data="admin_simple_welcome_edit")],
            [InlineKeyboardButton(text="👁️ Просмотреть", callback_data="admin_simple_welcome_view")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_questionnaire")]
        ]
    )


def get_channels_list_manage_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления сообщением со списком каналов (плейсхолдер {channels_list})."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data="admin_channels_list_edit")],
            [InlineKeyboardButton(text="👁️ Просмотреть", callback_data="admin_channels_list_view")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_questionnaire")]
        ]
    )


def get_no_questionnaire_manage_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления приветствием в режиме «без анкеты»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data="admin_no_questionnaire_edit")],
            [InlineKeyboardButton(text="👁️ Просмотреть", callback_data="admin_no_questionnaire_view")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_questionnaire")]
        ]
    )


def get_channels_manage_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура управления каналами.
    
    Returns:
        InlineKeyboardMarkup с кнопками управления
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_channel_add")],
            [InlineKeyboardButton(text="📋 Список каналов", callback_data="admin_channel_list")],
            [InlineKeyboardButton(text="🗑️ Удалить канал", callback_data="admin_channel_delete")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_subscription")]
        ]
    )
    return keyboard


def get_channel_delete_keyboard(channels: list) -> InlineKeyboardMarkup:
    """
    Клавиатура для удаления каналов.
    
    Args:
        channels: Список каналов
    
    Returns:
        InlineKeyboardMarkup с кнопками удаления
    """
    buttons = []
    for channel in channels[:10]:  # Максимум 10 кнопок
        channel_name = channel.title or channel.username or channel.chat_id or f"Канал #{channel.id}"
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑️ {channel_name[:30]}",
                callback_data=f"admin_channel_delete_{channel.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_channels")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_channel_check_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора проверки подписки для канала.
    
    Returns:
        InlineKeyboardMarkup с кнопками выбора
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверять подписку", callback_data="channel_check_yes")],
            [InlineKeyboardButton(text="❌ Не проверять подписку", callback_data="channel_check_no")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_channels")]
        ]
    )
    return keyboard


def get_messages_manage_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура управления сообщениями для рассылки.
    
    Returns:
        InlineKeyboardMarkup с кнопками управления
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать вручную", callback_data="admin_message_create")],
            [InlineKeyboardButton(text="📤 Переслать сообщение", callback_data="admin_message_forward")],
            [InlineKeyboardButton(text="📋 Список сообщений", callback_data="admin_message_list")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_mailings")]
        ]
    )
    return keyboard


def get_mailing_manage_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура управления рассылками.
    
    Returns:
        InlineKeyboardMarkup с кнопками управления
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить сейчас", callback_data="admin_mailing_send")],
            [InlineKeyboardButton(text="📅 Запланировать", callback_data="admin_mailing_schedule")],
            [InlineKeyboardButton(text="📋 История рассылок", callback_data="admin_mailing_history")],
            [InlineKeyboardButton(text="📊 Запланированные", callback_data="admin_mailing_scheduled")],
            [InlineKeyboardButton(text="⚙️ Настройки таймера", callback_data="admin_mailing_timer")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_mailings")]
        ]
    )
    return keyboard


def get_reports_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура управления отчётами.
    
    Returns:
        InlineKeyboardMarkup с кнопками управления отчётами
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Детальная аналитика", callback_data="admin_report_questionnaire_stats")],
           # [InlineKeyboardButton(text="👤 Действия пользователя", callback_data="admin_report_user")],
           # [InlineKeyboardButton(text="📊 Сводка активности", callback_data="admin_report_summary")],
           # [InlineKeyboardButton(text="📈 Статистика действий", callback_data="admin_report_stats")],
           # [InlineKeyboardButton(text="📋 Все логи", callback_data="admin_report_all")],
            [InlineKeyboardButton(text="📊 Отчёт по действиям", callback_data="admin_report_actions")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )
    return keyboard


def get_period_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора периода для отчёта по действиям (начальный выбор).
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Сегодня", callback_data="admin_report_period_today")],
            [InlineKeyboardButton(text="📅 За неделю", callback_data="admin_report_period_week")],
            [InlineKeyboardButton(text="📅 Календарная неделя", callback_data="admin_report_period_calweek")],
            [InlineKeyboardButton(text="📅 За месяц", callback_data="admin_report_period_month")],
            [InlineKeyboardButton(text="📅 За всё время", callback_data="admin_report_period_all")],
            [InlineKeyboardButton(text="📅 Свой период (дата с — по)", callback_data="admin_report_actions_period_custom")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")]
        ]
    )
    return keyboard


def get_actions_custom_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после показа Отчёта по действиям за свой период."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Другой период", callback_data="admin_report_actions")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
        ]
    )


def get_actions_nav_keyboard(period_type: str, base_date_str: str) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации по периодам для отчёта по действиям: −1 / +1 день (неделя, месяц).
    """
    labels = {
        "today": ("◀ −1 день", "▶ +1 день"),
        "week": ("◀ −1 нед", "▶ +1 нед"),
        "calweek": ("◀ −1 нед", "▶ +1 нед"),
        "month": ("◀ −1 мес", "▶ +1 мес"),
    }
    prev_label, next_label = labels.get(period_type, ("◀ −1", "▶ +1"))
    rows = [
        [
            InlineKeyboardButton(
                text=prev_label,
                callback_data=f"admin_report_prev_{period_type}_{base_date_str}",
            ),
            InlineKeyboardButton(
                text=next_label,
                callback_data=f"admin_report_next_{period_type}_{base_date_str}",
            ),
        ],
        [InlineKeyboardButton(text="📅 Другой период", callback_data="admin_report_actions")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_statistics_period_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора периода для Статистики (начальный выбор).
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Сегодня", callback_data="admin_statistics_period_today")],
            [InlineKeyboardButton(text="📅 За неделю", callback_data="admin_statistics_period_week")],
            [InlineKeyboardButton(text="📅 Календарная неделя", callback_data="admin_statistics_period_calweek")],
            [InlineKeyboardButton(text="📅 За месяц", callback_data="admin_statistics_period_month")],
            [InlineKeyboardButton(text="📅 За всё время", callback_data="admin_statistics_period_all")],
            [InlineKeyboardButton(text="📅 Свой период (дата с — по)", callback_data="admin_statistics_period_custom")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )
    return keyboard


def get_statistics_custom_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после показа статистики за свой период: другой период / назад."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Другой период", callback_data="admin_statistics")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")],
        ]
    )


# Подписи критерия «Активировали бота» в блоке Статистика
STATS_ACTIVATED_CRITERION_LABELS = {
    "bot_entry": "По /start",
    "questionnaire_started": "Увидели анкету",
    "questionnaire_completed": "Заполнили анкету",
    "subscription_check_clicked": "Нажали «Проверить подписку»",
}


def get_statistics_activated_criterion_row(
    current_criterion: str,
    period_type: str,
    base_date_str: str,
) -> list:
    """Кнопки переключения критерия «Активировали бота» (один столбец)."""
    rows = []
    for criterion, label in STATS_ACTIVATED_CRITERION_LABELS.items():
        prefix = "• " if criterion == current_criterion else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix}{label}",
                    callback_data=f"admin_stats_act_{criterion}_{period_type}_{base_date_str}",
                )
            ]
        )
    return rows


def get_statistics_nav_keyboard(period_type: str, base_date_str: str) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации по периодам для Статистики: −1 / +1 день (неделя, месяц).
    """
    labels = {
        "today": ("◀ −1 день", "▶ +1 день"),
        "week": ("◀ −1 нед", "▶ +1 нед"),
        "calweek": ("◀ −1 нед", "▶ +1 нед"),
        "month": ("◀ −1 мес", "▶ +1 мес"),
    }
    prev_label, next_label = labels.get(period_type, ("◀ −1", "▶ +1"))
    rows = [
        [
            InlineKeyboardButton(
                text=prev_label,
                callback_data=f"admin_statistics_prev_{period_type}_{base_date_str}",
            ),
            InlineKeyboardButton(
                text=next_label,
                callback_data=f"admin_statistics_next_{period_type}_{base_date_str}",
            ),
        ],
        [InlineKeyboardButton(text="📅 Другой период", callback_data="admin_statistics")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_questionnaire_period_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора периода для Детальной аналитики (начальный выбор).
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Сегодня", callback_data="admin_report_questionnaire_period_today")],
            [InlineKeyboardButton(text="📅 За неделю", callback_data="admin_report_questionnaire_period_week")],
            [InlineKeyboardButton(text="📅 Календарная неделя", callback_data="admin_report_questionnaire_period_calweek")],
            [InlineKeyboardButton(text="📅 За месяц", callback_data="admin_report_questionnaire_period_month")],
            [InlineKeyboardButton(text="📅 За всё время", callback_data="admin_report_questionnaire_period_all")],
            [InlineKeyboardButton(text="📅 Свой период (дата с — по)", callback_data="admin_report_questionnaire_period_custom")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")]
        ]
    )
    return keyboard


def get_questionnaire_custom_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после показа Детальной аналитики за свой период."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Другой период", callback_data="admin_report_questionnaire_stats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
        ]
    )


def get_questionnaire_nav_keyboard(period_type: str, base_date_str: str) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации по периодам: −1 / +1 день (неделя, месяц).
    period_type: "today" | "week" | "calweek" | "month"
    base_date_str: YYYY-MM-DD (для дня — эта дата, для недели/месяца — начало диапазона).
    """
    labels = {
        "today": ("◀ −1 день", "▶ +1 день"),
        "week": ("◀ −1 нед", "▶ +1 нед"),
        "calweek": ("◀ −1 нед", "▶ +1 нед"),
        "month": ("◀ −1 мес", "▶ +1 мес"),
    }
    prev_label, next_label = labels.get(period_type, ("◀ −1", "▶ +1"))
    rows = [
        [
            InlineKeyboardButton(
                text=prev_label,
                callback_data=f"admin_report_questionnaire_prev_{period_type}_{base_date_str}",
            ),
            InlineKeyboardButton(
                text=next_label,
                callback_data=f"admin_report_questionnaire_next_{period_type}_{base_date_str}",
            ),
        ],
        [InlineKeyboardButton(text="📅 Другой период", callback_data="admin_report_questionnaire_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_post_questionnaire_manage_keyboard(has_message: bool = True, is_active: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура управления сообщением после анкеты.
    has_message: показывать кнопку статуса; is_active: текущий статус для подписи кнопки.
    """
    rows = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin_post_questionnaire_edit")],
        [InlineKeyboardButton(text="📤 Переслать сообщение", callback_data="admin_post_questionnaire_forward")],
        [InlineKeyboardButton(text="👁️ Просмотреть", callback_data="admin_post_questionnaire_view")],
    ]
    if has_message:
        status_btn = "⚪️ Статус: Неактивно" if is_active else "🟢 Статус: Активно"
        rows.append([InlineKeyboardButton(text=status_btn, callback_data="admin_post_questionnaire_toggle")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_section_questionnaire")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_chain_messages_manage_keyboard(chain_is_active: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура управления цепочкой сообщений.
    chain_is_active: статус цепочки целиком (кнопка переключения).
    """
    status_btn = (
        "⚪️ Цепочка: Неактивна"
        if chain_is_active
        else "🟢 Цепочка: Активна"
    )
    rows = [
        [InlineKeyboardButton(text=status_btn, callback_data="admin_chain_toggle")],
        [InlineKeyboardButton(text="➕ Добавить сообщение", callback_data="admin_chain_add")],
        [InlineKeyboardButton(text="📋 Список сообщений", callback_data="admin_chain_list")],
        [InlineKeyboardButton(text="✏️ Редактировать сообщение", callback_data="admin_chain_edit")],
        [InlineKeyboardButton(text="📤 Переслать сообщение", callback_data="admin_chain_forward")],
        [InlineKeyboardButton(text="🗑 Удалить сообщение", callback_data="admin_chain_delete")],
        [InlineKeyboardButton(text="⚙️ Настроить интервалы", callback_data="admin_chain_intervals")],
        [InlineKeyboardButton(text="👁 Просмотреть цепочку", callback_data="admin_chain_preview")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_chain_list_keyboard(
    items: list[tuple[int, bool]],
    chain_is_active: bool = True
) -> InlineKeyboardMarkup:
    """
    Клавиатура списка сообщений цепочки с переключением статуса каждого.
    items: список (message_number, is_active).
    chain_is_active: для кнопки статуса цепочки.
    """
    rows = []
    for num, is_active in items:
        label = f"Сообщение {num}: {'🟢 Активно' if is_active else '⚪️ Неактивно'}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"admin_chain_toggle_msg_{num}")])
    status_btn = "⚪️ Цепочка: Неактивна" if chain_is_active else "🟢 Цепочка: Активна"
    rows.append([InlineKeyboardButton(text=status_btn, callback_data="admin_chain_toggle")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_chain")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_chain_intervals_keyboard(
    chain_messages: list,
) -> InlineKeyboardMarkup:
    """
    Клавиатура меню «Настройка интервалов»: кнопки для изменения интервала каждого сообщения.
    chain_messages: список ChainMessage (для отображения текущего интервала).
    """
    rows = []
    for msg in sorted(chain_messages, key=lambda x: x.message_number):
        rows.append([
            InlineKeyboardButton(
                text=f"Сообщение {msg.message_number}: {msg.delay_minutes} мин.",
                callback_data=f"admin_chain_interval_edit_{msg.message_number}"
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_chain")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_chain_message_select_keyboard(chain_messages: list) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора сообщения для редактирования.
    chain_messages: список ChainMessage из БД.
    """
    rows = []
    for msg in sorted(chain_messages, key=lambda x: x.message_number):
        rows.append([
            InlineKeyboardButton(
                text=f"📨 Сообщение {msg.message_number}",
                callback_data=f"admin_chain_edit_{msg.message_number}",
            )
        ])
    rows.append([InlineKeyboardButton(text="➕ Добавить сообщение", callback_data="admin_chain_add")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_chain")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_chain_message_forward_select_keyboard(chain_messages: list) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора сообщения для создания через пересылку.
    chain_messages: список ChainMessage из БД.
    """
    rows = []
    for msg in sorted(chain_messages, key=lambda x: x.message_number):
        rows.append([
            InlineKeyboardButton(
                text=f"📨 Сообщение {msg.message_number}",
                callback_data=f"admin_chain_forward_{msg.message_number}",
            )
        ])
    rows.append([InlineKeyboardButton(text="➕ Добавить сообщение", callback_data="admin_chain_add_forward")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_chain")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_chain_delete_keyboard(chain_messages: list) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора сообщения для удаления.
    chain_messages: список ChainMessage из БД.
    """
    rows = []
    for msg in sorted(chain_messages, key=lambda x: x.message_number):
        preview = (msg.text or "Без текста")[:30]
        rows.append([
            InlineKeyboardButton(
                text=f"🗑 Сообщение {msg.message_number}: {preview}",
                callback_data=f"admin_chain_delete_{msg.message_number}",
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_chain")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_settings_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню «Настройка»: три раздела + Назад в админку."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔀 Режим приветствия", callback_data="admin_settings_section_mode")],
            [InlineKeyboardButton(text="📊 Корректировка статистики", callback_data="admin_settings_section_adjustment")],
            [InlineKeyboardButton(text="✅ «Заполнили» от «Активировали»", callback_data="admin_settings_section_completed")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )


def get_settings_mode_keyboard(welcome_mode: str = "subscription_first") -> InlineKeyboardMarkup:
    """Подменю настройки режима приветствия: две кнопки режимов + Назад в меню настроек."""
    sub_active = welcome_mode == "subscription_first"
    quest_active = welcome_mode == "questionnaire_first"
    no_q_active = welcome_mode == "no_questionnaire"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=("✅ " if sub_active else "🔀 ") + "С подпиской",
                    callback_data="admin_welcome_mode_subscription",
                )
            ],
            [
                InlineKeyboardButton(
                    text=("✅ " if quest_active else "🔀 ") + "Анкета первой",
                    callback_data="admin_welcome_mode_questionnaire",
                )
            ],
            [
                InlineKeyboardButton(
                    text=("✅ " if no_q_active else "🔀 ") + "Без анкеты",
                    callback_data="admin_welcome_mode_no_questionnaire",
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_settings")]
        ]
    )


def get_settings_adjustment_keyboard() -> InlineKeyboardMarkup:
    """Подменю корректировки процента статистики + Назад в меню настроек."""
    rows = [
        [InlineKeyboardButton(text="0%", callback_data="settings_percent_0")],
        [
            InlineKeyboardButton(text="+5%", callback_data="settings_percent_5"),
            InlineKeyboardButton(text="-5%", callback_data="settings_percent_-5")
        ],
        [
            InlineKeyboardButton(text="+10%", callback_data="settings_percent_10"),
            InlineKeyboardButton(text="-10%", callback_data="settings_percent_-10")
        ],
        [
            InlineKeyboardButton(text="+25%", callback_data="settings_percent_25"),
            InlineKeyboardButton(text="-25%", callback_data="settings_percent_-25")
        ],
        [
            InlineKeyboardButton(text="+50%", callback_data="settings_percent_50"),
            InlineKeyboardButton(text="-50%", callback_data="settings_percent_-50")
        ],
        [
            InlineKeyboardButton(text="+75%", callback_data="settings_percent_75"),
            InlineKeyboardButton(text="-75%", callback_data="settings_percent_-75")
        ],
        [
            InlineKeyboardButton(text="+100%", callback_data="settings_percent_100"),
            InlineKeyboardButton(text="-100%", callback_data="settings_percent_-100")
        ],
        [InlineKeyboardButton(text="✏️ Ввести значение", callback_data="settings_percent_custom")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_settings_completed_keyboard(completed_percent: Optional[float] = None) -> InlineKeyboardMarkup:
    """Подменю «Заполнили анкету» как % от «Активировали» + Назад в меню настроек."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="По факту (заполнили)", callback_data="completed_percent_off")],
            [
                InlineKeyboardButton(text="10%", callback_data="completed_percent_10"),
                InlineKeyboardButton(text="25%", callback_data="completed_percent_25"),
                InlineKeyboardButton(text="50%", callback_data="completed_percent_50")
            ],
            [
                InlineKeyboardButton(text="75%", callback_data="completed_percent_75"),
                InlineKeyboardButton(text="100%", callback_data="completed_percent_100"),
                InlineKeyboardButton(text="✏️ Своё", callback_data="completed_percent_custom")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_settings")]
        ]
    )


FLOW_STEP_NAMES = {
    1: "Приветствие",
    2: "Старт анкеты",
    3: "Сообщение после анкеты",
    4: "Цепочка сообщений",
}

def get_flow_order_keyboard(flow_order: list[int]) -> InlineKeyboardMarkup:
    """Клавиатура перестановки порядка типов 1,2,3 (своп соседних). Цепочка (4) в настройках не показывается."""
    rows = []
    for i in range(len(flow_order) - 1):
        a, b = flow_order[i], flow_order[i + 1]
        name_a = FLOW_STEP_NAMES.get(a, str(a))
        name_b = FLOW_STEP_NAMES.get(b, str(b))
        rows.append([
            InlineKeyboardButton(
                text=f"↔️ {name_a} ↔ {name_b}",
                callback_data=f"flow_order_swap_{i}_{i + 1}"
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_completed_percent_keyboard(completed_percent: Optional[float] = None) -> InlineKeyboardMarkup:
    """Клавиатура только для настройки «Заполнили анкету» как % от «Активировали»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="По факту", callback_data="completed_percent_off")],
            [
                InlineKeyboardButton(text="10%", callback_data="completed_percent_10"),
                InlineKeyboardButton(text="25%", callback_data="completed_percent_25"),
                InlineKeyboardButton(text="50%", callback_data="completed_percent_50")
            ],
            [
                InlineKeyboardButton(text="75%", callback_data="completed_percent_75"),
                InlineKeyboardButton(text="100%", callback_data="completed_percent_100"),
                InlineKeyboardButton(text="✏️ Своё", callback_data="completed_percent_custom")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )
