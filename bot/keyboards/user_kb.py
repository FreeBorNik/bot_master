"""Клавиатуры для пользователей."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_subscription_check_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для проверки подписки.
    
    Returns:
        InlineKeyboardMarkup с кнопкой проверки подписки
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Проверить подписку", callback_data="check_subscription")]
        ]
    )
    return keyboard


def get_no_questionnaire_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для режима «без анкеты».

    Returns:
        InlineKeyboardMarkup с кнопкой получения ссылки
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Получить ссылку", callback_data="check_subscription")]
        ]
    )
    return keyboard


def get_fill_questionnaire_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой «Заполнить анкету» (режим приветствия «анкета первой»)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Заполнить анкету", callback_data="start_questionnaire_simple")]
        ]
    )


def get_i_subscribed_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Я подписчик".
    
    Returns:
        InlineKeyboardMarkup с кнопкой "Я подписчик"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я подписчик", callback_data="i_subscribed")]
        ]
    )
    return keyboard


def get_age_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора возраста.
    
    Returns:
        InlineKeyboardMarkup с кнопками диапазонов возраста
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="18-25", callback_data="questionnaire_age_18-25")],
            [InlineKeyboardButton(text="25-40", callback_data="questionnaire_age_25-40")],
            [InlineKeyboardButton(text="40-65", callback_data="questionnaire_age_40-65")]
        ]
    )
    return keyboard


def get_hours_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора часов работы.
    
    Returns:
        InlineKeyboardMarkup с кнопками диапазонов часов
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="до 2 часов в день", callback_data="questionnaire_hours_up_to_2")],
            [InlineKeyboardButton(text="от 2 до 4 часов в день", callback_data="questionnaire_hours_2_to_4")],
            [InlineKeyboardButton(text="более 4 часов в день", callback_data="questionnaire_hours_more_than_4")]
        ]
    )
    return keyboard


def get_other_job_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора наличия другой работы.
    
    Returns:
        InlineKeyboardMarkup с кнопками Да/Нет
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="questionnaire_job_yes"),
                InlineKeyboardButton(text="Нет", callback_data="questionnaire_job_no")
            ]
        ]
    )
    return keyboard
