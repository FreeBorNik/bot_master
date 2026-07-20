"""Роутер для администраторов."""
from typing import Any, Optional
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
import json
import os

from bot.config import RunnerConfig
from bot.database.db import Database
from bot.database.repositories import (
    StartMessageRepository,
    WelcomeMessageRepository,
    SimpleWelcomeMessageRepository,
    ChannelsListMessageRepository,
    NoQuestionnaireMessageRepository,
    PostQuestionnaireMessageRepository,
    ChainMessageRepository,
    ChannelRepository,
    MailingMessageRepository,
    MailingRepository,
    MailingLogRepository,
    UserRepository,
    SettingsRepository,
)
from bot.database.action_logs_repository import UserActionLogRepository
from bot.keyboards.admin_kb import (
    get_admin_main_keyboard,
    get_admin_section_start_keyboard,
    get_admin_section_subscription_keyboard,
    get_admin_section_questionnaire_keyboard,
    get_admin_section_no_questionnaire_keyboard,
    get_admin_section_mailings_keyboard,
    get_back_keyboard,
    get_start_message_manage_keyboard,
    get_welcome_manage_keyboard,
    get_simple_welcome_manage_keyboard,
    get_channels_list_manage_keyboard,
    get_no_questionnaire_manage_keyboard,
    get_post_questionnaire_manage_keyboard,
    get_chain_messages_manage_keyboard,
    get_chain_list_keyboard,
    get_chain_intervals_keyboard,
    get_chain_message_select_keyboard,
    get_chain_message_forward_select_keyboard,
    get_chain_delete_keyboard,
    get_channels_manage_keyboard,
    get_channel_delete_keyboard,
    get_channel_check_subscription_keyboard,
    get_messages_manage_keyboard,
    get_mailing_manage_keyboard,
    get_reports_keyboard,
    get_period_selection_keyboard,
    get_actions_nav_keyboard,
    get_statistics_period_keyboard,
    get_statistics_nav_keyboard,
    get_statistics_custom_result_keyboard,
    get_statistics_activated_criterion_row,
    STATS_ACTIVATED_CRITERION_LABELS,
    get_questionnaire_period_keyboard,
    get_questionnaire_nav_keyboard,
    get_questionnaire_custom_result_keyboard,
    get_actions_custom_result_keyboard,
    get_settings_main_keyboard,
    get_settings_mode_keyboard,
    get_settings_adjustment_keyboard,
    get_settings_completed_keyboard,
    get_flow_order_keyboard,
    FLOW_STEP_NAMES,
)
from bot.states.admin_states import (
    StartMessageStates,
    WelcomeMessageStates,
    SimpleWelcomeMessageStates,
    ChannelsListMessageStates,
    NoQuestionnaireMessageStates,
    PostQuestionnaireMessageStates,
    ChainMessageStates,
    ChainIntervalOnlyStates,
    ChannelAddStates,
    MailingMessageStates,
    MailingScheduleStates,
    ReportStates,
    SettingsStates,
    StatisticsCustomPeriodStates,
    QuestionnaireCustomPeriodStates,
    ActionsCustomPeriodStates,
)
from aiogram3_calendar import SimpleCalendar
from aiogram3_calendar.calendar_types import (
    SimpleCalendarAction,
    SimpleCalendarCallback,
)
from bot.utils.helpers import parse_entities_from_json, apply_welcome_placeholders, entities_to_html, resolve_button_url
from bot.utils.logger import setup_logger
from bot.handlers.user_router import send_chain_message, _send_media_with_text

logger = setup_logger(__name__)

router = Router(name="admin")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """
    Обработчик команды /admin - главное меню админ-панели.
    
    Args:
        message: Объект сообщения
    """
    await message.answer(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        disable_web_page_preview=True
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /cancel - отмена текущего действия.
    
    Args:
        message: Объект сообщения
        state: FSM контекст
    """
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=get_admin_main_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик кнопки "Назад" в админ-панели.
    
    Args:
        callback: Callback запрос
        state: FSM контекст
        bot: Экземпляр бота
    """
    await callback.answer()
    await state.clear()
    
    # Если сообщение содержит фото/видео, удаляем его и отправляем новое текстовое
    if callback.message.photo or callback.message.video:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="🔐 <b>Админ-панель</b>\n\n"
                 "Выберите раздел для управления:",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
    else:
        await callback.message.edit_text(
            "🔐 <b>Админ-панель</b>\n\n"
            "Выберите раздел для управления:",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "admin_section_start")
async def admin_section_start(callback: CallbackQuery) -> None:
    """Подменю: сообщения после /start."""
    await callback.answer()
    await callback.message.edit_text(
        "📍 <b>Сообщения после /start</b>\n\n"
        "Настройте что показывается пользователю сразу после /start: одно сообщение или цепочка сообщений.",
        reply_markup=get_admin_section_start_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_section_subscription")
async def admin_section_subscription(callback: CallbackQuery) -> None:
    """Подменю: режим «С подпиской»."""
    await callback.answer()
    await callback.message.edit_text(
        "🔐 <b>Режим «С подпиской»</b>\n\n"
        "Приветствие с кнопкой «Проверить подписку» → проверка подписки на выбранные каналы.\n\n"
        "✅ После успешной проверки подписки запускается анкета.\n\n"
        "После успешной проверки при необходимости запускается цепочка сообщений.",
        reply_markup=get_admin_section_subscription_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_section_questionnaire")
async def admin_section_questionnaire(callback: CallbackQuery) -> None:
    """Подменю: режим «Анкета первой»."""
    await callback.answer()
    await callback.message.edit_text(
        "📋 <b>Режим «Анкета первой»</b>\n\n"
        "Приветствие с кнопкой «Заполнить анкету» → анкета → проверка подписки → сообщение после анкеты.\n\n"
        "В этом разделе настраиваются тексты для данного режима.",
        reply_markup=get_admin_section_questionnaire_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_section_no_questionnaire")
async def admin_section_no_questionnaire(callback: CallbackQuery) -> None:
    """Подменю: режим «Без анкеты»."""
    await callback.answer()
    await callback.message.edit_text(
        "🚀 <b>Режим «Без анкеты»</b>\n\n"
        "После /start пользователь получает отдельное сообщение с кнопкой «Получить ссылку».\n\n"
        "В этом разделе можно редактировать и просматривать это сообщение.",
        reply_markup=get_admin_section_no_questionnaire_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_section_mailings")
async def admin_section_mailings(callback: CallbackQuery) -> None:
    """Подменю: рассылки."""
    await callback.answer()
    await callback.message.edit_text(
        "📤 <b>Рассылки</b>\n\n"
        "Шаблоны сообщений для рассылки и запуск рассылок.",
        reply_markup=get_admin_section_mailings_keyboard(),
        disable_web_page_preview=True
    )


# ========== Управление сообщением после /start ==========

@router.callback_query(F.data == "admin_start_message")
async def admin_start_message_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню управления сообщением после /start."""
    await callback.answer()
    
    start_repo = StartMessageRepository(db)
    start_msg = await start_repo.get_latest_start_message()  # Используем метод для получения последнего независимо от статуса
    
    if start_msg:
        status_text = "🟢 Включено" if start_msg.is_active else "🔴 Отключено"
        text = (
            "🚀 <b>Сообщение после /start</b>\n\n"
            f"Статус: {status_text}\n\n"
            f"Текущее сообщение:\n\n{start_msg.text[:200]}..."
            if len(start_msg.text) > 200
            else f"Текущее сообщение:\n\n{start_msg.text}"
        )
    else:
        text = (
            "🚀 <b>Сообщение после /start</b>\n\n"
            "Сообщение после /start еще не создано.\n"
            "Нажмите 'Редактировать' для создания."
        )
    
    is_active = start_msg.is_active if start_msg else False
    await callback.message.edit_text(
        text,
        reply_markup=get_start_message_manage_keyboard(is_active),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_start_message_view")
async def admin_start_message_view(callback: CallbackQuery, db: Database) -> None:
    """Просмотр сообщения после /start."""
    await callback.answer()
    
    start_repo = StartMessageRepository(db)
    start_msg = await start_repo.get_latest_start_message()  # Используем метод для получения последнего независимо от статуса
    
    if start_msg:
        await callback.message.answer("<b>Текущее сообщение после /start:</b>", disable_web_page_preview=True)
        
        entities = parse_entities_from_json(start_msg.entities_json)
        admin = callback.from_user
        text_preview, entities_preview = apply_welcome_placeholders(
            start_msg.text,
            first_name=admin.first_name or "Имя",
            full_name=admin.full_name,
            username=admin.username,
            entities=entities,
        )
        
        if entities_preview:
            await callback.message.answer(
                text_preview,
                entities=entities_preview,
                parse_mode=None,
                disable_web_page_preview=True
            )
        else:
            await callback.message.answer(text_preview, disable_web_page_preview=True)
        
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_start_message_manage_keyboard(start_msg.is_active),
            disable_web_page_preview=True
        )
    else:
        await callback.message.answer(
            "❌ Сообщение после /start еще не создано.",
            reply_markup=get_start_message_manage_keyboard(False),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "admin_start_message_edit")
async def admin_start_message_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования сообщения после /start."""
    await callback.answer()
    await state.set_state(StartMessageStates.text)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование сообщения после /start</b>\n\n"
        "Отправьте новое сообщение после /start.\n\n"
        "Для подстановки имени пользователя используйте плейсхолдеры:\n"
        "• <code>{first_name}</code> — имя\n"
            "• <code>{full_name}</code> — полное имя\n"
            "• <code>{username}</code> — username (без @)\n\n"
            "Пример: «Здравствуйте, {first_name}! Добро пожаловать!»\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_start_message_forward")
async def admin_start_message_forward_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало создания сообщения после /start через пересылку."""
    await callback.answer()
    await state.set_state("admin_start_message_forward")
    
    await callback.message.edit_text(
        "📤 <b>Создание сообщения после /start через пересылку</b>\n\n"
        "Перешлите сообщение, которое хотите использовать как сообщение после /start.\n\n"
        "💡 Это сообщение отправляется пользователям сразу после команды /start (самым первым).\n"
        "Поддерживается только текст и форматирование.\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(StartMessageStates.text)
async def admin_start_message_edit_text(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение сообщения после /start."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    text = message.text or ""
    entities_json = None
    
    # Получаем entities
    entities = message.entities or []
    if entities:
        entities_list = []
        for entity in entities:
            entity_dict = {
                "type": entity.type,
                "offset": entity.offset,
                "length": entity.length
            }
            if entity.type == "text_link":
                entity_dict["url"] = entity.url
            entities_list.append(entity_dict)
        entities_json = json.dumps(entities_list, ensure_ascii=False)
        logger.info(f"Сохранено {len(entities_list)} entities для сообщения после /start")
    
    start_repo = StartMessageRepository(db)
    await start_repo.create_or_update_start_message(text, entities_json)
    
    await state.clear()
    await message.answer(
        "✅ Сообщение после /start успешно сохранено!\n\n"
        "💡 Это сообщение будет отправляться пользователям сразу после команды /start (самым первым).",
        reply_markup=get_admin_main_keyboard(),
        disable_web_page_preview=True
    )
    logger.info(f"Админ {message.from_user.id} обновил сообщение после /start")


@router.callback_query(F.data.in_(["admin_start_message_enable", "admin_start_message_disable"]))
async def admin_start_message_toggle(callback: CallbackQuery, db: Database) -> None:
    """Включение/отключение сообщения после /start."""
    await callback.answer()
    
    is_enable = callback.data == "admin_start_message_enable"
    start_repo = StartMessageRepository(db)
    start_msg = await start_repo.get_latest_start_message()  # Используем метод для получения последнего независимо от статуса
    
    if not start_msg:
        await callback.message.answer(
            "❌ Сообщение после /start еще не создано. Сначала создайте сообщение.",
            reply_markup=get_start_message_manage_keyboard(False),
            disable_web_page_preview=True
        )
        return
    
    await start_repo.toggle_active(is_enable)
    
    # Получаем обновленное сообщение для отображения актуального статуса
    updated_msg = await start_repo.get_latest_start_message()
    is_active = updated_msg.is_active if updated_msg else False
    
    status_text = "включено" if is_enable else "отключено"
    await callback.message.answer(
        f"✅ Сообщение после /start {status_text}.",
        reply_markup=get_start_message_manage_keyboard(is_active),
        disable_web_page_preview=True
    )


# ========== Управление приветственным сообщением ==========

@router.callback_query(F.data == "admin_welcome")
async def admin_welcome_menu(callback: CallbackQuery, db: Database) -> None:
    """
    Меню управления приветственным сообщением.
    
    Args:
        callback: Callback запрос
        db: База данных
    """
    await callback.answer()
    
    welcome_repo = WelcomeMessageRepository(db)
    welcome_msg = await welcome_repo.get_welcome_message()
    
    if welcome_msg:
        text = (
            "📝 <b>Приветственное сообщение</b>\n\n"
            f"Текущее сообщение:\n\n{welcome_msg.text[:200]}..."
            if len(welcome_msg.text) > 200
            else f"Текущее сообщение:\n\n{welcome_msg.text}"
        )
    else:
        text = (
            "📝 <b>Приветственное сообщение</b>\n\n"
            "Приветственное сообщение еще не создано.\n"
            "Нажмите 'Редактировать' для создания."
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_welcome_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_welcome_view")
async def admin_welcome_view(callback: CallbackQuery, db: Database) -> None:
    """
    Просмотр приветственного сообщения.
    Заголовок отправляется отдельно, чтобы смещения entities совпадали с текстом.
    """
    await callback.answer()
    
    welcome_repo = WelcomeMessageRepository(db)
    welcome_msg = await welcome_repo.get_welcome_message()
    
    if welcome_msg:
        # Сначала отправляем заголовок отдельным сообщением
        await callback.message.answer("<b>Текущее приветственное сообщение:</b>", disable_web_page_preview=True)
        
        # Подставляем имя того, кто вызвал предпросмотр (администратора)
        entities = parse_entities_from_json(welcome_msg.entities_json)
        admin = callback.from_user
        text_preview, entities_preview = apply_welcome_placeholders(
            welcome_msg.text,
            first_name=admin.first_name or "Имя",
            full_name=admin.full_name,
            username=admin.username,
            entities=entities,
        )
        
        if entities_preview:
            await callback.message.answer(
                text_preview,
                entities=entities_preview,
                parse_mode=None,  # Важно: None для работы entities
                disable_web_page_preview=True
            )
        else:
            await callback.message.answer(text_preview, disable_web_page_preview=True)
        
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_welcome_manage_keyboard(),
            disable_web_page_preview=True
        )
    else:
        await callback.message.answer(
            "❌ Приветственное сообщение еще не создано.",
            reply_markup=get_welcome_manage_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "admin_welcome_edit")
async def admin_welcome_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начало редактирования приветственного сообщения.
    
    Args:
        callback: Callback запрос
        state: FSM контекст
    """
    await callback.answer()
    await state.set_state(WelcomeMessageStates.text)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование приветственного сообщения</b>\n\n"
        "Отправьте новое приветственное сообщение.\n"
        "Вы можете использовать форматирование и ссылки на каналы.\n\n"
        "Для подстановки имени пользователя используйте плейсхолдеры:\n"
        "• <code>{first_name}</code> — имя\n"
        "• <code>{full_name}</code> — полное имя\n"
        "• <code>{username}</code> — username (без @)\n\n"
        "Пример: «Здравствуйте, {first_name}! Спасибо за отклик!»\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_welcome_forward")
async def admin_welcome_forward_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начало создания приветственного сообщения через пересылку.
    
    Args:
        callback: Callback запрос
        state: FSM контекст
    """
    await callback.answer()
    await state.set_state("admin_welcome_forward")
    
    await callback.message.edit_text(
        "📤 <b>Создание приветственного сообщения через пересылку</b>\n\n"
        "Перешлите сообщение, которое хотите использовать как приветственное сообщение.\n\n"
        "💡 Приветственное сообщение отправляется пользователям при команде /start.\n"
        "📌 Ссылки на каналы будут автоматически извлечены и добавлены в список для проверки подписки.\n\n"
        "⚠️ Примечание: медиа и кнопки из пересланного сообщения не сохраняются (только текст и форматирование).\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(WelcomeMessageStates.text)
async def admin_welcome_edit_text(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    """
    Сохранение приветственного сообщения и автоматическое добавление каналов.
    
    Args:
        message: Сообщение с текстом
        state: FSM контекст
        db: База данных
        bot: Экземпляр бота
    """
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    # Сохранение текста и entities
    text = message.text or message.caption or ""
    entities_json = None
    
    # Получаем entities из message.entities или message.caption_entities
    entities = message.entities or message.caption_entities or []
    
    if entities:
        entities_list = []
        for entity in entities:
            entity_dict = {
                "type": entity.type,
                "offset": entity.offset,
                "length": entity.length
            }
            # Для text_link сохраняем URL
            if entity.type == "text_link":
                entity_dict["url"] = entity.url
            entities_list.append(entity_dict)
        entities_json = json.dumps(entities_list, ensure_ascii=False)
        logger.info(f"Сохранено {len(entities_list)} entities для приветственного сообщения")
    
    # Сохранение в БД
    welcome_repo = WelcomeMessageRepository(db)
    await welcome_repo.create_or_update_welcome_message(text, entities_json)
    
    # Парсинг ссылок из приветственного сообщения и сохранение каналов в БД
    from bot.utils.helpers import extract_channel_links
    from bot.database.repositories import ChannelRepository
    
    channels_found = extract_channel_links(text, entities_json=entities_json)
    channel_repo = ChannelRepository(db)
    
    # Сначала собираем все каналы из нового сообщения с их данными
    new_channel_data = []  # Список кортежей (identifier, channel_type, chat_id, username, title)
    
    for username_or_id, channel_type in channels_found:
        try:
            # Если это invite-ссылка (начинается с +), обрабатываем отдельно
            if channel_type == "channel_invite":
                new_channel_data.append((
                    username_or_id,
                    channel_type,
                    None,
                    username_or_id,  # Сохраняем invite-ссылку в username
                    f"Приватный канал ({username_or_id[:20]}...)"
                ))
                continue
            
            # Для обычных каналов пытаемся получить информацию
            try:
                # Формируем правильный идентификатор для get_chat
                chat_identifier = username_or_id if username_or_id.startswith("@") else f"@{username_or_id}"
                chat = await bot.get_chat(chat_identifier)
                chat_id = str(chat.id)
                username = chat.username
                title = chat.title
                
                new_channel_data.append((
                    username_or_id,
                    channel_type,
                    chat_id,
                    username,
                    title
                ))
            except Exception as e:
                logger.warning(f"Не удалось получить информацию о канале {username_or_id}: {e}")
                # Все равно добавляем с минимальной информацией
                if username_or_id.startswith("@"):
                    username = username_or_id[1:]
                else:
                    username = username_or_id
                
                new_channel_data.append((
                    username_or_id,
                    channel_type,
                    None,
                    username,
                    None
                ))
        except Exception as e:
            logger.error(f"Ошибка при обработке канала {username_or_id}: {e}")
    
    # Сначала собираем новые каналы (которых еще нет в БД)
    new_channels_to_add = []
    existing_channels = await channel_repo.get_all_channels()
    
    for identifier, channel_type, chat_id, username, title in new_channel_data:
        try:
            # Проверяем, существует ли уже такой канал
            exists = False
            if chat_id:
                exists = any(
                    ch.chat_id == chat_id for ch in existing_channels
                )
            if not exists and username:
                exists = any(
                    ch.username == username for ch in existing_channels
                )
            
            if not exists:
                new_channels_to_add.append({
                    "identifier": identifier,
                    "channel_type": channel_type,
                    "chat_id": chat_id,
                    "username": username,
                    "title": title
                })
        except Exception as e:
            logger.error(f"Ошибка при проверке канала {identifier}: {e}")
    
    # Если есть новые каналы, сохраняем их в FSM и показываем выбор проверки подписки
    # Удаление старых каналов произойдёт после обработки всех новых
    if new_channels_to_add:
        # Сохраняем список новых каналов и все каналы из сообщения в FSM
        await state.update_data(
            new_channels=new_channels_to_add,
            all_channel_data=new_channel_data,  # Все каналы из нового сообщения (для удаления старых)
            current_channel_index=0,
            added_count=0  # Счётчик добавленных каналов (с check_subscription=True)
        )
        await state.set_state(WelcomeMessageStates.waiting_for_channel_check)
        
        # Показываем первый канал для выбора
        first_channel = new_channels_to_add[0]
        channel_name = first_channel["title"] or first_channel["username"] or first_channel["identifier"]
        
        await message.answer(
            f"✅ Приветственное сообщение успешно сохранено!\n\n"
            f"📢 Найдено новых каналов: {len(new_channels_to_add)}\n\n"
            f"<b>Канал 1/{len(new_channels_to_add)}</b>\n"
            f"Название: {channel_name}\n\n"
            f"<b>Нужно ли проверять подписку на этот канал?</b>",
            reply_markup=get_channel_check_subscription_keyboard(),
            disable_web_page_preview=True
        )
    else:
        # Нет новых каналов - удаляем старые каналы, которых нет в новом сообщении
        deleted_count = await channel_repo.delete_channels_not_in_list(new_channel_data)
        
        await state.clear()
        
        response_text = "✅ Приветственное сообщение успешно сохранено!\n\n"
        
        if deleted_count > 0:
            response_text += f"🗑️ Удалено каналов, отсутствующих в новом сообщении: {deleted_count}\n"
        else:
            response_text += "📢 Каналы в сообщении уже присутствуют в базе данных."
        
        await message.answer(
            response_text,
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
    
    logger.info(f"Админ {message.from_user.id} обновил приветственное сообщение")


# ========== Приветствие (режим «анкета первой») ==========

@router.callback_query(F.data == "admin_simple_welcome")
async def admin_simple_welcome_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню приветствия в режиме «анкета первой» (текст + кнопка «Заполнить анкету»)."""
    await callback.answer()
    repo = SimpleWelcomeMessageRepository(db)
    msg = await repo.get_simple_welcome_message()
    if msg and msg.text:
        preview = msg.text[:200] + "..." if len(msg.text) > 200 else msg.text
        text = "📝 <b>Приветствие (анкета первой)</b>\n\nТекущий текст:\n\n" + preview
    else:
        text = (
            "📝 <b>Приветствие (анкета первой)</b>\n\n"
            "Текст ещё не задан. Под ним будет кнопка «Заполнить анкету».\n"
            "Нажмите «Редактировать текст»."
        )
    await callback.message.edit_text(
        text,
        reply_markup=get_simple_welcome_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_simple_welcome_view")
async def admin_simple_welcome_view(callback: CallbackQuery, db: Database) -> None:
    """Просмотр приветствия (анкета первой)."""
    await callback.answer()
    repo = SimpleWelcomeMessageRepository(db)
    msg = await repo.get_simple_welcome_message()
    if msg and msg.text:
        admin = callback.from_user
        entities = parse_entities_from_json(msg.entities_json) if msg.entities_json else None
        text_preview, ent = apply_welcome_placeholders(
            msg.text, admin.first_name or "", admin.full_name or "", admin.username or "", entities
        )
        await callback.message.answer("<b>Превью приветствия (анкета первой):</b>", disable_web_page_preview=True)
        if ent:
            await callback.message.answer(text_preview, entities=ent, parse_mode=None, disable_web_page_preview=True)
        else:
            await callback.message.answer(text_preview, disable_web_page_preview=True)
        await callback.message.answer("Кнопка под сообщением: «Заполнить анкету»", reply_markup=get_simple_welcome_manage_keyboard(), disable_web_page_preview=True)
    else:
        await callback.message.answer(
            "❌ Текст приветствия не задан.",
            reply_markup=get_simple_welcome_manage_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "admin_simple_welcome_edit")
async def admin_simple_welcome_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования приветствия (анкета первой)."""
    await callback.answer()
    await state.set_state(SimpleWelcomeMessageStates.text)
    await callback.message.edit_text(
        "✏️ <b>Приветствие (анкета первой)</b>\n\n"
        "Отправьте текст приветствия. Под ним будет кнопка «Заполнить анкету».\n\n"
        "Плейсхолдеры: <code>{first_name}</code>, <code>{full_name}</code>, <code>{username}</code>.",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(SimpleWelcomeMessageStates.text, F.text)
async def admin_simple_welcome_edit_text(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение текста приветствия (анкета первой)."""
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    text = (message.text or "").strip() or "Добро пожаловать!"
    entities = message.entities or []
    entities_json = None
    if entities:
        entities_list = [{"type": e.type, "offset": e.offset, "length": e.length, **({"url": e.url} if getattr(e, "url", None) else {})} for e in entities]
        entities_json = json.dumps(entities_list, ensure_ascii=False)
    repo = SimpleWelcomeMessageRepository(db)
    await repo.create_or_update(text, entities_json)
    await state.clear()
    await message.answer(
        "✅ Приветствие (анкета первой) сохранено. Под сообщением будет кнопка «Заполнить анкету».",
        reply_markup=get_admin_main_keyboard(),
        disable_web_page_preview=True
    )


# ========== Приветствие (режим «без анкеты») ==========

@router.callback_query(F.data == "admin_no_questionnaire_welcome")
async def admin_no_questionnaire_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню приветствия в режиме «без анкеты» (текст + кнопка «Получить ссылку»)."""
    await callback.answer()
    repo = NoQuestionnaireMessageRepository(db)
    msg = await repo.get_no_questionnaire_message()
    if msg and msg.text:
        preview = msg.text[:200] + "..." if len(msg.text) > 200 else msg.text
        text = "🚀 <b>Приветствие (без анкеты)</b>\n\nТекущий текст:\n\n" + preview
    else:
        text = (
            "🚀 <b>Приветствие (без анкеты)</b>\n\n"
            "Текст ещё не задан. Под ним будет кнопка «Получить ссылку».\n"
            "Нажмите «Редактировать текст»."
        )
    await callback.message.edit_text(
        text,
        reply_markup=get_no_questionnaire_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_no_questionnaire_view")
async def admin_no_questionnaire_view(callback: CallbackQuery, db: Database) -> None:
    """Просмотр приветствия в режиме «без анкеты»."""
    await callback.answer()
    repo = NoQuestionnaireMessageRepository(db)
    msg = await repo.get_no_questionnaire_message()
    if msg and msg.text:
        admin = callback.from_user
        entities = parse_entities_from_json(msg.entities_json) if msg.entities_json else None
        text_preview, ent = apply_welcome_placeholders(
            msg.text, admin.first_name or "", admin.full_name or "", admin.username or "", entities
        )
        await callback.message.answer("<b>Превью приветствия (без анкеты):</b>", disable_web_page_preview=True)
        if ent:
            await callback.message.answer(text_preview, entities=ent, parse_mode=None, disable_web_page_preview=True)
        else:
            await callback.message.answer(text_preview, disable_web_page_preview=True)
        await callback.message.answer(
            "Кнопка под сообщением: «Получить ссылку»",
            reply_markup=get_no_questionnaire_manage_keyboard(),
            disable_web_page_preview=True
        )
    else:
        await callback.message.answer(
            "❌ Текст приветствия не задан.",
            reply_markup=get_no_questionnaire_manage_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "admin_no_questionnaire_edit")
async def admin_no_questionnaire_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования приветствия (без анкеты)."""
    await callback.answer()
    await state.set_state(NoQuestionnaireMessageStates.text)
    await callback.message.edit_text(
        "✏️ <b>Приветствие (без анкеты)</b>\n\n"
        "Отправьте текст приветствия. Под ним будет кнопка «Получить ссылку».\n\n"
        "Плейсхолдеры: <code>{first_name}</code>, <code>{full_name}</code>, <code>{username}</code>.",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(NoQuestionnaireMessageStates.text, F.text)
async def admin_no_questionnaire_edit_text(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение текста приветствия (без анкеты)."""
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    text = (message.text or "").strip() or "Добро пожаловать!"
    entities = message.entities or []
    entities_json = None
    if entities:
        entities_list = [
            {
                "type": e.type,
                "offset": e.offset,
                "length": e.length,
                **({"url": e.url} if getattr(e, "url", None) else {}),
            }
            for e in entities
        ]
        entities_json = json.dumps(entities_list, ensure_ascii=False)
    repo = NoQuestionnaireMessageRepository(db)
    await repo.create_or_update(text, entities_json)
    await state.clear()
    await message.answer(
        "✅ Приветствие (без анкеты) сохранено. Под сообщением будет кнопка «Получить ссылку».",
        reply_markup=get_admin_main_keyboard(),
        disable_web_page_preview=True
    )


# ========== Сообщение со списком каналов ==========

@router.callback_query(F.data == "admin_channels_list")
async def admin_channels_list_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню сообщения со списком каналов (после анкеты в режиме «анкета первой»)."""
    await callback.answer()
    repo = ChannelsListMessageRepository(db)
    msg = await repo.get_channels_list_message()
    if msg and msg.text:
        preview = msg.text[:200] + "..." if len(msg.text) > 200 else msg.text
        text = "📢 <b>Сообщение со списком каналов</b>\n\nТекущий текст:\n\n" + preview
    else:
        text = (
            "📢 <b>Сообщение со списком каналов</b>\n\n"
            "Текст ещё не задан. Отправляется после анкеты в режиме «анкета первой»."
        )
    await callback.message.edit_text(
        text,
        reply_markup=get_channels_list_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_channels_list_view")
async def admin_channels_list_view(callback: CallbackQuery, db: Database) -> None:
    """Просмотр сообщения со списком каналов (с подставленным списком)."""
    await callback.answer()
    from bot.handlers.user_router import send_channels_list_message
    admin_id = callback.from_user.id
    sent = await send_channels_list_message(callback.bot, admin_id, db)
    if sent:
        await callback.message.answer("Превью отправлено вам выше.", reply_markup=get_channels_list_manage_keyboard(), disable_web_page_preview=True)
    else:
        await callback.message.answer("❌ Не удалось отправить превью.", reply_markup=get_channels_list_manage_keyboard(), disable_web_page_preview=True)


@router.callback_query(F.data == "admin_channels_list_edit")
async def admin_channels_list_edit_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Начало редактирования сообщения со списком каналов."""
    await callback.answer()
    await state.set_state(ChannelsListMessageStates.text)
    repo = ChannelsListMessageRepository(db)
    msg = await repo.get_channels_list_message()
    current = (msg.text or "") if msg else ""
    await callback.message.edit_text(
        "✏️ <b>Сообщение со списком каналов</b>\n\n"
        "Отправьте текст.\n\n"
        f"Текущий текст:\n{current[:300]}{'...' if len(current) > 300 else ''}",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(ChannelsListMessageStates.text, F.text)
async def admin_channels_list_edit_text(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение текста сообщения со списком каналов."""
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    text = (message.text or "").strip() or "Подпишитесь на наши каналы:\n\n{channels_list}"
    entities = message.entities or []
    entities_json = None
    if entities:
        entities_list = [{"type": e.type, "offset": e.offset, "length": e.length, **({"url": e.url} if getattr(e, "url", None) else {})} for e in entities]
        entities_json = json.dumps(entities_list, ensure_ascii=False)
    repo = ChannelsListMessageRepository(db)
    await repo.create_or_update(text, entities_json)
    await state.clear()
    await message.answer(
        "✅ Сообщение со списком каналов сохранено.",
        reply_markup=get_admin_main_keyboard(),
        disable_web_page_preview=True
    )


# ========== Управление сообщением после анкеты ==========

def _admin_preview_placeholders(callback: CallbackQuery) -> tuple[str, str, str]:
    """Данные администратора для подстановки в превью (как у приветственного сообщения)."""
    admin = callback.from_user
    if not admin:
        return "Имя", "Имя Фамилия", "username"
    first_name = admin.first_name or "Имя"
    full_name = (admin.full_name or first_name).strip()
    username = (admin.username or "").strip()
    return first_name, full_name, username


@router.callback_query(F.data == "admin_post_questionnaire")
async def admin_post_questionnaire_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню управления сообщением после анкеты."""
    await callback.answer()
    post_questionnaire_repo = PostQuestionnaireMessageRepository(db)
    msg = await post_questionnaire_repo.get_latest_post_questionnaire_message()
    if msg:
        status_suffix = " (неактивно)" if not msg.is_active else ""
        raw = msg.text or "Без текста"
        first_name, full_name, username = _admin_preview_placeholders(callback)
        preview_text, _ = apply_welcome_placeholders(raw, first_name, full_name, username, None)
        text_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text
        text = (
            "📋 <b>Сообщение после анкеты</b>\n\n"
            f"Текущее сообщение{status_suffix}:\n\n{text_preview}\n\n"
            "💡 В превью подставлены ваши данные (как у приветственного сообщения)."
        )
    else:
        text = (
            "📋 <b>Сообщение после анкеты</b>\n\n"
            "Сообщение после анкеты еще не создано.\n"
            "Нажмите 'Редактировать' или 'Переслать сообщение' для создания.\n\n"
            "💡 Это сообщение отправляется пользователю сразу после заполнения анкеты."
        )
    await callback.message.edit_text(
        text,
        reply_markup=get_post_questionnaire_manage_keyboard(
            has_message=msg is not None,
            is_active=msg.is_active if msg else True
        ),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_post_questionnaire_toggle")
async def admin_post_questionnaire_toggle(callback: CallbackQuery, db: Database) -> None:
    """Переключение статуса сообщения после анкеты (активно/неактивно)."""
    post_questionnaire_repo = PostQuestionnaireMessageRepository(db)
    latest = await post_questionnaire_repo.get_latest_post_questionnaire_message()
    if not latest or latest.id is None:
        await callback.answer("Нет сообщения для переключения.", show_alert=True)
        return
    await callback.answer()
    new_active = not latest.is_active
    await     post_questionnaire_repo.toggle_post_questionnaire_status(latest.id, new_active)
    status_suffix = " (неактивно)" if not new_active else ""
    raw = latest.text or "Без текста"
    first_name, full_name, username = _admin_preview_placeholders(callback)
    preview_text, _ = apply_welcome_placeholders(raw, first_name, full_name, username, None)
    text_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text
    text = (
        "📋 <b>Сообщение после анкеты</b>\n\n"
        f"Текущее сообщение{status_suffix}:\n\n{text_preview}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_post_questionnaire_manage_keyboard(has_message=True, is_active=new_active),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_post_questionnaire_view")
async def admin_post_questionnaire_view(callback: CallbackQuery, db: Database) -> None:
    """Просмотр сообщения после анкеты (плейсхолдеры подставлены как в превью)."""
    await callback.answer()
    post_questionnaire_repo = PostQuestionnaireMessageRepository(db)
    msg = await post_questionnaire_repo.get_latest_post_questionnaire_message()
    if not msg:
        await callback.message.answer(
            "❌ Сообщение после анкеты еще не создано.",
            reply_markup=get_post_questionnaire_manage_keyboard(has_message=False),
            disable_web_page_preview=True
        )
        return

    entities = parse_entities_from_json(msg.entities_json)
    first_name, full_name, username = _admin_preview_placeholders(callback)
    preview_text, preview_entities = apply_welcome_placeholders(
        msg.text or "", first_name, full_name, username, entities
    )
    reply_markup = None
    if msg.buttons_json:
        try:
            buttons_data = json.loads(msg.buttons_json)
            keyboard_buttons = []
            for row in buttons_data:
                row_buttons = []
                for button in row:
                    if button.get("url"):
                        row_buttons.append(InlineKeyboardButton(text=button["text"], url=button["url"]))
                if row_buttons:
                    keyboard_buttons.append(row_buttons)
            if keyboard_buttons:
                reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        except Exception as e:
            logger.error(f"Ошибка парсинга кнопок: {e}")

    # Заголовок отдельно: иначе caption/текст длиннее префикса, а entities считаются от сырого текста БД — смещение форматирования.
    await callback.message.answer(
        "<b>Текущее сообщение после анкеты:</b>",
        disable_web_page_preview=True,
    )

    if msg.media_type == "photo" and msg.media_file_id:
        await callback.message.answer_photo(
            photo=msg.media_file_id,
            caption=preview_text or "",
            caption_entities=preview_entities if preview_entities else None,
            parse_mode=None if preview_entities else ParseMode.HTML,
            reply_markup=reply_markup,
        )
    elif msg.media_type == "video" and msg.media_file_id:
        await callback.message.answer_video(
            video=msg.media_file_id,
            caption=preview_text or "",
            caption_entities=preview_entities if preview_entities else None,
            parse_mode=None if preview_entities else ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    else:
        if preview_entities:
            await callback.message.answer(
                preview_text or "Без текста",
                entities=preview_entities,
                parse_mode=None,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        else:
            await callback.message.answer(
                preview_text or "Без текста",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
    
    await callback.message.answer(
        "Меню:",
        reply_markup=get_post_questionnaire_manage_keyboard(
            has_message=True,
            is_active=msg.is_active
        ),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_post_questionnaire_edit")
async def admin_post_questionnaire_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования сообщения после анкеты."""
    await callback.answer()
    await state.set_state(PostQuestionnaireMessageStates.text)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование сообщения после анкеты</b>\n\n"
        "Отправьте новое сообщение (текст, медиа и/или кнопки).\n\n"
        "Для подстановки имени пользователя используйте плейсхолдеры:\n"
        "• <code>{first_name}</code> — имя\n"
        "• <code>{full_name}</code> — полное имя\n"
        "• <code>{username}</code> — username (без @)\n\n"
        "Пример: «Здравствуйте, {first_name}! Спасибо за отклик!»\n\n"
        "💡 Это сообщение отправляется пользователю сразу после заполнения анкеты.\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_post_questionnaire_forward")
async def admin_post_questionnaire_forward_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало создания сообщения после анкеты через пересылку."""
    await callback.answer()
    await state.set_state("admin_post_questionnaire_forward")
    
    await callback.message.edit_text(
        "📤 <b>Создание сообщения после анкеты через пересылку</b>\n\n"
        "Перешлите сообщение, которое хотите использовать как 'Сообщение после анкеты'.\n\n"
        "Для подстановки имени пользователя используйте плейсхолдеры:\n"
        "• <code>{first_name}</code> — имя\n"
        "• <code>{full_name}</code> — полное имя\n"
        "• <code>{username}</code> — username (без @)\n\n"
        "Пример: «Здравствуйте, {first_name}! Спасибо за отклик!»\n\n"
        "💡 Это сообщение будет отправляться пользователям сразу после заполнения анкеты.\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(PostQuestionnaireMessageStates.text)
async def admin_post_questionnaire_edit_text(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение текста сообщения после анкеты."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    text = message.text or message.caption or ""
    entities_json = None
    entities = message.entities or message.caption_entities or []
    if entities:
        entities_list = []
        for entity in entities:
            entity_dict = {"type": entity.type, "offset": entity.offset, "length": entity.length}
            if entity.type == "text_link":
                entity_dict["url"] = entity.url
            entities_list.append(entity_dict)
        entities_json = json.dumps(entities_list, ensure_ascii=False)
    
    media_type = None
    media_file_id = None
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    await state.update_data(
        text=text,
        entities_json=entities_json,
        media_type=media_type,
        media_file_id=media_file_id
    )
    
    await state.set_state(PostQuestionnaireMessageStates.media)
    
    if media_type:
        await message.answer(
            "✅ Текст и медиа сохранены.\n\nОтправьте дополнительное медиа или /skip.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
    else:
        await message.answer(
            "✅ Текст сохранен.\n\nОтправьте фото/видео или /skip.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


@router.message(PostQuestionnaireMessageStates.media)
async def admin_post_questionnaire_edit_media(message: Message, state: FSMContext, db: Database) -> None:
    """Обработка медиа для сообщения после анкеты."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    if message.text and message.text.lower() in ["/skip", "пропустить", "skip"]:
        await state.set_state(PostQuestionnaireMessageStates.waiting_for_buttons)
        await message.answer(
            "✅ Шаг пропущен.\n\nОтправьте кнопки в формате: <code>Текст:ссылка;Текст2:ссылка2</code> или /skip.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    media_type = None
    media_file_id = None
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    if media_type:
        await state.update_data(media_type=media_type, media_file_id=media_file_id)
        if message.caption:
            entities = message.caption_entities or []
            entities_list = []
            for entity in entities:
                entity_dict = {"type": entity.type, "offset": entity.offset, "length": entity.length}
                if entity.type == "text_link":
                    entity_dict["url"] = entity.url
                entities_list.append(entity_dict)
            await state.update_data(text=message.caption, entities_json=json.dumps(entities_list, ensure_ascii=False))
        
        await state.set_state(PostQuestionnaireMessageStates.waiting_for_buttons)
        await message.answer(
            "✅ Медиа сохранено.\n\nОтправьте кнопки в формате: <code>Текст:ссылка</code> или /skip.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
    else:
        await message.answer("❌ Отправьте фото/видео или /skip.", reply_markup=get_back_keyboard(), disable_web_page_preview=True)


@router.message(PostQuestionnaireMessageStates.waiting_for_buttons)
async def admin_post_questionnaire_edit_buttons(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение кнопок и сообщения после анкеты."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    buttons_json = None
    if message.text and message.text.lower() not in ["/skip", "пропустить", "skip"]:
        try:
            parts = [p.strip() for p in message.text.split(";")]
            buttons_list = []
            for part in parts:
                if ":" in part:
                    text_btn, url = part.split(":", 1)
                    text_btn, url = text_btn.strip(), url.strip()
                    if text_btn and url:
                        buttons_list.append([{"text": text_btn, "url": url}])
            if buttons_list:
                buttons_json = json.dumps(buttons_list, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка парсинга кнопок: {e}")
            await message.answer("❌ Неверный формат. Пример: Текст:ссылка;Текст2:ссылка2 или /skip.", reply_markup=get_back_keyboard(), disable_web_page_preview=True)
            return
    
    data = await state.get_data()
    if not data.get("text") and not data.get("media_type"):
        await message.answer("❌ Сообщение должно содержать текст или медиа. Начните заново.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        await state.clear()
        return
    
    post_questionnaire_repo = PostQuestionnaireMessageRepository(db)
    await post_questionnaire_repo.create_or_update_post_questionnaire_message(
        text=data.get("text"),
        entities_json=data.get("entities_json"),
        media_type=data.get("media_type"),
        media_file_id=data.get("media_file_id"),
        buttons_json=buttons_json
    )
    
    await state.clear()
    await message.answer(
        "✅ Сообщение после анкеты успешно сохранено!\n\n"
        "💡 Оно будет отправляться пользователям сразу после заполнения анкеты.",
        reply_markup=get_admin_main_keyboard(),
        disable_web_page_preview=True
    )
    logger.info(f"Админ {message.from_user.id} обновил сообщение после анкеты")


# ========== Управление цепочкой сообщений ==========

@router.callback_query(F.data == "admin_chain")
async def admin_chain_messages_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню управления цепочкой сообщений."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    chain_is_active = await chain_repo.get_chain_is_active()
    chain_messages = await chain_repo.get_all_chain_messages()
    chain_status = "активна" if chain_is_active else "неактивна"
    text = f"🔗 <b>Цепочка сообщений</b> ({chain_status})\n\n"
    text += "После отправки «Сообщения после анкеты» пользователи получают цепочку сообщений.\n\n"
    if chain_messages:
        text += "<b>Текущая цепочка:</b>\n"
        for msg in chain_messages:
            status = "✅" if msg.is_active else "❌"
            preview = msg.text[:50] + "..." if msg.text and len(msg.text) > 50 else (msg.text or "Без текста")
            text += f"{status} Сообщение {msg.message_number}: через {msg.delay_minutes} мин.\n"
            text += f"   {preview}\n\n"
    else:
        text += "Цепочка сообщений еще не настроена.\n"
    await callback.message.edit_text(
        text,
        reply_markup=get_chain_messages_manage_keyboard(chain_is_active=chain_is_active),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_chain_toggle")
async def admin_chain_toggle(callback: CallbackQuery, db: Database) -> None:
    """Переключение статуса цепочки целиком (активна/неактивна)."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    current = await chain_repo.get_chain_is_active()
    await chain_repo.set_chain_is_active(not current)
    chain_messages = await chain_repo.get_all_chain_messages()
    chain_status = "активна" if not current else "неактивна"
    text = f"🔗 <b>Цепочка сообщений</b> ({chain_status})\n\n"
    text += "После отправки «Сообщения после анкеты» пользователи получают цепочку сообщений.\n\n"
    if chain_messages:
        text += "<b>Текущая цепочка:</b>\n"
        for msg in chain_messages:
            status = "✅" if msg.is_active else "❌"
            preview = msg.text[:50] + "..." if msg.text and len(msg.text) > 50 else (msg.text or "Без текста")
            text += f"{status} Сообщение {msg.message_number}: через {msg.delay_minutes} мин.\n"
            text += f"   {preview}\n\n"
    else:
        text += "Цепочка сообщений еще не настроена.\n"
    await callback.message.edit_text(
        text,
        reply_markup=get_chain_messages_manage_keyboard(chain_is_active=not current),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_chain_preview")
async def admin_chain_preview(callback: CallbackQuery, db: Database) -> None:
    """Предпросмотр цепочки: отправка всех активных сообщений админу без интервалов."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    chain_is_active = await chain_repo.get_chain_is_active()
    chain_messages = await chain_repo.get_active_chain_messages()
    back_kb = get_chain_messages_manage_keyboard(chain_is_active=chain_is_active)
    if not chain_messages:
        await callback.message.answer(
            "❌ Нет активных сообщений в цепочке. Добавьте сообщения и включите их в списке.",
            reply_markup=back_kb,
            disable_web_page_preview=True
        )
        return
    admin_id = callback.from_user.id if callback.from_user else 0
    bot = callback.bot
    sent = 0
    for msg in sorted(chain_messages, key=lambda x: x.message_number):
        ok = await send_chain_message(bot, admin_id, db, msg)
        if ok:
            sent += 1
    await callback.message.answer(
        f"✅ Просмотр цепочки завершён. Вам отправлено сообщений: {sent} из {len(chain_messages)}.",
        reply_markup=back_kb,
        disable_web_page_preview=True
    )


def _build_chain_list_text(
    chain_messages: list,
    callback: Optional[CallbackQuery] = None,
) -> str:
    """Текст списка сообщений цепочки. Если передан callback, в превью подставляются данные админа."""
    text = "📋 <b>Список сообщений цепочки</b>\n\nНажмите на сообщение, чтобы переключить его статус (активно/неактивно).\n\n"
    first_name, full_name, username = _admin_preview_placeholders(callback) if callback else ("Имя", "Имя Фамилия", "username")
    for msg in chain_messages:
        status = "✅ Активно" if msg.is_active else "❌ Неактивно"
        text += f"<b>Сообщение {msg.message_number}</b> — {status}\n"
        text += f"⏱ Интервал: {msg.delay_minutes} мин. "
        if msg.text:
            preview_raw = msg.text[:80] + "..." if len(msg.text) > 80 else msg.text
            if callback:
                preview, _ = apply_welcome_placeholders(msg.text or "", first_name, full_name, username, None)
                preview = preview[:80] + "..." if len(preview) > 80 else preview
            else:
                preview = preview_raw
            text += f"📝 {preview}\n"
        else:
            text += "\n"
    return text


@router.callback_query(F.data == "admin_chain_list")
async def admin_chain_list(callback: CallbackQuery, db: Database) -> None:
    """Просмотр списка сообщений цепочки с переключением статуса каждого."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    chain_messages = await chain_repo.get_all_chain_messages()
    chain_is_active = await chain_repo.get_chain_is_active()
    if not chain_messages:
        await callback.message.answer(
            "❌ Цепочка сообщений еще не настроена.",
            reply_markup=get_chain_messages_manage_keyboard(chain_is_active=chain_is_active),
            disable_web_page_preview=True
        )
        return
    text = _build_chain_list_text(chain_messages, callback)
    items = [(m.message_number, m.is_active) for m in chain_messages]
    await callback.message.answer(
        text,
        reply_markup=get_chain_list_keyboard(items, chain_is_active),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("admin_chain_toggle_msg_"))
async def admin_chain_toggle_msg(callback: CallbackQuery, db: Database) -> None:
    """Переключение статуса одного сообщения цепочки (активно/неактивно)."""
    await callback.answer()
    try:
        num = int(callback.data.replace("admin_chain_toggle_msg_", ""))
    except ValueError:
        return
    chain_repo = ChainMessageRepository(db)
    msg = await chain_repo.get_chain_message(num)
    if not msg:
        return
    await chain_repo.toggle_chain_message_status(num, not msg.is_active)
    chain_messages = await chain_repo.get_all_chain_messages()
    chain_is_active = await chain_repo.get_chain_is_active()
    text = _build_chain_list_text(chain_messages, callback)
    items = [(m.message_number, m.is_active) for m in chain_messages]
    await callback.message.edit_text(
        text,
        reply_markup=get_chain_list_keyboard(items, chain_is_active),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_chain_edit")
async def admin_chain_edit_select(callback: CallbackQuery, db: Database) -> None:
    """Выбор сообщения для редактирования."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    chain_messages = await chain_repo.get_all_chain_messages()
    text = "✏️ <b>Редактирование сообщения цепочки</b>\n\n"
    if chain_messages:
        text += "Выберите сообщение для редактирования:"
    else:
        text += "Сообщений пока нет. Нажмите «Добавить сообщение»."
    await callback.message.edit_text(
        text,
        reply_markup=get_chain_message_select_keyboard(chain_messages),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_chain_forward")
async def admin_chain_forward_select(callback: CallbackQuery, db: Database) -> None:
    """Выбор сообщения для создания через пересылку."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    chain_messages = await chain_repo.get_all_chain_messages()
    text = "📤 <b>Создание сообщения цепочки через пересылку</b>\n\n"
    if chain_messages:
        text += "Выберите сообщение для замены или добавьте новое:"
    else:
        text += "Сообщений пока нет. Нажмите «Добавить сообщение»."
    await callback.message.edit_text(
        text,
        reply_markup=get_chain_message_forward_select_keyboard(chain_messages),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_chain_add")
async def admin_chain_add(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Добавление нового сообщения в конец цепочки."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    message_number = await chain_repo.get_next_message_number()
    await state.update_data(chain_message_number=message_number)
    await state.set_state(ChainMessageStates.text)
    await callback.message.edit_text(
        f"➕ <b>Добавление сообщения {message_number}</b>\n\n"
        "Отправьте текст нового сообщения.\n\n"
        "Для подстановки имени пользователя используйте плейсхолдеры:\n"
        "• <code>{first_name}</code> — имя\n"
        "• <code>{full_name}</code> — полное имя\n"
        "• <code>{username}</code> — username (без @)\n\n"
        "Пример: «Здравствуйте, {first_name}! Спасибо за отклик!»\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_chain_add_forward")
async def admin_chain_add_forward(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Добавление нового сообщения через пересылку."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    message_number = await chain_repo.get_next_message_number()
    await state.update_data(chain_message_number=message_number)
    await state.set_state("admin_chain_forward")
    await callback.message.edit_text(
        f"📤 <b>Добавление сообщения {message_number} через пересылку</b>\n\n"
        f"Перешлите сообщение, которое хотите использовать как сообщение {message_number} цепочки.\n\n"
        "Для подстановки имени пользователя используйте плейсхолдеры:\n"
        "• <code>{first_name}</code> — имя\n"
        "• <code>{full_name}</code> — полное имя\n"
        "• <code>{username}</code> — username (без @)\n\n"
        "💡 После пересылки нужно будет указать интервал времени (в минутах).\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_chain_delete")
async def admin_chain_delete_select(callback: CallbackQuery, db: Database) -> None:
    """Выбор сообщения для удаления."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    chain_messages = await chain_repo.get_all_chain_messages()
    if not chain_messages:
        chain_is_active = await chain_repo.get_chain_is_active()
        await callback.message.edit_text(
            "❌ Нет сообщений для удаления.",
            reply_markup=get_chain_messages_manage_keyboard(chain_is_active=chain_is_active),
            disable_web_page_preview=True
        )
        return
    await callback.message.edit_text(
        "🗑 <b>Удаление сообщения из цепочки</b>\n\n"
        "Выберите сообщение. После удаления оставшиеся сообщения будут перенумерованы.",
        reply_markup=get_chain_delete_keyboard(chain_messages),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("admin_chain_delete_"))
async def admin_chain_delete_confirm(callback: CallbackQuery, db: Database) -> None:
    """Удаление сообщения с перенумерацией."""
    await callback.answer()
    try:
        message_number = int(callback.data.replace("admin_chain_delete_", ""))
    except ValueError:
        await callback.message.answer("❌ Ошибка: неверный номер сообщения.", disable_web_page_preview=True)
        return
    chain_repo = ChainMessageRepository(db)
    deleted = await chain_repo.delete_chain_message(message_number)
    chain_is_active = await chain_repo.get_chain_is_active()
    chain_messages = await chain_repo.get_all_chain_messages()
    if not deleted:
        await callback.message.edit_text(
            "❌ Сообщение не найдено.",
            reply_markup=get_chain_messages_manage_keyboard(chain_is_active=chain_is_active),
            disable_web_page_preview=True
        )
        return
    text = f"✅ Сообщение {message_number} удалено."
    if chain_messages:
        text += f"\n\nВ цепочке осталось сообщений: {len(chain_messages)}."
    else:
        text += "\n\n⚠️ Цепочка пуста. Добавьте сообщения перед отправкой пользователям."
    await callback.message.edit_text(
        text,
        reply_markup=get_chain_messages_manage_keyboard(chain_is_active=chain_is_active),
        disable_web_page_preview=True
    )
    logger.info(f"Админ {callback.from_user.id} удалил сообщение {message_number} из цепочки")


@router.callback_query(F.data.startswith("admin_chain_forward_"))
async def admin_chain_forward_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Начало создания сообщения цепочки через пересылку."""
    await callback.answer()
    
    try:
        message_number = int(callback.data.split("_")[-1])
        
        # Сохраняем номер сообщения в состоянии
        await state.update_data(chain_message_number=message_number)
        await state.set_state("admin_chain_forward")
        
        chain_repo = ChainMessageRepository(db)
        existing_msg = await chain_repo.get_chain_message(message_number)
        
        if existing_msg:
            delay_info = f"\nТекущий интервал: {existing_msg.delay_minutes} минут"
        else:
            delay_info = ""
        
        await callback.message.edit_text(
            f"📤 <b>Создание сообщения {message_number} цепочки через пересылку</b>\n\n"
            f"Перешлите сообщение, которое хотите использовать как сообщение {message_number} цепочки.\n\n"
            "Для подстановки имени пользователя используйте плейсхолдеры:\n"
            "• <code>{first_name}</code> — имя\n"
            "• <code>{full_name}</code> — полное имя\n"
            "• <code>{username}</code> — username (без @)\n\n"
            "Пример: «Здравствуйте, {first_name}! Спасибо за отклик!»\n\n"
            f"💡 После пересылки вам нужно будет указать интервал времени (в минутах).{delay_info}\n\n"
            f"Для отмены отправьте /cancel",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
    except ValueError:
        await callback.message.answer("❌ Ошибка: неверный номер сообщения.", disable_web_page_preview=True)


@router.callback_query(F.data.startswith("admin_chain_edit_"))
async def admin_chain_edit_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Начало редактирования сообщения цепочки."""
    await callback.answer()
    
    try:
        message_number = int(callback.data.split("_")[-1])
        
        chain_repo = ChainMessageRepository(db)
        existing_msg = await chain_repo.get_chain_message(message_number)
        if not existing_msg:
            await callback.message.answer("❌ Сообщение не найдено.", disable_web_page_preview=True)
            return
        
        # Сохраняем номер сообщения в состоянии
        await state.update_data(chain_message_number=message_number)
        await state.set_state(ChainMessageStates.text)
        
        # Показываем текущее сообщение (заголовок отдельно — не увеличивает caption)
        if existing_msg:
            entities = parse_entities_from_json(existing_msg.entities_json)
            first_name, full_name, username = _admin_preview_placeholders(callback)
            preview_text, preview_entities = apply_welcome_placeholders(
                existing_msg.text or "", first_name, full_name, username, entities
            )

            reply_markup = None
            if existing_msg.buttons_json:
                try:
                    buttons_data = json.loads(existing_msg.buttons_json)
                    keyboard_buttons = []
                    for row in buttons_data:
                        row_buttons = []
                        for button in row:
                            raw_url = button.get("url")
                            if raw_url:
                                resolved_url = resolve_button_url(
                                    raw_url, first_name, full_name, username
                                )
                                if resolved_url:
                                    row_buttons.append(InlineKeyboardButton(
                                        text=button["text"], url=resolved_url
                                    ))
                        if row_buttons:
                            keyboard_buttons.append(row_buttons)
                    if keyboard_buttons:
                        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                except Exception as e:
                    logger.error(f"Ошибка парсинга кнопок: {e}")

            await callback.message.answer(
                f"<b>Текущее сообщение {message_number} цепочки:</b>",
                disable_web_page_preview=True,
            )
            try:
                await _send_media_with_text(
                    callback.bot,
                    callback.message.chat.id,
                    media_type=existing_msg.media_type,
                    media_file_id=existing_msg.media_file_id,
                    text=preview_text,
                    entities=preview_entities,
                    reply_markup=reply_markup,
                    default_text="Без текста",
                    disable_link_preview=True,
                )
            except TelegramBadRequest as e:
                err = str(e).lower()
                if "wrong file identifier" in err:
                    logger.warning(
                        f"Невалидный media_file_id для сообщения {message_number} цепочки, "
                        "отправляем текст без медиа"
                    )
                    if preview_entities:
                        await callback.message.answer(
                            preview_text or "Без текста",
                            entities=preview_entities,
                            parse_mode=None,
                            reply_markup=reply_markup,
                            disable_web_page_preview=True,
                        )
                    else:
                        await callback.message.answer(
                            preview_text or "Без текста",
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            disable_web_page_preview=True,
                        )
                    await callback.message.answer(
                        "⚠️ Медиа недоступно (устаревший file_id). Перезагрузите медиа.",
                        disable_web_page_preview=True,
                    )
                else:
                    raise

            delay_info = f"\nТекущий интервал: {existing_msg.delay_minutes} минут"
        else:
            delay_info = ""
        
        # Отправляем инструкцию по редактированию
        await callback.message.answer(
            f"✏️ <b>Редактирование сообщения {message_number}</b>\n\n"
            "Отправьте новый текст сообщения.\n\n"
            "Для подстановки имени пользователя используйте плейсхолдеры:\n"
            "• <code>{first_name}</code> — имя\n"
            "• <code>{full_name}</code> — полное имя\n"
            "• <code>{username}</code> — username (без @)\n\n"
            "Пример: «Здравствуйте, {first_name}! Спасибо за отклик!»\n\n"
            f"{delay_info}\n\n"
            f"Для отмены отправьте /cancel",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
    except ValueError:
        await callback.message.answer("❌ Ошибка: неверный номер сообщения.", disable_web_page_preview=True)
    except Exception as e:
        logger.error(
            f"Ошибка при начале редактирования сообщения цепочки: {e}",
            exc_info=True,
        )
        await callback.message.answer(
            "⚠️ Не удалось показать превью сообщения.\n\n"
            "Отправьте новый текст сообщения или /cancel для выхода.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True,
        )


@router.message(ChainMessageStates.text)
async def admin_chain_edit_text(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение текста сообщения цепочки."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    text = message.text or message.caption or ""
    entities_json = None
    
    # Получаем entities
    entities = message.entities or message.caption_entities or []
    if entities:
        entities_list = []
        for entity in entities:
            entity_dict = {
                "type": entity.type,
                "offset": entity.offset,
                "length": entity.length
            }
            if entity.type == "text_link":
                entity_dict["url"] = entity.url
            entities_list.append(entity_dict)
        entities_json = json.dumps(entities_list, ensure_ascii=False)
    
    # Проверяем медиа
    media_type = None
    media_file_id = None
    
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    # Сохраняем в состояние
    await state.update_data(
        text=text,
        entities_json=entities_json,
        media_type=media_type,
        media_file_id=media_file_id
    )
    
    await state.set_state(ChainMessageStates.media)
    
    if media_type:
        await message.answer(
            f"✅ Текст и медиа сохранены.\n\n"
            f"Если хотите добавить еще медиа, отправьте фото или видео.\n"
            f"Или отправьте /skip чтобы перейти к кнопкам.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
    else:
        await message.answer(
            f"✅ Текст сохранен.\n\n"
            f"Отправьте фото или видео (опционально), или отправьте /skip для перехода к кнопкам.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


@router.message(ChainMessageStates.media)
async def admin_chain_edit_media(message: Message, state: FSMContext, db: Database) -> None:
    """Обработка медиа для сообщения цепочки."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    if message.text and message.text.lower() in ["/skip", "пропустить", "skip"]:
        await state.set_state(ChainMessageStates.waiting_for_buttons)
        data = await state.get_data()
        message_number = data.get("chain_message_number")
        
        await message.answer(
            f"✅ Медиа пропущено.\n\n"
            f"Отправьте кнопки в формате:\n"
            f"<code>Текст кнопки1:ссылка1;Текст кнопки2:ссылка2</code>\n\n"
            f"Или отправьте /skip чтобы перейти к настройке интервала.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    else:
        await message.answer("❌ Отправьте фото или видео, либо /skip для пропуска.", disable_web_page_preview=True)
        return
    
    await state.update_data(media_type=media_type, media_file_id=media_file_id)
    
    if message.caption:
        entities_json = None
        entities = message.caption_entities or []
        if entities:
            entities_list = []
            for entity in entities:
                entity_dict = {
                    "type": entity.type,
                    "offset": entity.offset,
                    "length": entity.length
                }
                if entity.type == "text_link":
                    entity_dict["url"] = entity.url
                entities_list.append(entity_dict)
            entities_json = json.dumps(entities_list, ensure_ascii=False)
        await state.update_data(text=message.caption, entities_json=entities_json)
    
    await state.set_state(ChainMessageStates.waiting_for_buttons)
    await message.answer(
        f"✅ Медиа сохранено ({media_type}).\n\n"
        f"Отправьте кнопки в формате:\n"
        f"<code>Текст кнопки1:ссылка1;Текст кнопки2:ссылка2</code>\n\n"
        f"Или отправьте /skip чтобы перейти к настройке интервала.",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(ChainMessageStates.waiting_for_buttons)
async def admin_chain_edit_buttons(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение кнопок и переход к настройке интервала."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    buttons_json = None
    
    if message.text and message.text.lower() in ["/skip", "пропустить", "skip"]:
        buttons_json = None
    elif message.text and ":" in message.text:
        try:
            buttons_list = []
            button_strings = message.text.split(";")
            
            for button_str in button_strings:
                button_str = button_str.strip()
                if not button_str:
                    continue
                
                if ":" in button_str:
                    parts = button_str.split(":", 1)
                    button_text = parts[0].strip()
                    button_url = parts[1].strip() if len(parts) > 1 else None
                    
                    if button_text and button_url:
                        button_url = button_url.strip()
                        # Поддерживаем короткий формат @username — оставляем как есть,
                        # дальнейшую нормализацию сделает resolve_button_url при отправке.
                        if not button_url.startswith("@"):
                            if not (button_url.startswith("http://") or 
                                   button_url.startswith("https://") or 
                                   button_url.startswith("tg://") or
                                   button_url.startswith("t.me/")):
                                if button_url.startswith("t.me/"):
                                    button_url = "https://" + button_url
                                elif not button_url.startswith("http"):
                                    button_url = "https://" + button_url
                        
                        buttons_list.append([{
                            "text": button_text,
                            "url": button_url,
                            "callback_data": None
                        }])
            
            if buttons_list:
                buttons_json = json.dumps(buttons_list, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка парсинга кнопок: {e}")
            await message.answer(
                f"❌ Ошибка при парсинге кнопок: {e}\n\n"
                "Отправьте /skip чтобы пропустить.",
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
            return
    
    await state.update_data(buttons_json=buttons_json)
    await state.set_state(ChainMessageStates.delay_minutes)
    
    data = await state.get_data()
    message_number = data.get("chain_message_number")
    chain_repo = ChainMessageRepository(db)
    existing_msg = await chain_repo.get_chain_message(message_number)
    current_delay = ChainMessageRepository.get_default_delay(message_number, existing_msg)
    
    # Формируем подсказку в зависимости от номера сообщения
    if message_number == 1:
        hint_text = (
            f"📌 <b>Важно:</b> Для первого сообщения интервал считается от 'Сообщения после анкеты'.\n"
            f"⚠️ Если установить 0 минут, сообщение отправится сразу после 'Сообщения после анкеты'.\n\n"
        )
    else:
        hint_text = (
            f"📌 <b>Важно:</b> Интервал считается от предыдущего сообщения цепочки.\n"
            f"⚠️ Если установить 0 минут, сообщение отправится сразу после предыдущего.\n\n"
        )
    
    await message.answer(
        f"✅ Кнопки {'сохранены' if buttons_json else 'пропущены'}.\n\n"
        f"<b>Настройка интервала времени</b>\n\n"
        f"{hint_text}"
        f"Отправьте количество минут задержки.\n"
        f"Текущее значение: <b>{current_delay} минут</b>\n\n"
        f"<i>Пример: если указать 30 минут, сообщение отправится через 30 минут после предыдущего.</i>\n\n"
        f"Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


@router.message(ChainMessageStates.delay_minutes)
async def admin_chain_edit_delay(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение интервала времени и завершение редактирования."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    try:
        delay_minutes = int(message.text)
        if delay_minutes < 0:
            await message.answer("❌ Интервал не может быть отрицательным. Введите число от 0 и выше.", disable_web_page_preview=True)
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (количество минут).", disable_web_page_preview=True)
        return
    
    data = await state.get_data()
    message_number = data.get("chain_message_number")
    
    if not message_number:
        await message.answer("❌ Ошибка: номер сообщения не найден.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        await state.clear()
        return
    
    # Проверяем, было ли показано предупреждение (для первого сообщения с delay=0)
    delay_warning_shown = data.get("delay_warning_shown", False)
    
    # Валидация для первого сообщения: предупреждение если delay_minutes = 0
    if message_number == 1 and delay_minutes == 0 and not delay_warning_shown:
        warning_text = (
            "⚠️ <b>Внимание!</b> Вы установили интервал 0 минут для первого сообщения.\n\n"
            "Это означает, что сообщение отправится <b>сразу</b> после 'Сообщения после анкеты'.\n\n"
            "Рекомендуется установить интервал хотя бы 1-5 минут для лучшего пользовательского опыта.\n\n"
            "Вы уверены? Отправьте <b>0</b> еще раз для подтверждения или любое другое число для изменения.\n"
            "Для отмены отправьте /cancel"
        )
        await message.answer(warning_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        # Сохраняем флаг предупреждения в состоянии
        await state.update_data(delay_warning_shown=True)
        return
    
    # Если предупреждение было показано и пользователь снова ввел 0 - подтверждаем
    # Если ввел другое число - используем его (сбрасываем флаг)
    if delay_warning_shown:
        await state.update_data(delay_warning_shown=False)
    
    # Сохранение в БД
    chain_repo = ChainMessageRepository(db)
    await chain_repo.create_or_update_chain_message(
        message_number=message_number,
        text=data.get("text", ""),
        delay_minutes=delay_minutes,
        entities_json=data.get("entities_json"),
        media_type=data.get("media_type"),
        media_file_id=data.get("media_file_id"),
        buttons_json=data.get("buttons_json"),
        is_active=True
    )
    
    await state.clear()
    
    # Формируем сообщение о сохранении с дополнительной информацией
    if message_number == 1:
        if delay_minutes == 0:
            save_message = (
                f"✅ Сообщение {message_number} цепочки успешно сохранено!\n\n"
                f"⏱ Интервал: <b>{delay_minutes} минут</b>\n\n"
                f"⚠️ <i>Сообщение отправится сразу после 'Сообщения после анкеты'</i>"
            )
        else:
            save_message = (
                f"✅ Сообщение {message_number} цепочки успешно сохранено!\n\n"
                f"⏱ Интервал: <b>{delay_minutes} минут</b>\n\n"
                f"📌 <i>Сообщение отправится через {delay_minutes} минут после 'Сообщения после анкеты'</i>"
            )
    else:
        save_message = (
            f"✅ Сообщение {message_number} цепочки успешно сохранено!\n\n"
            f"⏱ Интервал: <b>{delay_minutes} минут</b>\n\n"
            f"📌 <i>Сообщение отправится через {delay_minutes} минут после предыдущего сообщения цепочки</i>"
        )
    
    await message.answer(
        save_message,
        reply_markup=get_admin_main_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    
    logger.info(f"Админ {message.from_user.id} обновил сообщение {message_number} цепочки")


@router.callback_query(F.data == "admin_chain_intervals")
async def admin_chain_intervals_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню настройки интервалов цепочки сообщений (только интервалы, без редактирования сообщений)."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    chain_messages = await chain_repo.get_all_chain_messages()
    text = "⚙️ <b>Настройка интервалов цепочки сообщений</b>\n\n"
    text += "Текущие интервалы. Нажмите на сообщение, чтобы изменить только его интервал:\n\n"
    for msg in sorted(chain_messages, key=lambda x: x.message_number):
        text += f"Сообщение {msg.message_number}: {msg.delay_minutes} мин.\n"
    await callback.message.edit_text(
        text,
        reply_markup=get_chain_intervals_keyboard(chain_messages),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("admin_chain_interval_edit_"))
async def admin_chain_interval_edit_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Начало изменения интервала одного сообщения из меню интервалов."""
    await callback.answer()
    try:
        message_number = int(callback.data.replace("admin_chain_interval_edit_", ""))
    except ValueError:
        return
    chain_repo = ChainMessageRepository(db)
    existing = await chain_repo.get_chain_message(message_number)
    if not existing:
        await callback.message.answer("❌ Сообщение цепочки не найдено.", disable_web_page_preview=True)
        return
    await state.update_data(chain_interval_message_number=message_number)
    await state.set_state(ChainIntervalOnlyStates.delay_minutes)
    hint = (
        f"Сообщение 1 отправится через N минут после «Сообщения после анкеты»."
        if message_number == 1
        else f"Сообщение {message_number} отправится через N минут после предыдущего сообщения цепочки."
    )
    await callback.message.answer(
        f"⏱ Введите интервал в минутах для сообщения {message_number} (текущее: {existing.delay_minutes} мин.).\n\n"
        f"📌 {hint}\n\nДля отмены отправьте /cancel",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


@router.message(ChainIntervalOnlyStates.delay_minutes)
async def admin_chain_interval_only_delay(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение только интервала из меню «Настройка интервалов»."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    try:
        delay_minutes = int(message.text)
        if delay_minutes < 0:
            await message.answer("❌ Интервал не может быть отрицательным. Введите число от 0 и выше.", disable_web_page_preview=True)
            return
    except (ValueError, TypeError):
        await message.answer("❌ Введите число (количество минут).", disable_web_page_preview=True)
        return
    data = await state.get_data()
    message_number = data.get("chain_interval_message_number")
    if not message_number:
        await state.clear()
        await message.answer("❌ Ошибка: номер сообщения не найден.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    chain_repo = ChainMessageRepository(db)
    await chain_repo.update_chain_message_delay(message_number, delay_minutes)
    await state.clear()
    chain_messages = await chain_repo.get_all_chain_messages()
    text = "⚙️ <b>Настройка интервалов цепочки сообщений</b>\n\n"
    text += f"✅ Интервал для сообщения {message_number} обновлён: {delay_minutes} мин.\n\n"
    text += "Текущие интервалы. Нажмите на сообщение, чтобы изменить только его интервал:\n\n"
    for msg in sorted(chain_messages, key=lambda x: x.message_number):
        text += f"Сообщение {msg.message_number}: {msg.delay_minutes} мин.\n"
    await message.answer(text, reply_markup=get_chain_intervals_keyboard(chain_messages), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    logger.info(f"Админ {message.from_user.id} обновил интервал сообщения {message_number} цепочки: {delay_minutes} мин.")


# ========== Управление каналами ==========

@router.callback_query(F.data == "admin_channels")
async def admin_channels_menu(callback: CallbackQuery, db: Database) -> None:
    """
    Меню управления каналами.
    
    Args:
        callback: Callback запрос
        db: База данных
    """
    await callback.answer()
    
    channel_repo = ChannelRepository(db)
    channels = await channel_repo.get_all_channels()
    
    text = "📢 <b>Каналы для проверки подписки</b>\n\n"
    
    if channels:
        text += f"Всего каналов: {len(channels)}\n\n"
        for i, channel in enumerate(channels[:10], 1):  # Показываем первые 10
            channel_name = channel.title or channel.username or channel.chat_id or "Без названия"
            check_status = "✅" if channel.check_subscription else "❌"
            text += f"{i}. {channel_name} ({channel.type}) {check_status}\n"
        if len(channels) > 10:
            text += f"\n... и еще {len(channels) - 10} каналов"
        text += "\n\n✅ - проверяется подписка\n❌ - не проверяется"
    else:
        text += "Каналы еще не добавлены."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_channels_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_channel_list")
async def admin_channel_list(callback: CallbackQuery, db: Database) -> None:
    """
    Просмотр списка каналов.
    
    Args:
        callback: Callback запрос
        db: База данных
    """
    await callback.answer()
    
    channel_repo = ChannelRepository(db)
    channels = await channel_repo.get_all_channels()
    
    if not channels:
        await callback.message.answer(
            "❌ Каналы еще не добавлены.",
            reply_markup=get_channels_manage_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    text = "📋 <b>Список каналов:</b>\n\n"
    for i, channel in enumerate(channels, 1):
        channel_name = channel.title or channel.username or channel.chat_id or "Без названия"
        check_status = "✅ Проверяется подписка" if channel.check_subscription else "❌ Не проверяется подписка"
        text += f"{i}. <b>{channel_name}</b>\n"
        text += f"   Тип: {channel.type}\n"
        if channel.username:
            text += f"   Username: @{channel.username}\n"
        if channel.chat_id:
            text += f"   Chat ID: {channel.chat_id}\n"
        text += f"   {check_status}\n\n"
    
    await callback.message.answer(text, reply_markup=get_channels_manage_keyboard(), disable_web_page_preview=True)


@router.callback_query(F.data == "admin_channel_add")
async def admin_channel_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начало добавления канала.
    
    Args:
        callback: Callback запрос
        state: FSM контекст
    """
    await callback.answer()
    await state.set_state(ChannelAddStates.waiting_for_channel)
    
    await callback.message.edit_text(
        "➕ <b>Добавление канала</b>\n\n"
        "Отправьте username канала (например: @channel) или перешлите сообщение из канала.\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(ChannelAddStates.waiting_for_channel)
async def admin_channel_add_process(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    """
    Обработка добавления канала - получение информации о канале.
    
    Args:
        message: Сообщение с данными канала
        state: FSM контекст
        db: База данных
        bot: Экземпляр бота
    """
    
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    try:
        chat_id = None
        username = None
        title = None
        channel_type = None
        
        # Если переслано сообщение из канала
        if message.forward_from_chat:
            chat = message.forward_from_chat
            chat_id = str(chat.id)
            username = chat.username
            title = chat.title
            channel_type = "channel" if chat.type == "channel" else "bot"
        
        # Если отправлен username
        elif message.text and message.text.startswith("@"):
            username = message.text.replace("@", "").strip()
            
            # Пытаемся получить информацию о канале
            try:
                chat = await bot.get_chat(f"@{username}")
                chat_id = str(chat.id)
                title = chat.title
                channel_type = "channel" if chat.type == "channel" else "bot"
            except Exception as e:
                await message.answer(
                    f"❌ Ошибка при получении информации о канале: {e}\n\n"
                    "Попробуйте переслать сообщение из канала.",
                    reply_markup=get_back_keyboard(),
                    disable_web_page_preview=True
                )
                return
        else:
            await message.answer(
                "❌ Отправьте username канала (например: @channel) или перешлите сообщение из канала.",
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
            return
        
        # Сохраняем данные канала в состояние и переходим к выбору проверки подписки
        await state.update_data(
            channel_chat_id=chat_id,
            channel_username=username,
            channel_title=title,
            channel_type=channel_type
        )
        await state.set_state(ChannelAddStates.waiting_for_check_subscription)
        
        await message.answer(
            f"📢 <b>Информация о канале</b>\n\n"
            f"Название: {title}\n"
            f"Username: @{username if username else 'не указан'}\n"
            f"Chat ID: {chat_id}\n\n"
            f"<b>Нужно ли проверять подписку на этот канал?</b>",
            reply_markup=get_channel_check_subscription_keyboard(),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке канала: {e}")
        await message.answer(
            f"❌ Ошибка: {e}",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data.in_(["channel_check_yes", "channel_check_no"]), ChannelAddStates.waiting_for_check_subscription)
async def admin_channel_check_subscription_choice(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Обработка выбора проверки подписки для канала (при ручном добавлении)."""
    await callback.answer()
    
    check_subscription = callback.data == "channel_check_yes"
    data = await state.get_data()
    
    channel_repo = ChannelRepository(db)
    
    try:
        await channel_repo.add_channel(
            chat_id=data.get("channel_chat_id"),
            username=data.get("channel_username"),
            title=data.get("channel_title"),
            channel_type=data.get("channel_type", "channel"),
            check_subscription=check_subscription
        )
        
        check_text = "✅ Проверять подписку" if check_subscription else "❌ Не проверять подписку"
        await callback.message.edit_text(
            f"✅ <b>Канал успешно добавлен!</b>\n\n"
            f"Название: {data.get('channel_title')}\n"
            f"Username: @{data.get('channel_username') or 'не указан'}\n"
            f"Chat ID: {data.get('channel_chat_id')}\n\n"
            f"{check_text}",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
        
        await state.clear()
        logger.info(
            f"Админ {callback.from_user.id} добавил канал: "
            f"{data.get('channel_username') or data.get('channel_chat_id')} "
            f"(проверка подписки: {check_subscription})"
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении канала: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при добавлении канала: {e}",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        await state.clear()


@router.callback_query(F.data.in_(["channel_check_yes", "channel_check_no"]), WelcomeMessageStates.waiting_for_channel_check)
async def admin_welcome_channel_check_subscription_choice(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Обработка выбора проверки подписки для каналов из приветственного сообщения."""
    await callback.answer()
    
    check_subscription = callback.data == "channel_check_yes"
    data = await state.get_data()
    
    new_channels = data.get("new_channels", [])
    current_index = data.get("current_channel_index", 0)
    
    if current_index >= len(new_channels):
        await state.clear()
        return
    
    channel_repo = ChannelRepository(db)
    current_channel = new_channels[current_index]
    
    try:
        # Добавляем канал в БД только если выбрано "Проверять подписку"
        if check_subscription:
            if current_channel["channel_type"] == "channel_invite":
                await channel_repo.add_channel(
                    username=current_channel["username"],
                    title=current_channel["title"],
                    channel_type="channel",
                    check_subscription=True
                )
            else:
                await channel_repo.add_channel(
                    chat_id=current_channel["chat_id"],
                    username=current_channel["username"],
                    title=current_channel["title"],
                    channel_type=current_channel["channel_type"],
                    check_subscription=True
                )
            
            logger.info(
                f"Добавлен канал из приветственного сообщения: "
                f"{current_channel.get('username') or current_channel.get('chat_id')} "
                f"(проверка подписки: True)"
            )
        else:
            logger.info(
                f"Канал пропущен (не проверять подписку): "
                f"{current_channel.get('username') or current_channel.get('chat_id')}"
            )
        
        # Обновляем счётчик добавленных каналов
        added_count = data.get("added_count", 0)
        if check_subscription:
            added_count += 1
        await state.update_data(added_count=added_count)
        
        # Переходим к следующему каналу
        next_index = current_index + 1
        
        if next_index < len(new_channels):
            # Есть еще каналы - показываем следующий
            await state.update_data(current_channel_index=next_index)
            
            next_channel = new_channels[next_index]
            channel_name = next_channel["title"] or next_channel["username"] or next_channel["identifier"]
            
            status_text = "✅ добавлен" if check_subscription else "⏭️ пропущен (не проверять)"
            await callback.message.edit_text(
                f"Канал {current_index + 1} {status_text}!\n\n"
                f"<b>Канал {next_index + 1}/{len(new_channels)}</b>\n"
                f"Название: {channel_name}\n\n"
                f"<b>Нужно ли проверять подписку на этот канал?</b>",
                reply_markup=get_channel_check_subscription_keyboard()
            )
        else:
            # Все каналы обработаны - теперь удаляем старые каналы, которых нет в новом сообщении
            all_channel_data = data.get("all_channel_data", [])
            deleted_count = await channel_repo.delete_channels_not_in_list(all_channel_data)
            
            added_count = data.get("added_count", 0)
            await callback.message.edit_text(
                f"✅ <b>Обработка каналов завершена!</b>\n\n"
                f"🗑️ Удалено каналов: {deleted_count}\n"
                f"📢 Добавлено каналов для проверки: {added_count}\n"
                f"⏭️ Пропущено каналов (не проверять): {len(new_channels) - added_count}",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении канала из приветственного сообщения: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при добавлении канала: {e}",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        await state.clear()


@router.callback_query(F.data == "admin_channel_delete")
async def admin_channel_delete_menu(callback: CallbackQuery, db: Database) -> None:
    """
    Меню удаления каналов.
    
    Args:
        callback: Callback запрос
        db: База данных
    """
    await callback.answer()
    
    channel_repo = ChannelRepository(db)
    channels = await channel_repo.get_all_channels()
    
    if not channels:
        await callback.message.edit_text(
            "❌ Нет каналов для удаления.",
            reply_markup=get_channels_manage_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    await callback.message.edit_text(
        "🗑️ <b>Удаление канала</b>\n\n"
        "Выберите канал для удаления:",
        reply_markup=get_channel_delete_keyboard(channels),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("admin_channel_delete_"))
async def admin_channel_delete_confirm(callback: CallbackQuery, db: Database) -> None:
    """
    Подтверждение и удаление канала.
    
    Args:
        callback: Callback запрос
        db: База данных
    """
    await callback.answer()
    
    try:
        channel_id = int(callback.data.split("_")[-1])
        
        channel_repo = ChannelRepository(db)
        channels = await channel_repo.get_all_channels()
        channel_to_delete = next((ch for ch in channels if ch.id == channel_id), None)
        
        if not channel_to_delete:
            await callback.message.answer("❌ Канал не найден.", disable_web_page_preview=True)
            return
        
        # Удаляем канал
        await channel_repo.delete_channel(channel_id)
        
        channel_name = channel_to_delete.title or channel_to_delete.username or f"Канал #{channel_id}"
        await callback.message.edit_text(
            f"✅ Канал '{channel_name}' успешно удален!",
            reply_markup=get_channels_manage_keyboard(),
            disable_web_page_preview=True
        )
        
        logger.info(f"Админ {callback.from_user.id} удалил канал {channel_id}")
        
    except (ValueError, Exception) as e:
        logger.error(f"Ошибка при удалении канала: {e}")
        await callback.message.answer(
            f"❌ Ошибка при удалении канала: {e}",
            reply_markup=get_channels_manage_keyboard(),
            disable_web_page_preview=True
        )


# ========== Управление сообщениями для рассылки ==========

@router.callback_query(F.data == "admin_messages")
async def admin_messages_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню управления сообщениями для рассылки."""
    await callback.answer()
    
    message_repo = MailingMessageRepository(db)
    messages = await message_repo.get_all_mailing_messages()
    
    text = "✉️ <b>Сообщения для рассылки</b>\n\n"
    if messages:
        text += f"Всего сообщений: {len(messages)}\n\n"
        for i, msg in enumerate(messages[:5], 1):
            preview = (msg.text[:50] + "...") if msg.text and len(msg.text) > 50 else (msg.text or "Без текста")
            text += f"{i}. {preview}\n"
        if len(messages) > 5:
            text += f"\n... и еще {len(messages) - 5} сообщений"
    else:
        text += "Сообщения еще не созданы."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_messages_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_message_list")
async def admin_message_list(callback: CallbackQuery, db: Database) -> None:
    """Список сообщений для рассылки."""
    await callback.answer()
    
    message_repo = MailingMessageRepository(db)
    messages = await message_repo.get_all_mailing_messages()
    
    if not messages:
        await callback.message.answer(
            "❌ Сообщения еще не созданы.",
            reply_markup=get_messages_manage_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    text = "📋 <b>Список сообщений для рассылки:</b>\n\n"
    for i, msg in enumerate(messages, 1):
        text += f"{i}. <b>ID: {msg.id}</b>\n"
        if msg.text:
            preview = msg.text[:100] + "..." if len(msg.text) > 100 else msg.text
            text += f"   {preview}\n"
        if msg.media_type:
            text += f"   Медиа: {msg.media_type}\n"
        text += f"   Создано: {msg.created_at}\n\n"
    
    await callback.message.answer(text, reply_markup=get_messages_manage_keyboard(), disable_web_page_preview=True)


@router.callback_query(F.data == "admin_message_create")
async def admin_message_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало создания сообщения для рассылки вручную."""
    await callback.answer()
    await state.set_state(MailingMessageStates.text)
    
    await callback.message.edit_text(
        "✏️ <b>Создание сообщения для рассылки</b>\n\n"
        "<b>Шаг 1/3: Текст сообщения</b>\n\n"
        "Отправьте текст сообщения.\n"
        "Вы можете использовать форматирование (жирный, курсив и т.д.).\n\n"
        "💡 <i>Если нужен только текст без медиа и кнопок, отправьте /skip после текста</i>\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(MailingMessageStates.text)
async def admin_message_create_text(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение текста сообщения для рассылки."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    # Пропуск медиа и кнопок
    if message.text and message.text.lower() in ["/skip", "пропустить", "skip"]:
        text = ""
        entities_json = None
    else:
        text = message.text or message.caption or ""
        entities_json = None
        
        # Сохраняем entities
        entities = message.entities or message.caption_entities or []
        if entities:
            entities_list = []
            for entity in entities:
                entity_dict = {
                    "type": entity.type,
                    "offset": entity.offset,
                    "length": entity.length
                }
                if entity.type == "text_link":
                    entity_dict["url"] = entity.url
                entities_list.append(entity_dict)
            entities_json = json.dumps(entities_list, ensure_ascii=False)
    
    # Проверяем наличие медиа в первом сообщении
    media_type = None
    media_file_id = None
    
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    # Сохраняем в состояние
    await state.update_data(
        text=text,
        entities_json=entities_json,
        media_type=media_type,
        media_file_id=media_file_id
    )
    
    # Переходим к шагу медиа
    await state.set_state(MailingMessageStates.media)
    
    if media_type:
        await message.answer(
            f"✅ <b>Шаг 1/3 завершен:</b> Текст и медиа сохранены.\n\n"
            f"<b>Шаг 2/3: Дополнительное медиа (опционально)</b>\n\n"
            f"Если хотите добавить еще медиа, отправьте фото или видео.\n"
            f"Или отправьте /skip чтобы пропустить этот шаг.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
    else:
        await message.answer(
            f"✅ <b>Шаг 1/3 завершен:</b> Текст сохранен.\n\n"
            f"<b>Шаг 2/3: Медиа (опционально)</b>\n\n"
            f"Отправьте фото или видео для сообщения.\n"
            f"Или отправьте /skip чтобы пропустить этот шаг.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


@router.message(MailingMessageStates.media)
async def admin_message_create_media(message: Message, state: FSMContext, db: Database) -> None:
    """Обработка медиа для сообщения рассылки."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    # Пропуск медиа
    if message.text and message.text.lower() in ["/skip", "пропустить", "skip"]:
        await state.set_state(MailingMessageStates.waiting_for_buttons)
        await message.answer(
            "✅ <b>Шаг 2/3 пропущен.</b>\n\n"
            "<b>Шаг 3/3: Кнопки (опционально)</b>\n\n"
            "Отправьте кнопки в формате:\n"
            "<code>Текст кнопки1:ссылка1;Текст кнопки2:ссылка2</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>Перейти на сайт:https://example.com;Наш канал:https://t.me/channel</code>\n\n"
            "Или отправьте /skip чтобы завершить без кнопок.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    # Проверяем медиа
    media_type = None
    media_file_id = None
    
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    if media_type:
        # Обновляем медиа в состоянии (перезаписываем предыдущее)
        await state.update_data(
            media_type=media_type,
            media_file_id=media_file_id
        )
        
        # Если есть подпись к медиа, обновляем текст
        if message.caption:
            entities_json = None
            entities = message.caption_entities or []
            if entities:
                entities_list = []
                for entity in entities:
                    entity_dict = {
                        "type": entity.type,
                        "offset": entity.offset,
                        "length": entity.length
                    }
                    if entity.type == "text_link":
                        entity_dict["url"] = entity.url
                    entities_list.append(entity_dict)
                entities_json = json.dumps(entities_list, ensure_ascii=False)
            
            await state.update_data(
                text=message.caption,
                entities_json=entities_json
            )
        
        await state.set_state(MailingMessageStates.waiting_for_buttons)
        await message.answer(
            f"✅ <b>Шаг 2/3 завершен:</b> Медиа сохранено ({media_type}).\n\n"
            f"<b>Шаг 3/3: Кнопки (опционально)</b>\n\n"
            f"Отправьте кнопки в формате:\n"
            f"<code>Текст кнопки1:ссылка1;Текст кнопки2:ссылка2</code>\n\n"
            f"<b>Пример:</b>\n"
            f"<code>Перейти на сайт:https://example.com;Наш канал:https://t.me/channel</code>\n\n"
            f"Или отправьте /skip чтобы завершить без кнопок.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
    else:
        await message.answer(
            "❌ Пожалуйста, отправьте фото или видео, либо отправьте /skip для пропуска.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


@router.message(MailingMessageStates.waiting_for_buttons)
async def admin_message_create_buttons(message: Message, state: FSMContext, db: Database) -> None:
    """Сохранение кнопок и создание сообщения для рассылки."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    buttons_json = None
    
    # Пропуск кнопок
    if message.text and message.text.lower() in ["/skip", "пропустить", "skip"]:
        buttons_json = None
    elif message.text and ":" in message.text:
        # Парсим кнопки из текстового формата: текст:ссылка;текст:ссылка
        try:
            buttons_list = []
            # Разделяем по точке с запятой для разных кнопок
            button_strings = message.text.split(";")
            
            for button_str in button_strings:
                button_str = button_str.strip()
                if not button_str:
                    continue
                
                # Разделяем текст и ссылку
                if ":" in button_str:
                    parts = button_str.split(":", 1)  # Разделяем только по первому двоеточию
                    button_text = parts[0].strip()
                    button_url = parts[1].strip() if len(parts) > 1 else None
                    
                    if button_text and button_url:
                        button_url = button_url.strip()
                        # Поддерживаем короткий формат @username — оставляем как есть,
                        # дальнейшую нормализацию сделает resolve_button_url при отправке.
                        if not button_url.startswith("@"):
                            # Проверяем, что ссылка валидна
                            if not (button_url.startswith("http://") or 
                                   button_url.startswith("https://") or 
                                   button_url.startswith("tg://") or
                                   button_url.startswith("t.me/")):
                                # Если нет протокола, добавляем https://
                                if button_url.startswith("t.me/"):
                                    button_url = "https://" + button_url
                                elif not button_url.startswith("http"):
                                    button_url = "https://" + button_url
                        
                        buttons_list.append([{
                            "text": button_text,
                            "url": button_url,
                            "callback_data": None
                        }])
            
            if buttons_list:
                buttons_json = json.dumps(buttons_list, ensure_ascii=False)
            else:
                await message.answer(
                    "❌ Не удалось распарсить кнопки.\n\n"
                    "Проверьте формат:\n"
                    "<code>Текст кнопки1:ссылка1;Текст кнопки2:ссылка2</code>\n\n"
                    "Или отправьте /skip чтобы пропустить.",
                    reply_markup=get_back_keyboard(),
                    disable_web_page_preview=True
                )
                return
                
        except Exception as e:
            logger.error(f"Ошибка парсинга кнопок: {e}")
            await message.answer(
                f"❌ Ошибка при парсинге кнопок: {e}\n\n"
                "Проверьте формат:\n"
                "<code>Текст кнопки1:ссылка1;Текст кнопки2:ссылка2</code>\n\n"
                "Или отправьте /skip чтобы пропустить.",
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
            return
    elif message.reply_markup and message.reply_markup.inline_keyboard:
        # Также поддерживаем пересылку сообщения с кнопками (для обратной совместимости)
        buttons_list = []
        for row in message.reply_markup.inline_keyboard:
            row_buttons = []
            for button in row:
                button_dict = {
                    "text": button.text,
                    "url": button.url if hasattr(button, "url") and button.url else None,
                    "callback_data": button.callback_data if hasattr(button, "callback_data") and button.callback_data else None
                }
                row_buttons.append(button_dict)
            buttons_list.append(row_buttons)
        buttons_json = json.dumps(buttons_list, ensure_ascii=False)
    else:
        # Если отправлено сообщение без кнопок и не /skip
        await message.answer(
            "❌ Неверный формат кнопок.\n\n"
            "Отправьте кнопки в формате:\n"
            "<code>Текст кнопки1:ссылка1;Текст кнопки2:ссылка2</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>Перейти на сайт:https://example.com;Наш канал:https://t.me/channel</code>\n\n"
            "Или отправьте /skip чтобы завершить без кнопок.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    
    # Проверяем, что есть хотя бы текст или медиа
    if not data.get("text") and not data.get("media_type"):
        await message.answer(
            "❌ Ошибка: сообщение должно содержать текст или медиа.\n"
            "Начните создание заново.",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
        await state.clear()
        return
    
    # Создаем сообщение для рассылки
    message_repo = MailingMessageRepository(db)
    mailing_message = await message_repo.create_mailing_message(
        text=data.get("text"),
        entities_json=data.get("entities_json"),
        media_type=data.get("media_type"),
        media_file_id=data.get("media_file_id"),
        buttons_json=buttons_json
    )
    
    await state.clear()
    
    # Формируем информацию о созданном сообщении
    info_text = "✅ <b>Сообщение для рассылки успешно создано!</b>\n\n"
    info_text += f"📝 ID сообщения: <b>{mailing_message.id}</b>\n"
    if mailing_message.text:
        preview = mailing_message.text[:50] + "..." if len(mailing_message.text) > 50 else mailing_message.text
        info_text += f"📄 Текст: {preview}\n"
    if mailing_message.media_type:
        info_text += f"🖼️ Медиа: {mailing_message.media_type}\n"
    if buttons_json:
        info_text += f"🔘 Кнопки: добавлены\n"
    
    await message.answer(
        info_text,
        reply_markup=get_admin_main_keyboard(),
        disable_web_page_preview=True
    )
    
    logger.info(f"Админ {message.from_user.id} создал сообщение для рассылки (id={mailing_message.id})")


@router.callback_query(F.data == "admin_message_forward")
async def admin_message_forward_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало создания сообщения через пересылку."""
    await callback.answer()
    await state.set_state("admin_message_forward")
    
    await callback.message.edit_text(
        "📤 <b>Создание сообщения через пересылку</b>\n\n"
        "Перешлите сообщение, которое хотите использовать для рассылки.\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(F.forward_date)
async def admin_message_forward_process(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    """Обработка пересланного сообщения для рассылки, сообщения после анкеты или приветственного сообщения."""
    current_state = await state.get_state()
    
    # Проверяем, что мы находимся в нужном состоянии для обработки пересылки
    if current_state not in ["admin_message_forward", "admin_start_message_forward", "admin_welcome_forward", "admin_post_questionnaire_forward", "admin_chain_forward"]:
        return
    
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    # Извлекаем данные из пересланного сообщения
    text = message.text or message.caption or ""
    entities_json = None
    media_type = None
    media_file_id = None
    buttons_json = None
    
    # Сохраняем entities
    entities = message.entities or message.caption_entities or []
    if entities:
        entities_list = []
        for entity in entities:
            entity_dict = {
                "type": entity.type,
                "offset": entity.offset,
                "length": entity.length
            }
            if entity.type == "text_link":
                entity_dict["url"] = entity.url
            entities_list.append(entity_dict)
        entities_json = json.dumps(entities_list, ensure_ascii=False)
    
    # Проверяем медиа
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    # Сохраняем кнопки
    if message.reply_markup and message.reply_markup.inline_keyboard:
        buttons_list = []
        for row in message.reply_markup.inline_keyboard:
            row_buttons = []
            for button in row:
                button_dict = {
                    "text": button.text,
                    "url": button.url if hasattr(button, "url") and button.url else None,
                    "callback_data": button.callback_data if hasattr(button, "callback_data") and button.callback_data else None
                }
                row_buttons.append(button_dict)
            buttons_list.append(row_buttons)
        buttons_json = json.dumps(buttons_list, ensure_ascii=False)
    
    # Обработка для "Сообщения после /start"
    if current_state == "admin_start_message_forward":
        # Сообщение после /start поддерживает только текст и форматирование
        start_repo = StartMessageRepository(db)
        await start_repo.create_or_update_start_message(text, entities_json)
        
        await state.clear()
        await message.answer(
            "✅ Сообщение после /start успешно создано из пересланного сообщения!\n\n"
            "💡 Это сообщение будет отправляться пользователям сразу после команды /start (самым первым).\n\n"
            "⚠️ Медиа и кнопки не поддерживаются "
            "(сообщение после /start поддерживает только текст и форматирование).",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
        logger.info(f"Админ {message.from_user.id} создал сообщение после /start через пересылку")
        return
    
    # Обработка для "Приветственного сообщения"
    if current_state == "admin_welcome_forward":
        # Приветственное сообщение поддерживает только текст и форматирование
        # Медиа и кнопки игнорируются
        welcome_repo = WelcomeMessageRepository(db)
        await welcome_repo.create_or_update_welcome_message(text, entities_json)
        
        # Парсинг ссылок из приветственного сообщения и сохранение каналов в БД
        from bot.utils.helpers import extract_channel_links
        from bot.database.repositories import ChannelRepository
        
        channels_found = extract_channel_links(text, entities_json=entities_json)
        channel_repo = ChannelRepository(db)
        
        # Собираем все каналы из нового сообщения с их данными
        new_channel_data = []  # Список кортежей (identifier, channel_type, chat_id, username, title)
        
        for username_or_id, channel_type in channels_found:
            try:
                # Если это invite-ссылка (начинается с +), обрабатываем отдельно
                if channel_type == "channel_invite":
                    new_channel_data.append((
                        username_or_id,
                        channel_type,
                        None,
                        username_or_id,  # Сохраняем invite-ссылку в username
                        f"Приватный канал ({username_or_id[:20]}...)"
                    ))
                    continue
                
                # Для обычных каналов пытаемся получить информацию
                try:
                    # Формируем правильный идентификатор для get_chat
                    chat_identifier = username_or_id if username_or_id.startswith("@") else f"@{username_or_id}"
                    chat = await bot.get_chat(chat_identifier)
                    chat_id = str(chat.id)
                    username = chat.username
                    title = chat.title
                    
                    new_channel_data.append((
                        username_or_id,
                        channel_type,
                        chat_id,
                        username,
                        title
                    ))
                except Exception as e:
                    logger.warning(f"Не удалось получить информацию о канале {username_or_id}: {e}")
                    # Все равно добавляем с минимальной информацией
                    if username_or_id.startswith("@"):
                        username = username_or_id[1:]
                    else:
                        username = username_or_id
                    
                    new_channel_data.append((
                        username_or_id,
                        channel_type,
                        None,
                        username,
                        None
                    ))
            except Exception as e:
                logger.error(f"Ошибка при обработке канала {username_or_id}: {e}")
        
        # Собираем новые каналы (которых еще нет в БД)
        new_channels_to_add = []
        existing_channels = await channel_repo.get_all_channels()
        
        for identifier, channel_type, chat_id, username, title in new_channel_data:
            try:
                # Проверяем, существует ли уже такой канал
                exists = False
                if chat_id:
                    exists = any(
                        ch.chat_id == chat_id for ch in existing_channels
                    )
                if not exists and username:
                    exists = any(
                        ch.username == username for ch in existing_channels
                    )
                
                if not exists:
                    new_channels_to_add.append({
                        "identifier": identifier,
                        "channel_type": channel_type,
                        "chat_id": chat_id,
                        "username": username,
                        "title": title
                    })
            except Exception as e:
                logger.error(f"Ошибка при проверке канала {identifier}: {e}")
        
        # Если есть новые каналы, сохраняем их в FSM и показываем выбор проверки подписки
        if new_channels_to_add:
            # Сохраняем список новых каналов и все каналы из сообщения в FSM
            await state.update_data(
                new_channels=new_channels_to_add,
                all_channel_data=new_channel_data,  # Все каналы из нового сообщения (для удаления старых)
                current_channel_index=0,
                added_count=0  # Счётчик добавленных каналов (с check_subscription=True)
            )
            await state.set_state(WelcomeMessageStates.waiting_for_channel_check)
            
            # Показываем первый канал для выбора
            first_channel = new_channels_to_add[0]
            channel_name = first_channel["title"] or first_channel["username"] or first_channel["identifier"]
            
            await message.answer(
                f"✅ Приветственное сообщение успешно создано из пересланного сообщения!\n\n"
                f"📢 Найдено новых каналов: {len(new_channels_to_add)}\n\n"
                f"<b>Канал 1/{len(new_channels_to_add)}</b>\n"
                f"Название: {channel_name}\n\n"
                f"<b>Нужно ли проверять подписку на этот канал?</b>",
                reply_markup=get_channel_check_subscription_keyboard()
            )
            return  # Не очищаем state, продолжаем обработку каналов
        
        # Нет новых каналов - завершаем
        await state.clear()
        
        success_message = (
            "✅ Приветственное сообщение успешно создано из пересланного сообщения!\n\n"
            "💡 Это сообщение будет отправляться пользователям при команде /start.\n\n"
        )
        
        success_message += "📢 Каналы в сообщении уже присутствуют в базе данных.\n\n"
        
        if media_type or buttons_json:
            success_message += (
                "⚠️ Примечание: медиа и кнопки из пересланного сообщения не сохранены "
                "(приветственное сообщение поддерживает только текст и форматирование)."
            )
        
        await message.answer(
            success_message,
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
        
        logger.info(f"Админ {message.from_user.id} создал приветственное сообщение через пересылку")
        return
    
    # Обработка для "Сообщения после анкеты"
    if current_state == "admin_post_questionnaire_forward":
        post_questionnaire_repo = PostQuestionnaireMessageRepository(db)
        await post_questionnaire_repo.create_or_update_post_questionnaire_message(
            text=text,
            entities_json=entities_json,
            media_type=media_type,
            media_file_id=media_file_id,
            buttons_json=buttons_json
        )
        await state.clear()
        await message.answer(
            "✅ Сообщение после анкеты успешно создано из пересланного сообщения!\n\n"
            "💡 Оно будет отправляться пользователям через 5 секунд после заполнения анкеты (если активно).",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
        logger.info(f"Админ {message.from_user.id} создал сообщение после анкеты через пересылку")
        return
    
    # Обработка для сообщения цепочки
    if current_state == "admin_chain_forward":
        data = await state.get_data()
        message_number = data.get("chain_message_number")
        
        if not message_number:
            await state.clear()
            await message.answer("❌ Ошибка: номер сообщения не найден.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
            return
        
        # Сохраняем данные из пересланного сообщения в состояние
        await state.update_data(
            text=text,
            entities_json=entities_json,
            media_type=media_type,
            media_file_id=media_file_id,
            buttons_json=buttons_json
        )
        
        # Переходим к запросу интервала времени
        await state.set_state(ChainMessageStates.delay_minutes)
        
        chain_repo = ChainMessageRepository(db)
        existing_msg = await chain_repo.get_chain_message(message_number)
        current_delay = ChainMessageRepository.get_default_delay(message_number, existing_msg)
        
        # Формируем подсказку в зависимости от номера сообщения
        if message_number == 1:
            hint_text = (
                f"📌 <b>Важно:</b> Для первого сообщения интервал считается от 'Сообщения после анкеты'.\n"
                f"⚠️ Если установить 0 минут, сообщение отправится сразу после 'Сообщения после анкеты'.\n\n"
            )
        else:
            hint_text = (
                f"📌 <b>Важно:</b> Интервал считается от предыдущего сообщения цепочки.\n"
                f"⚠️ Если установить 0 минут, сообщение отправится сразу после предыдущего.\n\n"
            )
        
        await message.answer(
            f"✅ Данные из пересланного сообщения сохранены!\n\n"
            f"<b>Настройка интервала времени для сообщения {message_number}</b>\n\n"
            f"{hint_text}"
            f"Отправьте количество минут задержки.\n"
            f"Текущее значение: <b>{current_delay} минут</b>\n\n"
            f"<i>Пример: если указать 30 минут, сообщение отправится через 30 минут после предыдущего.</i>\n\n"
            f"Для отмены отправьте /cancel",
            reply_markup=get_back_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        
        logger.info(f"Админ {message.from_user.id} переслал сообщение для цепочки {message_number}, ожидается интервал")
        return
    
    # Обработка для сообщения для рассылки (старая логика)
    if current_state == "admin_message_forward":
        message_repo = MailingMessageRepository(db)
        mailing_message = await message_repo.create_mailing_message(
            text=text,
            entities_json=entities_json,
            media_type=media_type,
            media_file_id=media_file_id,
            buttons_json=buttons_json
        )
        
        await state.clear()
        await message.answer(
            f"✅ Сообщение для рассылки успешно создано из пересланного сообщения!\n\n"
            f"ID сообщения: {mailing_message.id}",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
        
        logger.info(f"Админ {message.from_user.id} создал сообщение для рассылки через пересылку (id={mailing_message.id})")
        return


# ========== Управление рассылками ==========

@router.callback_query(F.data == "admin_mailings")
async def admin_mailings_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню управления рассылками."""
    await callback.answer()
    
    mailing_repo = MailingRepository(db)
    mailings = await mailing_repo.get_all_mailings()
    
    text = "📤 <b>Рассылки</b>\n\n"
    if mailings:
        text += f"Всего рассылок: {len(mailings)}\n\n"
        for i, mailing in enumerate(mailings[:5], 1):
            text += f"{i}. ID: {mailing.id} | Отправлено: {mailing.sent_count} | Ошибок: {mailing.failed_count}\n"
        if len(mailings) > 5:
            text += f"\n... и еще {len(mailings) - 5} рассылок"
    else:
        text += "Рассылки еще не созданы."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_mailing_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_mailing_send")
async def admin_mailing_send_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню выбора сообщения для рассылки."""
    await callback.answer()
    
    message_repo = MailingMessageRepository(db)
    messages = await message_repo.get_all_mailing_messages()
    
    if not messages:
        await callback.message.answer(
            "❌ Нет сообщений для рассылки. Сначала создайте сообщение.",
            reply_markup=get_mailing_manage_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    for msg in messages[:10]:  # Максимум 10 сообщений
        preview = (msg.text[:30] + "...") if msg.text and len(msg.text) > 30 else (msg.text or f"Сообщение #{msg.id}")
        buttons.append([
            InlineKeyboardButton(
                text=f"📤 {preview}",
                callback_data=f"admin_mailing_send_{msg.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_mailings")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "📤 <b>Отправка рассылки</b>\n\n"
        "Выберите сообщение для рассылки:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("admin_mailing_send_"))
async def admin_mailing_send_confirm(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    """Подтверждение и запуск рассылки."""
    await callback.answer()
    
    try:
        message_id = int(callback.data.split("_")[-1])
        
        # Запрашиваем подтверждение
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        confirm_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, отправить", callback_data=f"admin_mailing_confirm_{message_id}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="admin_mailings")
                ]
            ]
        )
        
        await callback.message.edit_text(
            "⚠️ <b>Подтверждение рассылки</b>\n\n"
            "Рассылка будет отправлена всем пользователям бота.\n"
            "Это может занять некоторое время.\n\n"
            "Продолжить?",
            reply_markup=confirm_keyboard
        )
        
    except (ValueError, Exception) as e:
        logger.error(f"Ошибка при подготовке рассылки: {e}")
        await callback.message.answer(
            f"❌ Ошибка: {e}",
            reply_markup=get_mailing_manage_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data.startswith("admin_mailing_confirm_"))
async def admin_mailing_send_execute(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    """Выполнение рассылки (немедленная отправка)."""
    await callback.answer("Рассылка запущена...", show_alert=True)
    
    try:
        message_id = int(callback.data.split("_")[-1])
        
        # Запускаем рассылку в фоне
        from bot.services.mailing import send_mailing_to_all_users
        
        await callback.message.edit_text(
            "⏳ <b>Рассылка запущена</b>\n\n"
            "Рассылка выполняется в фоновом режиме.\n"
            "Результаты будут сохранены в истории рассылок."
        )
        
        # Запускаем рассылку (без планирования)
        result = await send_mailing_to_all_users(bot, db, message_id, scheduled_time=None)
        
        if "error" in result:
            await callback.message.answer(
                f"❌ Ошибка при рассылке: {result['error']}",
                reply_markup=get_mailing_manage_keyboard(),
                disable_web_page_preview=True
            )
        else:
            await callback.message.answer(
                f"✅ <b>Рассылка завершена!</b>\n\n"
                f"📊 Статистика:\n"
                f"✅ Отправлено: {result['sent']}\n"
                f"❌ Ошибок: {result['failed']}\n"
                f"📝 Всего пользователей: {result['total']}",
                reply_markup=get_mailing_manage_keyboard(),
                disable_web_page_preview=True
            )
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении рассылки: {e}")
        await callback.message.answer(
            f"❌ Ошибка при рассылке: {e}",
            reply_markup=get_mailing_manage_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "admin_mailing_schedule")
async def admin_mailing_schedule_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню выбора сообщения для планирования."""
    await callback.answer()
    
    message_repo = MailingMessageRepository(db)
    messages = await message_repo.get_all_mailing_messages()
    
    if not messages:
        await callback.message.answer(
            "❌ Нет сообщений для рассылки. Сначала создайте сообщение.",
            reply_markup=get_mailing_manage_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    for msg in messages[:10]:  # Максимум 10 сообщений
        preview = (msg.text[:30] + "...") if msg.text and len(msg.text) > 30 else (msg.text or f"Сообщение #{msg.id}")
        buttons.append([
            InlineKeyboardButton(
                text=f"📅 {preview}",
                callback_data=f"admin_mailing_schedule_{msg.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_mailings")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "📅 <b>Планирование рассылки</b>\n\n"
        "Выберите сообщение для планирования:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("admin_mailing_schedule_"))
async def admin_mailing_schedule_time(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Запрос времени для планирования рассылки."""
    await callback.answer()
    
    try:
        message_id = int(callback.data.split("_")[-1])
        
        # Сохраняем message_id в состоянии
        await state.update_data(schedule_message_id=message_id)
        await state.set_state(MailingScheduleStates.waiting_for_time)
        
        await callback.message.edit_text(
            "📅 <b>Планирование рассылки</b>\n\n"
            "Отправьте дату и время в формате:\n"
            "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
            "<b>Примеры:</b>\n"
            "<code>25.01.2026 15:30</code>\n"
            "<code>01.02.2026 10:00</code>\n\n"
            "Или отправьте /cancel для отмены.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        
    except (ValueError, Exception) as e:
        logger.error(f"Ошибка при планировании рассылки: {e}")
        await callback.message.answer(
            f"❌ Ошибка: {e}",
            reply_markup=get_mailing_manage_keyboard(),
            disable_web_page_preview=True
        )


@router.message(MailingScheduleStates.waiting_for_time)
async def admin_mailing_schedule_process(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    """Обработка времени для планирования рассылки."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    from datetime import datetime
    
    try:
        # Парсим дату и время
        time_str = message.text.strip()
        
        # Пробуем разные форматы
        formats = [
            "%d.%m.%Y %H:%M",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M",
            "%d.%m.%Y %H:%M:%S",
        ]
        
        scheduled_datetime = None
        for fmt in formats:
            try:
                scheduled_datetime = datetime.strptime(time_str, fmt)
                break
            except ValueError:
                continue
        
        if not scheduled_datetime:
            await message.answer(
                "❌ Неверный формат даты и времени.\n\n"
                "Используйте формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
                "Пример: <code>25.01.2026 15:30</code>",
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
            return
        
        # Проверяем, что время в будущем
        if scheduled_datetime <= datetime.now():
            await message.answer(
                "❌ Время должно быть в будущем.\n\n"
                "Пожалуйста, укажите дату и время позже текущего момента.",
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
            return
        
        # Получаем message_id из состояния
        data = await state.get_data()
        message_id = data.get("schedule_message_id")
        
        if not message_id:
            await message.answer(
                "❌ Ошибка: не найден ID сообщения.",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
            await state.clear()
            return
        
        # Создаем запланированную рассылку
        scheduled_time_str = scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S")
        mailing_repo = MailingRepository(db)
        mailing = await mailing_repo.create_mailing(message_id, scheduled_time_str)
        
        await state.clear()
        
        await message.answer(
            f"✅ <b>Рассылка запланирована!</b>\n\n"
            f"📅 Дата и время: <b>{scheduled_datetime.strftime('%d.%m.%Y %H:%M')}</b>\n"
            f"📝 ID рассылки: <b>{mailing.id}</b>\n\n"
            f"Рассылка будет автоматически запущена в указанное время.",
            reply_markup=get_admin_main_keyboard(),
            disable_web_page_preview=True
        )
        
        logger.info(
            f"Админ {message.from_user.id} запланировал рассылку "
            f"(mailing_id={mailing.id}, time={scheduled_time_str})"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при планировании рассылки: {e}")
        await message.answer(
            f"❌ Ошибка при планировании: {e}\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены.",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "admin_mailing_scheduled")
async def admin_mailing_scheduled_list(callback: CallbackQuery, db: Database) -> None:
    """Список запланированных рассылок."""
    await callback.answer()
    
    mailing_repo = MailingRepository(db)
    message_repo = MailingMessageRepository(db)
    
    # Получаем все рассылки со статусом scheduled
    all_mailings = await mailing_repo.get_all_mailings()
    scheduled_mailings = [m for m in all_mailings if m.status == "scheduled" and m.scheduled_time]
    
    if not scheduled_mailings:
        await callback.message.answer(
            "📅 Нет запланированных рассылок.",
            reply_markup=get_mailing_manage_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    from datetime import datetime
    
    text = "📅 <b>Запланированные рассылки:</b>\n\n"
    for i, mailing in enumerate(scheduled_mailings[:10], 1):
        message = await message_repo.get_mailing_message(mailing.message_id)
        preview = (message.text[:30] + "...") if message and message.text and len(message.text) > 30 else (f"Сообщение #{mailing.message_id}" if message else "Удалено")
        
        scheduled_dt = datetime.strptime(mailing.scheduled_time, "%Y-%m-%d %H:%M:%S")
        formatted_time = scheduled_dt.strftime("%d.%m.%Y %H:%M")
        
        text += f"{i}. <b>ID: {mailing.id}</b>\n"
        text += f"   Сообщение: {preview}\n"
        text += f"   📅 Время: {formatted_time}\n\n"
    
    if len(scheduled_mailings) > 10:
        text += f"\n... и еще {len(scheduled_mailings) - 10} рассылок"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_mailing_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_mailing_history")
async def admin_mailing_history(callback: CallbackQuery, db: Database) -> None:
    """История рассылок."""
    await callback.answer()
    
    mailing_repo = MailingRepository(db)
    message_repo = MailingMessageRepository(db)
    mailings = await mailing_repo.get_all_mailings()
    
    if not mailings:
        await callback.message.answer(
            "❌ История рассылок пуста.",
            reply_markup=get_mailing_manage_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    from datetime import datetime
    
    text = "📋 <b>История рассылок:</b>\n\n"
    for i, mailing in enumerate(mailings[:10], 1):
        message = await message_repo.get_mailing_message(mailing.message_id)
        preview = (message.text[:30] + "...") if message and message.text and len(message.text) > 30 else (f"Сообщение #{mailing.message_id}" if message else "Удалено")
        
        # Определяем статус
        status_emoji = {
            "pending": "⏳",
            "scheduled": "📅",
            "sending": "⏳",
            "sent": "✅",
            "failed": "❌"
        }
        status_text = {
            "pending": "Ожидает",
            "scheduled": "Запланирована",
            "sending": "Отправляется",
            "sent": "Отправлена",
            "failed": "Ошибка"
        }
        
        emoji = status_emoji.get(mailing.status, "❓")
        status = status_text.get(mailing.status, mailing.status)
        
        text += f"{i}. <b>ID: {mailing.id}</b> {emoji} {status}\n"
        text += f"   Сообщение: {preview}\n"
        
        if mailing.scheduled_time:
            scheduled_dt = datetime.strptime(mailing.scheduled_time, "%Y-%m-%d %H:%M:%S")
            text += f"   📅 Запланировано: {scheduled_dt.strftime('%d.%m.%Y %H:%M')}\n"
        
        if mailing.status == "sent":
            text += f"   ✅ Отправлено: {mailing.sent_count}\n"
            text += f"   ❌ Ошибок: {mailing.failed_count}\n"
        
        text += f"   📅 Создано: {mailing.created_at}\n\n"
    
    if len(mailings) > 10:
        text += f"\n... и еще {len(mailings) - 10} рассылок"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_mailing_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_mailing_timer")
async def admin_mailing_timer(callback: CallbackQuery) -> None:
    """Настройки таймера рассылки."""
    await callback.answer()
    
    current_delay = RunnerConfig.MAILING_DELAY
    
    await callback.message.edit_text(
        f"⚙️ <b>Настройки таймера рассылки</b>\n\n"
        f"Текущая задержка между сообщениями: <b>{current_delay} секунд</b>\n\n"
        f"Задержка настраивается через переменную окружения MAILING_DELAY в файле .env\n\n"
        f"Рекомендуемые значения:\n"
        f"• 0.05 - быстро (20 сообщений/сек)\n"
        f"• 0.1 - нормально (10 сообщений/сек)\n"
        f"• 0.2 - медленно (5 сообщений/сек)",
        reply_markup=get_mailing_manage_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_statistics")
async def admin_statistics_menu(callback: CallbackQuery) -> None:
    """Выбор периода для Статистики."""
    await callback.answer()
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        "Выберите период для отчёта:"
    )
    try:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_statistics_period_keyboard(),
            disable_web_page_preview=True
        )
    except TelegramBadRequest as e:
        if "no text" in str(e).lower() or "message to edit" in str(e).lower():
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_statistics_period_keyboard(),
                disable_web_page_preview=True
            )
        else:
            raise


def _statistics_calendar_with_back(calendar_kb: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Добавляет к календарю строку с кнопкой «Назад»."""
    back_row = [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    return InlineKeyboardMarkup(inline_keyboard=calendar_kb.inline_keyboard + [back_row])


@router.callback_query(F.data == "admin_statistics_period_custom")
async def admin_statistics_custom_period_start(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Запуск выбора своего периода: показ календаря для даты начала."""
    await callback.answer()
    await state.set_state(StatisticsCustomPeriodStates.date_from)
    calendar_kb = await SimpleCalendar().start_calendar()
    await callback.message.edit_text(
        "📊 <b>Свой период</b>\n\nВыберите <b>дату начала</b> периода:",
        parse_mode=ParseMode.HTML,
        reply_markup=_statistics_calendar_with_back(calendar_kb),
        disable_web_page_preview=True,
    )


@router.callback_query(
    SimpleCalendarCallback.filter(),
    StateFilter(
        StatisticsCustomPeriodStates.date_from,
        StatisticsCustomPeriodStates.date_to,
        QuestionnaireCustomPeriodStates.date_from,
        QuestionnaireCustomPeriodStates.date_to,
        ActionsCustomPeriodStates.date_from,
        ActionsCustomPeriodStates.date_to,
    ),
)
async def admin_statistics_calendar_select(
    callback: CallbackQuery,
    state: FSMContext,
    callback_data: SimpleCalendarCallback,
    db: Database,
    bot: Bot,
) -> None:
    """Обработка выбора даты в календаре: дата начала → календарь окончания → статистика."""
    from datetime import datetime, timedelta

    act = callback_data.act
    year, month = int(callback_data.year), int(callback_data.month)

    # Навигация по месяцам/годам: обрабатываем сами, чтобы сохранить кнопку «Назад» и ответ на callback
    if act in (
        SimpleCalendarAction.PREV_YEAR,
        SimpleCalendarAction.NEXT_YEAR,
        SimpleCalendarAction.PREV_MONTH,
        SimpleCalendarAction.NEXT_MONTH,
    ):
        await callback.answer()
        temp = datetime(year, month, 1)
        if act == SimpleCalendarAction.PREV_YEAR:
            temp = temp.replace(year=year - 1)
        elif act == SimpleCalendarAction.NEXT_YEAR:
            temp = temp.replace(year=year + 1)
        elif act == SimpleCalendarAction.PREV_MONTH:
            temp = (temp - timedelta(days=1)).replace(day=1)
        elif act == SimpleCalendarAction.NEXT_MONTH:
            temp = (temp + timedelta(days=31)).replace(day=1)
        new_kb = await SimpleCalendar().start_calendar(
            year=temp.year, month=temp.month
        )
        try:
            await callback.message.edit_reply_markup(
                reply_markup=_statistics_calendar_with_back(new_kb)
            )
        except TelegramBadRequest:
            pass
        return

    if act == SimpleCalendarAction.IGNORE:
        await callback.answer(cache_time=60)
        return

    # Выбор дня
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback, callback_data)
    if not selected or not date:
        return
    await callback.answer()
    date_str = date.strftime("%Y-%m-%d")
    current = await state.get_state()

    if current == StatisticsCustomPeriodStates.date_from.state:
        await state.update_data(statistics_date_from=date_str)
        await state.set_state(StatisticsCustomPeriodStates.date_to)
        calendar_kb = await SimpleCalendar().start_calendar(
            year=date.year, month=date.month
        )
        try:
            await callback.message.edit_text(
                "📊 <b>Свой период</b>\n\nВыберите <b>дату окончания</b> периода:",
                parse_mode=ParseMode.HTML,
                reply_markup=_statistics_calendar_with_back(calendar_kb),
                disable_web_page_preview=True,
            )
        except TelegramBadRequest:
            await callback.message.answer(
                "📊 <b>Свой период</b>\n\nВыберите <b>дату окончания</b> периода:",
                parse_mode=ParseMode.HTML,
                reply_markup=_statistics_calendar_with_back(calendar_kb),
                disable_web_page_preview=True,
            )
        return

    if current == QuestionnaireCustomPeriodStates.date_from.state:
        await state.update_data(statistics_date_from=date_str)
        await state.set_state(QuestionnaireCustomPeriodStates.date_to)
        calendar_kb = await SimpleCalendar().start_calendar(
            year=date.year, month=date.month
        )
        try:
            await callback.message.edit_text(
                "📋 <b>Детальная аналитика — свой период</b>\n\nВыберите <b>дату окончания</b> периода:",
                parse_mode=ParseMode.HTML,
                reply_markup=_statistics_calendar_with_back(calendar_kb),
                disable_web_page_preview=True,
            )
        except TelegramBadRequest:
            await callback.message.answer(
                "📋 <b>Детальная аналитика — свой период</b>\n\nВыберите <b>дату окончания</b> периода:",
                parse_mode=ParseMode.HTML,
                reply_markup=_statistics_calendar_with_back(calendar_kb),
                disable_web_page_preview=True,
            )
        return

    if current == ActionsCustomPeriodStates.date_from.state:
        await state.update_data(statistics_date_from=date_str)
        await state.set_state(ActionsCustomPeriodStates.date_to)
        calendar_kb = await SimpleCalendar().start_calendar(
            year=date.year, month=date.month
        )
        try:
            await callback.message.edit_text(
                "📊 <b>Отчёт по действиям — свой период</b>\n\nВыберите <b>дату окончания</b> периода:",
                parse_mode=ParseMode.HTML,
                reply_markup=_statistics_calendar_with_back(calendar_kb),
                disable_web_page_preview=True,
            )
        except TelegramBadRequest:
            await callback.message.answer(
                "📊 <b>Отчёт по действиям — свой период</b>\n\nВыберите <b>дату окончания</b> периода:",
                parse_mode=ParseMode.HTML,
                reply_markup=_statistics_calendar_with_back(calendar_kb),
                disable_web_page_preview=True,
            )
        return

    # state == date_to (любой из трёх отчётов)
    report_type = (
        "statistics"
        if current == StatisticsCustomPeriodStates.date_to.state
        else ("questionnaire" if current == QuestionnaireCustomPeriodStates.date_to.state else "actions")
    )
    data = await state.get_data()
    date_from_str = data.get("statistics_date_from")
    await state.clear()
    period_kb = (
        get_statistics_period_keyboard()
        if report_type == "statistics"
        else (get_questionnaire_period_keyboard() if report_type == "questionnaire" else get_period_selection_keyboard())
    )
    if not date_from_str:
        await callback.message.edit_text(
            "Ошибка: дата начала не найдена. Выберите период заново.",
            reply_markup=period_kb,
            disable_web_page_preview=True,
        )
        return
    date_to_str = date.strftime("%Y-%m-%d")
    d_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
    d_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
    if d_to < d_from:
        await callback.message.edit_text(
            "❌ Дата окончания не может быть раньше даты начала. Выберите период заново.",
            reply_markup=period_kb,
            disable_web_page_preview=True,
        )
        return

    def _fmt(d: str) -> str:
        parts = d.split("-")
        return f"{parts[2]}.{parts[1]}.{parts[0]}" if len(parts) == 3 else d

    period_name = f"{_fmt(date_from_str)} — {_fmt(date_to_str)}"

    if report_type == "statistics":
        from bot.services.statistics import get_statistics
        general_stats = await get_statistics(db)
        period_stats = await get_statistics(db, date_from=date_from_str, date_to=date_to_str)
        settings_repo = SettingsRepository(db)
        settings = await settings_repo.get_settings()
        criterion = getattr(settings, "stats_activated_criterion", "bot_entry")
        criterion_label = STATS_ACTIVATED_CRITERION_LABELS.get(criterion, "По /start")
        text = "📊 <b>Статистика бота</b>\n\n"
        text += "<b>Общая статистика:</b>\n"
        text += f"👥 Всего пользователей в боте: {general_stats['total_users']}\n"
        text += f"🟢 Активных пользователей: {general_stats['active_users']}\n"
        text += f"🔴 Заблокировавших бота: {general_stats['blocked_users']}\n"
        text += f"📨 Отправлено сообщений: {general_stats['messages_sent']}\n"
        text += f"\n<b>Свой период: {period_name}</b>\n"
        text += f"🟢 Активировали бота: {period_stats.get('activated_in_period', 0)} <i>({criterion_label})</i>\n"
        text += f"🔴 Заблокировали бота: {period_stats.get('blocked_in_period', 0)}\n"
        try:
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_statistics_custom_result_keyboard(),
                disable_web_page_preview=True,
            )
        except TelegramBadRequest:
            await callback.message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_statistics_custom_result_keyboard(),
                disable_web_page_preview=True,
            )
        return

    if report_type == "questionnaire":
        settings_repo = SettingsRepository(db)
        settings = await settings_repo.get_settings()
        crit = _normalized_stats_activated_criterion(settings)
        log_repo = UserActionLogRepository(db)
        stats = await log_repo.get_questionnaire_stats(
            date_from=date_from_str,
            date_to=date_to_str,
            activated_action_type=crit,
        )
        multiplier = 1.0 + (settings.adjustment_percent / 100.0)
        activated = int(stats.get("activated_count", 0) * multiplier)
        caption = _build_questionnaire_report_caption(
            activated=activated, period_name=period_name
        )
        try:
            await callback.message.delete()
        except Exception:
            pass
        image_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "analitics.png"
        )
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=FSInputFile(image_path),
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=get_questionnaire_custom_result_keyboard(),
        )
        return

    # report_type == "actions"
    log_repo = UserActionLogRepository(db)
    stats = await log_repo.get_simplified_actions_stats(date_from_str, date_to_str)
    if not stats:
        empty_text = (
            f"📊 <b>Отчёт по действиям: {period_name}</b>\n\n"
            "❌ За выбранный период действий не найдено."
        )
        try:
            await callback.message.edit_text(
                empty_text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_actions_custom_result_keyboard(),
            )
        except TelegramBadRequest:
            await callback.message.answer(
                empty_text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_actions_custom_result_keyboard(),
            )
        return
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    completed_percent = getattr(settings, "completed_percent", None)
    if (
        completed_percent is not None
        and 0 <= completed_percent <= 100
        and "bot_entry" in stats
        and "questionnaire_completed" in stats
    ):
        activated_unique = stats["bot_entry"]["unique_users"]
        override_completed = int(activated_unique * completed_percent / 100)
        stats["questionnaire_completed"] = {
            **stats["questionnaire_completed"],
            "total_actions": override_completed,
            "unique_users": override_completed,
        }
    text = f"📊 <b>Отчёт по действиям: {period_name}</b>\n\n"
    text += f"Период: {period_name}\n"
    text += "<i>События и уникальные пользователи только за этот период.</i>\n\n"
    main_actions = {}
    button_actions = {}
    for action_key, data_item in stats.items():
        if action_key.startswith("button_"):
            button_actions[action_key] = data_item
        else:
            main_actions[action_key] = data_item
    sorted_main = sorted(
        main_actions.items(),
        key=lambda x: x[1]["total_actions"],
        reverse=True,
    )
    sorted_buttons = sorted(
        button_actions.items(),
        key=lambda x: x[1]["total_actions"],
        reverse=True,
    )
    text += "<b>Статистика событий:</b>\n\n"
    for action_key, data_item in sorted_main:
        action_name = data_item["name"]
        total_actions = data_item["total_actions"]
        unique_users = data_item["unique_users"]
        text += f"• <b>{action_name}</b>\n"
        text += f"  📊 Событий: {total_actions}\n"
        text += f"  👥 Уникальных пользователей: {unique_users}\n\n"
    if sorted_buttons:
        text += "<b>Нажатия кнопок:</b>\n\n"
        for action_key, data_item in sorted_buttons[:10]:
            action_name = data_item["name"]
            total_actions = data_item["total_actions"]
            unique_users = data_item["unique_users"]
            text += f"• <b>{action_name}</b>\n"
            text += f"  📊 Событий: {total_actions}\n"
            text += f"  👥 Уникальных пользователей: {unique_users}\n\n"
    try:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_actions_custom_result_keyboard(),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_actions_custom_result_keyboard(),
        )


def _parse_statistics_period_callback(data: str) -> tuple[str, str, str | None]:
    """
    Парсит callback статистики: admin_statistics_period_today,
    admin_statistics_period_today_2025-01-28, admin_statistics_prev_today_2025-01-28, etc.
    """
    prefix = "admin_statistics_"
    if not data.startswith(prefix):
        return "period", "all", None
    suffix = data[len(prefix):]
    parts = suffix.split("_")
    if len(parts) < 2:
        return "period", "all", None
    direction = parts[0]
    period_type = parts[1]
    date_str = None
    if len(parts) >= 3 and len(parts[2]) == 10 and "-" in parts[2]:
        date_str = parts[2]
    return direction, period_type, date_str


@router.callback_query(
    F.data.startswith("admin_statistics_period_")
    | F.data.startswith("admin_statistics_prev_")
    | F.data.startswith("admin_statistics_next_")
)
async def admin_statistics_show(callback: CallbackQuery, db: Database) -> None:
    """Отображение статистики за выбранный период с навигацией −1/+1."""
    direction, period_type, date_str = _parse_statistics_period_callback(callback.data)
    date_from, date_to, period_name, base_date_str, was_future_capped = _compute_questionnaire_dates(
        direction, period_type, date_str
    )
    if was_future_capped:
        msg = (
            "Вы пытались посмотреть будущий период. Показаны данные за последние 7 дней."
            if period_type in ("week", "calweek")
            else "Вы пытались посмотреть будущий период. Показаны данные за последние 30 дней."
        )
        await callback.answer(msg, show_alert=True)
    else:
        await callback.answer()

    from bot.services.statistics import get_statistics
    # Всегда получаем общую статистику
    general_stats = await get_statistics(db)
    # Если период задан — получаем статистику за период
    if period_type == "all":
        period_stats = None
    else:
        period_stats = await get_statistics(db, date_from=date_from, date_to=date_to)

    text = "📊 <b>Статистика бота</b>\n\n"
    text += "<b>Общая статистика:</b>\n"
    text += f"👥 Всего пользователей в боте: {general_stats['total_users']}\n"
    text += f"🟢 Активных пользователей: {general_stats['active_users']}\n"
    text += f"🔴 Заблокировавших бота: {general_stats['blocked_users']}\n"
    text += f"📨 Отправлено сообщений: {general_stats['messages_sent']}\n"
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    criterion = getattr(settings, "stats_activated_criterion", "bot_entry")
    if period_stats is not None and (period_stats.get("activated_in_period") is not None or period_stats.get("blocked_in_period") is not None):
        period_label = "Календарная неделя" if period_type == "calweek" else "За период"
        text += f"\n<b>{period_label}: {period_name}</b>\n"
        criterion_label = STATS_ACTIVATED_CRITERION_LABELS.get(criterion, "По /start")
        text += f"🟢 Активировали бота: {period_stats.get('activated_in_period', 0)} <i>({criterion_label})</i>\n"
        text += f"🔴 Заблокировали бота: {period_stats.get('blocked_in_period', 0)}\n"
    nav_kb = get_statistics_nav_keyboard(period_type, base_date_str) if period_type != "all" else get_back_keyboard()
    if period_stats is not None and period_type != "all":
        nav_kb = InlineKeyboardMarkup(
            inline_keyboard=nav_kb.inline_keyboard + get_statistics_activated_criterion_row(criterion, period_type, base_date_str)
        )
    try:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=nav_kb,
            disable_web_page_preview=True
        )
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "message is not modified" in error_msg:
            await callback.answer()
        elif "no text" in error_msg or "message to edit" in error_msg:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=nav_kb,
                disable_web_page_preview=True
            )
        else:
            raise


@router.callback_query(F.data.startswith("admin_stats_act_"))
async def admin_statistics_activated_criterion_switch(callback: CallbackQuery, db: Database) -> None:
    """Переключение критерия «Активировали бота» в блоке Статистика."""
    suffix = callback.data.replace("admin_stats_act_", "")
    parts = suffix.split("_")
    if len(parts) < 3:
        await callback.answer("Ошибка", show_alert=True)
        return
    date_str = parts[-1] if len(parts[-1]) == 10 and "-" in parts[-1] else None
    period_type = parts[-2] if date_str else parts[-1]
    criterion = "_".join(parts[:-2]) if date_str else "_".join(parts[:-1])
    if criterion not in (
        "bot_entry",
        "questionnaire_started",
        "questionnaire_completed",
        "subscription_check_clicked",
    ):
        await callback.answer("Ошибка", show_alert=True)
        return
    if not date_str:
        await callback.answer()
        return
    base_date_str = date_str
    settings_repo = SettingsRepository(db)
    await settings_repo.set_stats_activated_criterion(criterion)
    await callback.answer("✅ Критерий обновлён", show_alert=True)
    date_from, date_to, period_name, _bd, _ = _compute_questionnaire_dates("period", period_type, base_date_str)
    from bot.services.statistics import get_statistics
    general_stats = await get_statistics(db)
    period_stats = await get_statistics(db, date_from=date_from, date_to=date_to)
    text = "📊 <b>Статистика бота</b>\n\n"
    text += "<b>Общая статистика:</b>\n"
    text += f"👥 Всего пользователей в боте: {general_stats['total_users']}\n"
    text += f"🟢 Активных пользователей: {general_stats['active_users']}\n"
    text += f"🔴 Заблокировавших бота: {general_stats['blocked_users']}\n"
    text += f"📨 Отправлено сообщений: {general_stats['messages_sent']}\n"
    settings = await settings_repo.get_settings()
    criterion_cur = getattr(settings, "stats_activated_criterion", "bot_entry")
    if period_stats is not None:
        period_label = "Календарная неделя" if period_type == "calweek" else "За период"
        text += f"\n<b>{period_label}: {period_name}</b>\n"
        criterion_label = STATS_ACTIVATED_CRITERION_LABELS.get(criterion_cur, "По /start")
        text += f"🟢 Активировали бота: {period_stats.get('activated_in_period', 0)} <i>({criterion_label})</i>\n"
        text += f"🔴 Заблокировали бота: {period_stats.get('blocked_in_period', 0)}\n"
    nav_kb = get_statistics_nav_keyboard(period_type, base_date_str)
    nav_kb = InlineKeyboardMarkup(
        inline_keyboard=nav_kb.inline_keyboard + get_statistics_activated_criterion_row(criterion_cur, period_type, base_date_str)
    )
    try:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=nav_kb,
            disable_web_page_preview=True
        )
    except TelegramBadRequest:
        pass


def _format_settings_text(settings) -> str:
    """Текст главного меню настроек: сводка по всем разделам."""
    sign = "+" if settings.adjustment_percent >= 0 else ""
    completed_str = (
        f"<b>{settings.completed_percent:.0f}%</b> от активировавших"
        if settings.completed_percent is not None else "по факту из логов"
    )
    mode = getattr(settings, "welcome_mode", "subscription_first")
    mode_map = {
        "subscription_first": "С проверкой подписки",
        "questionnaire_first": "Приветствие + анкета сначала",
        "no_questionnaire": "Без анкеты",
    }
    mode_str = mode_map.get(mode, "С проверкой подписки")
    return (
        "⚙️ <b>Настройки</b>\n\n"
        "🔀 <b>Режим приветствия</b>: " + mode_str + "\n"
        "📊 <b>Корректировка статистики</b>: " + f"{sign}{settings.adjustment_percent:.1f}%" + "\n"
        "✅ <b>«Заполнили» от «Активировали»</b>: " + completed_str + "\n\n"
        "Выберите раздел ниже."
    )


def _format_settings_mode_text(settings) -> str:
    """Текст подменю «Режим приветствия»."""
    mode = getattr(settings, "welcome_mode", "subscription_first")
    mode_map = {
        "subscription_first": "С проверкой подписки",
        "questionnaire_first": "Приветствие + анкета сначала",
        "no_questionnaire": "Без анкеты",
    }
    mode_str = mode_map.get(mode, "С проверкой подписки")
    return (
        "🔀 <b>Режим приветствия</b>\n\n"
        f"Сейчас: <b>{mode_str}</b>\n\n"
        "• <b>С подпиской</b>: приветствие с кнопкой проверки подписки.\n"
        "• <b>Анкета первой</b>: приветствие с кнопкой «Заполнить анкету», затем каналы и сообщение после анкеты.\n"
        "• <b>Без анкеты</b>: отдельное приветствие с кнопкой «Получить ссылку», после нажатия отправляется сообщение после анкеты."
    )


def _format_settings_adjustment_text(settings) -> str:
    """Текст подменю «Корректировка статистики»."""
    sign = "+" if settings.adjustment_percent >= 0 else ""
    return (
        "📊 <b>Процент корректировки статистики</b>\n\n"
        f"Текущее: <b>{sign}{settings.adjustment_percent:.1f}%</b>\n\n"
        "Диапазон от -100% до +100%."
    )


def _format_settings_completed_text(settings) -> str:
    """Текст подменю «Заполнили» от «Активировали»."""
    completed_str = (
        f"<b>{settings.completed_percent:.0f}%</b> от активировавших"
        if settings.completed_percent is not None else "по факту из логов"
    )
    return (
        "✅ <b>«Заполнили анкету» в Детальной аналитике</b>\n\n"
        f"Сейчас: {completed_str}\n\n"
        "Можно задать % от «Активировали бота» (0–100) или «По факту»."
    )


@router.callback_query(F.data == "admin_settings")
async def admin_settings_menu(callback: CallbackQuery, db: Database) -> None:
    """Главное меню настроек: три раздела (режим, корректировка, заполнили)."""
    await callback.answer()
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    await callback.message.edit_text(
        _format_settings_text(settings),
        reply_markup=get_settings_main_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_settings_section_mode")
async def admin_settings_section_mode(callback: CallbackQuery, db: Database) -> None:
    """Подменю настройки режима приветствия."""
    await callback.answer()
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    mode = getattr(settings, "welcome_mode", "subscription_first")
    await callback.message.edit_text(
        _format_settings_mode_text(settings),
        reply_markup=get_settings_mode_keyboard(mode),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_settings_section_adjustment")
async def admin_settings_section_adjustment(callback: CallbackQuery, db: Database) -> None:
    """Подменю корректировки процента статистики."""
    await callback.answer()
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    await callback.message.edit_text(
        _format_settings_adjustment_text(settings),
        reply_markup=get_settings_adjustment_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_settings_section_completed")
async def admin_settings_section_completed(callback: CallbackQuery, db: Database) -> None:
    """Подменю «Заполнили анкету» как % от «Активировали»."""
    await callback.answer()
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    await callback.message.edit_text(
        _format_settings_completed_text(settings),
        reply_markup=get_settings_completed_keyboard(settings.completed_percent),
        disable_web_page_preview=True
    )


@router.callback_query(
    F.data.in_(
        [
            "admin_welcome_mode_subscription",
            "admin_welcome_mode_questionnaire",
            "admin_welcome_mode_no_questionnaire",
        ]
    )
)
async def admin_welcome_mode_set(callback: CallbackQuery, db: Database) -> None:
    """Переключение режима приветствия."""
    mode_mapping = {
        "admin_welcome_mode_subscription": "subscription_first",
        "admin_welcome_mode_questionnaire": "questionnaire_first",
        "admin_welcome_mode_no_questionnaire": "no_questionnaire",
    }
    mode = mode_mapping.get(callback.data, "subscription_first")
    settings_repo = SettingsRepository(db)
    current = await settings_repo.get_settings()
    if getattr(current, "welcome_mode", "subscription_first") == mode:
        await callback.answer("Уже выбран этот режим", show_alert=True)
        return
    await settings_repo.set_welcome_mode(mode)
    settings = await settings_repo.get_settings()
    await callback.message.edit_text(
        _format_settings_mode_text(settings),
        reply_markup=get_settings_mode_keyboard(mode),
        disable_web_page_preview=True
    )
    await callback.answer("✅ Режим приветствия обновлён", show_alert=True)


def _format_flow_order_display(order: list[int]) -> str:
    """Текст текущего порядка для админки (только типы 1,2,3)."""
    return " → ".join(FLOW_STEP_NAMES.get(x, str(x)) for x in order)


def _flow_order_without_chain(flow_order: list[int]) -> list[int]:
    """Порядок без цепочки (4): только 1, 2, 3 для отображения в настройках."""
    return [x for x in flow_order if x != 4]


@router.callback_query(F.data == "admin_flow_order")
async def admin_flow_order_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню настройки порядка типов 1,2,3. Цепочка (4) всегда после /start, не настраивается."""
    await callback.answer()
    chain_repo = ChainMessageRepository(db)
    flow_order = await chain_repo.get_flow_order()
    order_display = _flow_order_without_chain(flow_order)
    text = (
        "📋 <b>Порядок сообщений для пользователя</b>\n\n"
        "Текущий порядок (что и когда получает пользователь):\n\n"
        f"<b>{_format_flow_order_display(order_display)}</b>\n\n"
        "Цепочка сообщений всегда запускается после /start и не настраивается здесь.\n\n"
        "Нажмите кнопку, чтобы поменять местами два соседних типа. "
        "Первый в списке отправляется сразу после /start (или после подписки, если первым идёт «Старт анкеты»)."
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_flow_order_keyboard(order_display),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("flow_order_swap_"))
async def admin_flow_order_swap(callback: CallbackQuery, db: Database) -> None:
    """Поменять местами два соседних типа в порядке из трёх (индексы 0–1 или 1–2). Цепочка (4) не участвует."""
    try:
        parts = callback.data.replace("flow_order_swap_", "").split("_")
        i, j = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка", show_alert=True)
        return
    if j != i + 1 or i not in (0, 1):
        await callback.answer("Недопустимый своп", show_alert=True)
        return
    chain_repo = ChainMessageRepository(db)
    flow_order = await chain_repo.get_flow_order()
    order_three = _flow_order_without_chain(flow_order)
    order_three[i], order_three[j] = order_three[j], order_three[i]
    await chain_repo.set_flow_order(order_three + [4])
    await callback.answer("✅ Порядок обновлён", show_alert=True)
    text = (
        "📋 <b>Порядок сообщений для пользователя</b>\n\n"
        "Текущий порядок:\n\n"
        f"<b>{_format_flow_order_display(order_three)}</b>\n\n"
        "Цепочка сообщений всегда запускается после /start и не настраивается здесь.\n\n"
        "Нажмите кнопку, чтобы поменять местами два соседних типа."
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_flow_order_keyboard(order_three),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("settings_percent_"))
async def admin_settings_set_percent(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    """Установка процента корректировки из предустановленных значений или начало ввода."""
    await callback.answer()
    
    callback_data = callback.data
    
    # Если это кнопка "Ввести значение"
    if callback_data == "settings_percent_custom":
        await state.set_state(SettingsStates.waiting_for_percent)
        await callback.message.edit_text(
            "✏️ <b>Ввод процента корректировки</b>\n\n"
            "Отправьте число от -100 до +100.\n\n"
            "Примеры: 5, -10, 25.5, -50\n\n"
            "Для отмены отправьте /cancel",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    # Извлекаем значение из callback_data (settings_percent_5, settings_percent_-5 и т.д.)
    try:
        percent_str = callback_data.replace("settings_percent_", "")
        percent = float(percent_str)
        
        # Проверка диапазона
        if percent < -100 or percent > 100:
            await callback.answer("Процент должен быть от -100 до +100", show_alert=True)
            return
        
        # Сохранение процента
        settings_repo = SettingsRepository(db)
        await settings_repo.update_adjustment_percent(percent)
        
        sign = "+" if percent >= 0 else ""
        await callback.answer(f"Процент установлен: {sign}{percent:.1f}%", show_alert=True)
        settings = await settings_repo.get_settings()
        await callback.message.edit_text(
            _format_settings_adjustment_text(settings),
            reply_markup=get_settings_adjustment_keyboard(),
            disable_web_page_preview=True
        )
    except ValueError:
        await callback.answer("Ошибка: неверное значение", show_alert=True)


@router.message(SettingsStates.waiting_for_percent)
async def admin_settings_custom_percent(message: Message, state: FSMContext, db: Database) -> None:
    """Обработка введённого процента корректировки."""
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    try:
        percent = float(message.text.strip())
        
        # Проверка диапазона
        if percent < -100 or percent > 100:
            await message.answer(
                "❌ Процент должен быть в диапазоне от -100 до +100.\n\n"
                "Попробуйте ещё раз или отправьте /cancel для отмены.",
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
            return
        
        settings_repo = SettingsRepository(db)
        await settings_repo.update_adjustment_percent(percent)
        settings = await settings_repo.get_settings()
        await state.clear()
        await message.answer(
            _format_settings_adjustment_text(settings),
            reply_markup=get_settings_adjustment_keyboard(),
            disable_web_page_preview=True
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Отправьте число от -100 до +100.\n\n"
            "Примеры: 5, -10, 25.5, -50\n\n"
            "Для отмены отправьте /cancel",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "completed_percent_off")
async def admin_completed_percent_off(callback: CallbackQuery, db: Database) -> None:
    """«Заполнили анкету» — по факту из логов."""
    settings_repo = SettingsRepository(db)
    await settings_repo.update_completed_percent(None)
    settings = await settings_repo.get_settings()
    await callback.answer("✅ «Заполнили анкету» теперь по факту из логов", show_alert=True)
    await callback.message.edit_text(
        _format_settings_completed_text(settings),
        reply_markup=get_settings_completed_keyboard(settings.completed_percent),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("completed_percent_"))
async def admin_completed_percent_set(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    """Установка «Заполнили анкету» как % от «Активировали» (кнопки или ввод своего)."""
    data = callback.data
    if data == "completed_percent_custom":
        await callback.answer()
        await state.set_state(SettingsStates.waiting_for_completed_percent)
        await callback.message.edit_text(
            "✏️ <b>«Заполнили анкету» как % от «Активировали бота»</b>\n\n"
            "Отправьте число от 0 до 100.\n"
            "Пример: 25 — тогда при 100 активировавших будет показано 25 заполнивших.\n\n"
            "Для отмены отправьте /cancel",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )
        return
    try:
        percent_str = data.replace("completed_percent_", "")
        percent = float(percent_str)
        if percent < 0 or percent > 100:
            await callback.answer("Процент должен быть от 0 до 100", show_alert=True)
            return
        settings_repo = SettingsRepository(db)
        await settings_repo.update_completed_percent(percent)
        settings = await settings_repo.get_settings()
        await callback.answer(f"✅ «Заполнили анкету» = {percent:.0f}% от «Активировали бота»", show_alert=True)
        await callback.message.edit_text(
            _format_settings_completed_text(settings),
            reply_markup=get_settings_completed_keyboard(settings.completed_percent),
            disable_web_page_preview=True
        )
    except ValueError:
        await callback.answer("Ошибка значения", show_alert=True)


@router.message(SettingsStates.waiting_for_completed_percent)
async def admin_completed_percent_custom(message: Message, state: FSMContext, db: Database) -> None:
    """Обработка введённого % для «Заполнили анкету» от «Активировали»."""
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    try:
        percent = float(message.text.strip())
        if percent < 0 or percent > 100:
            await message.answer(
                "❌ Процент должен быть от 0 до 100.\n\n"
                "Попробуйте ещё раз или отправьте /cancel.",
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
            return
        settings_repo = SettingsRepository(db)
        await settings_repo.update_completed_percent(percent)
        settings = await settings_repo.get_settings()
        await state.clear()
        await message.answer(
            _format_settings_completed_text(settings),
            reply_markup=get_settings_completed_keyboard(settings.completed_percent),
            disable_web_page_preview=True
        )
    except ValueError:
        await message.answer(
            "❌ Введите число от 0 до 100.\n\nДля отмены отправьте /cancel",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


# ========== Отчёты о действиях пользователей ==========

@router.callback_query(F.data == "admin_reports")
async def admin_reports_menu(callback: CallbackQuery, db: Database) -> None:
    """Меню отчётов о действиях пользователей."""
    await callback.answer()

    log_repo = UserActionLogRepository(db)
    total_count = len(await log_repo.get_all_logs(limit=10000))  # Примерное количество

    text = (
        f"📋 <b>Отчёты о действиях пользователей</b>\n\n"
        f"Всего записей в логах: {total_count}\n\n"
        f"Выберите тип отчёта:"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_reports_keyboard(),
            disable_web_page_preview=True
        )
    except TelegramBadRequest as e:
        if "no text" in str(e).lower() or "message to edit" in str(e).lower():
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                reply_markup=get_reports_keyboard()
            )
        else:
            raise


@router.callback_query(F.data == "admin_report_user")
async def admin_report_user_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало просмотра действий конкретного пользователя."""
    await callback.answer()
    await state.set_state(ReportStates.waiting_for_user_id)
    
    await callback.message.edit_text(
        "👤 <b>Действия пользователя</b>\n\n"
        "Отправьте Telegram ID пользователя или username (например: @username или 123456789).\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=get_back_keyboard(),
        disable_web_page_preview=True
    )


@router.message(ReportStates.waiting_for_user_id)
async def admin_report_user_process(message: Message, state: FSMContext, db: Database) -> None:
    """Обработка запроса действий пользователя."""
    
    if message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_admin_main_keyboard(), disable_web_page_preview=True)
        return
    
    try:
        user_id = None
        user_identifier = message.text.strip()
        
        # Если это username
        if user_identifier.startswith("@"):
            username = user_identifier[1:]
            user_repo = UserRepository(db)
            # Ищем пользователя по username
            all_users = await user_repo.get_all_users()
            user = next((u for u in all_users if u.username == username), None)
            if user:
                user_id = user.user_id
            else:
                await message.answer(
                    f"❌ Пользователь с username {user_identifier} не найден.",
                    reply_markup=get_back_keyboard(),
                    disable_web_page_preview=True
                )
                return
        # Если это ID
        elif user_identifier.isdigit():
            user_id = int(user_identifier)
        else:
            await message.answer(
                "❌ Неверный формат. Отправьте Telegram ID (число) или username (@username).",
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
            return
        
        # Получаем логи пользователя
        log_repo = UserActionLogRepository(db)
        logs = await log_repo.get_user_logs(user_id, limit=50)
        
        if not logs:
            await message.answer(
                f"❌ Действия пользователя {user_id} не найдены.",
                reply_markup=get_reports_keyboard()
            )
            await state.clear()
            return
        
        # Получаем информацию о пользователе
        user_repo = UserRepository(db)
        user = await user_repo.get_user(user_id)
        user_name = user.full_name if user else f"ID: {user_id}"
        
        # Формируем отчёт
        from datetime import datetime
        
        text = f"👤 <b>Действия пользователя: {user_name}</b>\n\n"
        text += f"Всего действий: {len(logs)}\n\n"
        
        # Группируем по типам действий
        action_types = {}
        for log in logs:
            action_type = log.action_type
            action_types[action_type] = action_types.get(action_type, 0) + 1
        
        text += "<b>Статистика по типам:</b>\n"
        for action_type, count in sorted(action_types.items(), key=lambda x: x[1], reverse=True):
            text += f"• {action_type}: {count}\n"
        
        text += "\n<b>Последние действия:</b>\n\n"
        
        for i, log in enumerate(logs[:20], 1):
            log_time = datetime.strptime(log.created_at, "%Y-%m-%d %H:%M:%S").strftime("%d.%m %H:%M")
            text += f"{i}. <b>{log.action_type}</b> - {log_time}\n"
            if log.message_text:
                preview = log.message_text[:50] + "..." if len(log.message_text) > 50 else log.message_text
                text += f"   Текст: {preview}\n"
            if log.callback_data:
                text += f"   Callback: {log.callback_data}\n"
            text += "\n"
        
        if len(logs) > 20:
            text += f"\n... и еще {len(logs) - 20} действий"
        
        await message.answer(text, reply_markup=get_reports_keyboard(), disable_web_page_preview=True)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при получении отчёта о пользователе: {e}")
        await message.answer(
            f"❌ Ошибка: {e}",
            reply_markup=get_back_keyboard(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == "admin_report_summary")
async def admin_report_summary(callback: CallbackQuery, db: Database) -> None:
    """Сводка активности пользователей."""
    await callback.answer()
    
    log_repo = UserActionLogRepository(db)
    summary = await log_repo.get_users_activity_summary(limit=20)
    
    if not summary:
        await callback.message.answer(
            "❌ Нет данных о действиях пользователей.",
            reply_markup=get_reports_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    from datetime import datetime
    
    text = "📊 <b>Сводка активности пользователей</b>\n\n"
    text += "Топ-20 самых активных пользователей:\n\n"
    
    for i, user_info in enumerate(summary, 1):
        username = user_info["username"] or "Без username"
        full_name = user_info["full_name"] or "Без имени"
        actions = user_info["actions_count"]
        last_action = user_info["last_action"]
        
        if last_action:
            try:
                last_dt = datetime.strptime(last_action, "%Y-%m-%d %H:%M:%S")
                last_formatted = last_dt.strftime("%d.%m.%Y %H:%M")
            except:
                last_formatted = last_action
        else:
            last_formatted = "Нет действий"
        
        text += f"{i}. <b>{full_name}</b> (@{username})\n"
        text += f"   Действий: {actions} | Последнее: {last_formatted}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_reports_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_report_stats")
async def admin_report_stats(callback: CallbackQuery, db: Database) -> None:
    """Статистика действий."""
    await callback.answer()
    
    log_repo = UserActionLogRepository(db)
    stats = await log_repo.get_user_activity_stats()
    
    if not stats or stats.get("total", 0) == 0:
        await callback.message.answer(
            "❌ Нет данных о действиях.",
            reply_markup=get_reports_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    text = "📈 <b>Статистика действий</b>\n\n"
    text += f"Всего действий: <b>{stats.get('total', 0)}</b>\n\n"
    text += "<b>По типам действий:</b>\n"
    
    # Сортируем по количеству
    sorted_stats = sorted(
        [(k, v) for k, v in stats.items() if k != "total"],
        key=lambda x: x[1],
        reverse=True
    )
    
    for action_type, count in sorted_stats:
        percentage = (count / stats["total"] * 100) if stats["total"] > 0 else 0
        text += f"• <b>{action_type}</b>: {count} ({percentage:.1f}%)\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_reports_keyboard(),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "admin_report_questionnaire_stats")
async def admin_report_questionnaire_stats(callback: CallbackQuery) -> None:
    """Выбор периода для Детальной аналитики."""
    await callback.answer()
    text = (
        "📋 <b>Детальная аналитика</b>\n\n"
        "Выберите период для отчёта:"
    )
    try:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_questionnaire_period_keyboard(),
            disable_web_page_preview=True
        )
    except TelegramBadRequest as e:
        if "no text" in str(e).lower() or "message to edit" in str(e).lower():
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_questionnaire_period_keyboard()
            )
        else:
            raise


@router.callback_query(F.data == "admin_report_questionnaire_period_custom")
async def admin_report_questionnaire_custom_start(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Свой период для Детальной аналитики: показ календаря даты начала."""
    await callback.answer()
    await state.set_state(QuestionnaireCustomPeriodStates.date_from)
    calendar_kb = await SimpleCalendar().start_calendar()
    await callback.message.edit_text(
        "📋 <b>Детальная аналитика — свой период</b>\n\nВыберите <b>дату начала</b> периода:",
        parse_mode=ParseMode.HTML,
        reply_markup=_statistics_calendar_with_back(calendar_kb),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "admin_report_actions_period_custom")
async def admin_report_actions_custom_start(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Свой период для Отчёта по действиям: показ календаря даты начала."""
    await callback.answer()
    await state.set_state(ActionsCustomPeriodStates.date_from)
    calendar_kb = await SimpleCalendar().start_calendar()
    await callback.message.edit_text(
        "📊 <b>Отчёт по действиям — свой период</b>\n\nВыберите <b>дату начала</b> периода:",
        parse_mode=ParseMode.HTML,
        reply_markup=_statistics_calendar_with_back(calendar_kb),
        disable_web_page_preview=True,
    )


def _normalized_stats_activated_criterion(settings: Any) -> str:
    """Тот же критерий «Активировали», что в get_statistics."""
    criterion = getattr(settings, "stats_activated_criterion", "bot_entry")
    if criterion not in (
        "bot_entry",
        "questionnaire_started",
        "questionnaire_completed",
        "subscription_check_clicked",
    ):
        criterion = "bot_entry"
    return criterion


def _build_questionnaire_report_caption(
    activated: int,
    period_name: str,
) -> str:
    """Подпись к отчёту «Детальная аналитика» (критерий счёта — из настроек stats_activated_criterion)."""
    return (
        "📋 <b>Детальная аналитика</b>\n"
        f"<i>{period_name}</i>\n\n"
        f"👥 Активировали бота: <b>{activated}</b>\n"
        "   (уникальных пользователей)\n"
    )


def _parse_questionnaire_period_callback(data: str) -> tuple[str, str, str | None]:
    """
    Парсит callback: admin_report_questionnaire_period_today,
    admin_report_questionnaire_period_today_2025-01-28,
    admin_report_questionnaire_prev_today_2025-01-28, admin_report_questionnaire_next_week_2025-01-22, etc.
    Returns: (direction, period_type, date_str) где direction in ("period", "prev", "next"), period_type in ("today", "week", "month", "all"), date_str YYYY-MM-DD или None.
    """
    prefix = "admin_report_questionnaire_"
    if not data.startswith(prefix):
        return "period", "all", None
    suffix = data[len(prefix):]  # period_today, prev_today_2025-01-28, ...
    parts = suffix.split("_")
    if len(parts) < 2:
        return "period", "all", None
    direction = parts[0]  # period, prev, next
    period_type = parts[1]  # today, week, month, all
    date_str = None
    if len(parts) >= 3 and len(parts[2]) == 10 and "-" in parts[2]:
        date_str = parts[2]
    return direction, period_type, date_str


def _compute_questionnaire_dates(
    direction: str,
    period_type: str,
    date_str: str | None,
) -> tuple[str | None, str, str, str, bool]:
    """
    Возвращает (date_from, date_to, period_name, base_date_str, was_future_capped).
    was_future_capped: True, если запрошен будущий период и показаны последние 7/30 дней.
    """
    from datetime import datetime, timedelta

    today = datetime.now().date()

    def _fmt(d: str) -> str:
        if not d:
            return ""
        parts = d.split("-")
        return f"{parts[2]}.{parts[1]}.{parts[0]}" if len(parts) == 3 else d

    date_to_fmt = _fmt(today.strftime("%Y-%m-%d"))

    if period_type == "all":
        return None, today.strftime("%Y-%m-%d"), f"За всё время (по {date_to_fmt})", "", False

    def _parse_date(s: str | None):
        if not s:
            return today
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return today

    if period_type == "today":
        if direction == "period" and not date_str:
            base = today
        else:
            base = _parse_date(date_str)
            if direction == "prev":
                base = base - timedelta(days=1)
            elif direction == "next":
                base = base + timedelta(days=1)
        base = min(base, today)
        d_str = base.strftime("%Y-%m-%d")
        return d_str, d_str, f"{_fmt(d_str)} — {_fmt(d_str)}", d_str, False

    # Календарная неделя: понедельник–воскресенье.
    # Для текущей недели (если выбран период "сейчас") показываем с понедельника по сегодня.
    if period_type == "calweek":
        current_monday = today - timedelta(days=today.weekday())  # Monday=0
        if direction == "period" and not date_str:
            base = current_monday
        else:
            base = _parse_date(date_str)
            if direction == "prev":
                base = base - timedelta(days=7)
            elif direction == "next":
                base = base + timedelta(days=7)

        was_future = base > current_monday
        if was_future:
            base = current_monday

        date_from = base
        if base == current_monday:
            date_to = today
        else:
            date_to = base + timedelta(days=6)

        df = date_from.strftime("%Y-%m-%d")
        dt = date_to.strftime("%Y-%m-%d")
        return df, dt, f"{_fmt(df)} — {_fmt(dt)}", df, was_future

    if period_type == "week":
        if direction == "period" and not date_str:
            base = today - timedelta(days=6)
        else:
            base = _parse_date(date_str)
            if direction == "prev":
                base = base - timedelta(days=7)
            elif direction == "next":
                base = base + timedelta(days=7)
        date_from = base
        date_to = min(base + timedelta(days=6), today)
        was_future = date_from > today
        if was_future:
            date_from = today - timedelta(days=6)
            date_to = today
        df = date_from.strftime("%Y-%m-%d")
        dt = date_to.strftime("%Y-%m-%d")
        return df, dt, f"{_fmt(df)} — {_fmt(dt)}", df, was_future

    if period_type == "month":
        if direction == "period" and not date_str:
            base = today - timedelta(days=29)
        else:
            base = _parse_date(date_str)
            if direction == "prev":
                base = base - timedelta(days=30)
            elif direction == "next":
                base = base + timedelta(days=30)
        date_from = base
        date_to = min(base + timedelta(days=29), today)
        was_future = date_from > today
        if was_future:
            date_from = today - timedelta(days=29)
            date_to = today
        df = date_from.strftime("%Y-%m-%d")
        dt = date_to.strftime("%Y-%m-%d")
        return df, dt, f"{_fmt(df)} — {_fmt(dt)}", df, was_future

    return None, today.strftime("%Y-%m-%d"), f"За всё время (по {date_to_fmt})", "", False


@router.callback_query(
    F.data.startswith("admin_report_questionnaire_period_")
    | F.data.startswith("admin_report_questionnaire_prev_")
    | F.data.startswith("admin_report_questionnaire_next_")
)
async def admin_report_questionnaire_show(callback: CallbackQuery, bot: Bot, db: Database) -> None:
    """Отображение Детальной аналитики за выбранный период с навигацией −1/+1."""
    direction, period_type, date_str = _parse_questionnaire_period_callback(callback.data)
    date_from, date_to, period_name, base_date_str, was_future_capped = _compute_questionnaire_dates(
        direction, period_type, date_str
    )
    if was_future_capped:
        msg = (
            "Вы пытались посмотреть будущий период. Показаны данные за последние 7 дней."
            if period_type in ("week", "calweek")
            else "Вы пытались посмотреть будущий период. Показаны данные за последние 30 дней."
        )
        await callback.answer(msg, show_alert=True)
    else:
        await callback.answer()

    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    crit = _normalized_stats_activated_criterion(settings)
    log_repo = UserActionLogRepository(db)
    stats = await log_repo.get_questionnaire_stats(
        date_from=date_from, date_to=date_to, activated_action_type=crit
    )
    activated_raw = stats.get("activated_count", 0)
    completed_raw = stats.get("completed_count", 0)

    adjustment_percent = settings.adjustment_percent
    completed_percent = settings.completed_percent

    multiplier = 1.0 + (adjustment_percent / 100.0)
    activated = int(activated_raw * multiplier)

    if completed_percent is not None and 0 <= completed_percent <= 100:
        completed = int(activated * completed_percent / 100)
        completed_note = " (уникальных пользователей)"
    else:
        completed = int(completed_raw * multiplier)
        completed_note = " (уникальных пользователей)"

    caption = _build_questionnaire_report_caption(
        activated=activated, period_name=period_name
    )

    if period_type == "all":
        nav_kb = get_questionnaire_period_keyboard()
    else:
        nav_kb = get_questionnaire_nav_keyboard(period_type, base_date_str)

    try:
        await callback.message.delete()
    except Exception:
        pass

    image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "analitics.png")
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=FSInputFile(image_path),
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=nav_kb
    )


@router.callback_query(F.data == "admin_report_all")
async def admin_report_all(callback: CallbackQuery, db: Database) -> None:
    """Просмотр всех логов."""
    await callback.answer()
    
    log_repo = UserActionLogRepository(db)
    logs = await log_repo.get_all_logs(limit=30)
    
    if not logs:
        await callback.message.answer(
            "❌ Логи не найдены.",
            reply_markup=get_reports_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    from datetime import datetime
    
    text = "📋 <b>Последние действия пользователей</b>\n\n"
    
    for i, log in enumerate(logs, 1):
        log_time = datetime.strptime(log.created_at, "%Y-%m-%d %H:%M:%S").strftime("%d.%m %H:%M")
        text += f"{i}. <b>Пользователь {log.user_id}</b> - {log.action_type}\n"
        text += f"   Время: {log_time}\n"
        if log.message_text:
            preview = log.message_text[:40] + "..." if len(log.message_text) > 40 else log.message_text
            text += f"   Текст: {preview}\n"
        if log.callback_data:
            text += f"   Callback: {log.callback_data}\n"
        text += "\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_reports_keyboard(),
        disable_web_page_preview=True
    )


# ========== Отчёт по уникальным действиям за период ==========

@router.callback_query(F.data == "admin_report_actions")
async def admin_report_actions_period(callback: CallbackQuery) -> None:
    """Выбор периода для отчёта по действиям."""
    await callback.answer()
    
    text = (
        "📊 <b>Отчёт по уникальным действиям</b>\n\n"
        "Выберите период для отчёта:"
    )
    try:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_period_selection_keyboard(),
            disable_web_page_preview=True
        )
    except TelegramBadRequest as e:
        if "no text" in str(e).lower() or "message to edit" in str(e).lower():
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_period_selection_keyboard()
            )
        else:
            raise


def _parse_actions_period_callback(data: str) -> tuple[str, str, str | None]:
    """
    Парсит callback отчёта по действиям: admin_report_period_today,
    admin_report_period_today_2025-01-28, admin_report_prev_today_2025-01-28, admin_report_next_week_2025-01-22.
    Returns: (direction, period_type, date_str).
    """
    prefix = "admin_report_"
    if not data.startswith(prefix):
        return "period", "all", None
    suffix = data[len(prefix):]
    parts = suffix.split("_")
    if len(parts) < 2:
        return "period", "all", None
    direction = parts[0]
    period_type = parts[1]
    date_str = None
    if len(parts) >= 3 and len(parts[2]) == 10 and "-" in parts[2]:
        date_str = parts[2]
    return direction, period_type, date_str


@router.callback_query(
    F.data.startswith("admin_report_period_")
    | F.data.startswith("admin_report_prev_")
    | F.data.startswith("admin_report_next_")
)
async def admin_report_actions_show(callback: CallbackQuery, db: Database) -> None:
    """Отображение отчёта по действиям за выбранный период с навигацией −1/+1."""
    direction, period_type, date_str = _parse_actions_period_callback(callback.data)
    date_from, date_to, period_name, base_date_str, was_future_capped = _compute_questionnaire_dates(
        direction, period_type, date_str
    )
    if was_future_capped:
        msg = (
            "Вы пытались посмотреть будущий период. Показаны данные за последние 7 дней."
            if period_type in ("week", "calweek")
            else "Вы пытались посмотреть будущий период. Показаны данные за последние 30 дней."
        )
        await callback.answer(msg, show_alert=True)
    else:
        await callback.answer()

    log_repo = UserActionLogRepository(db)
    stats = await log_repo.get_simplified_actions_stats(date_from, date_to)

    if period_type == "all":
        nav_kb = get_period_selection_keyboard()
    else:
        nav_kb = get_actions_nav_keyboard(period_type, base_date_str)

    if not stats:
        empty_text = (
            f"📊 <b>Отчёт по действиям: {period_name}</b>\n\n"
            "❌ За выбранный период действий не найдено."
        )
        try:
            await callback.message.edit_text(
                empty_text,
                parse_mode=ParseMode.HTML,
                reply_markup=nav_kb
            )
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            if "no text" in error_msg or "message to edit" in error_msg:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(
                    empty_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=nav_kb
                )
            elif "message is not modified" in error_msg:
                pass
            else:
                raise
        return

    # Настройка «Заполнили анкету» как % от «Активировали»
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    completed_percent = getattr(settings, "completed_percent", None)
    if completed_percent is not None and 0 <= completed_percent <= 100 and "bot_entry" in stats and "questionnaire_completed" in stats:
        activated_unique = stats["bot_entry"]["unique_users"]
        override_completed = int(activated_unique * completed_percent / 100)
        stats["questionnaire_completed"] = {
            **stats["questionnaire_completed"],
            "total_actions": override_completed,
            "unique_users": override_completed,
        }

    text = f"📊 <b>Отчёт по действиям: {period_name}</b>\n\n"
    if date_from:
        text += f"Период: {period_name}\n"
        text += "<i>События и уникальные пользователи только за этот период.</i>\n\n"
    else:
        text += "Период: всё время\n\n"

    main_actions = {}
    button_actions = {}
    for action_key, data in stats.items():
        if action_key.startswith("button_"):
            button_actions[action_key] = data
        else:
            main_actions[action_key] = data

    sorted_main = sorted(
        main_actions.items(),
        key=lambda x: x[1]["total_actions"],
        reverse=True
    )
    sorted_buttons = sorted(
        button_actions.items(),
        key=lambda x: x[1]["total_actions"],
        reverse=True
    )

    text += "<b>Статистика событий:</b>\n\n"
    for action_key, data in sorted_main:
        action_name = data["name"]
        total_actions = data["total_actions"]
        unique_users = data["unique_users"]
        text += f"• <b>{action_name}</b>\n"
        text += f"  📊 Событий: {total_actions}\n"
        text += f"  👥 Уникальных пользователей: {unique_users}\n\n"

    if sorted_buttons:
        text += "<b>Нажатия кнопок:</b>\n\n"
        for action_key, data in sorted_buttons[:10]:
            action_name = data["name"]
            total_actions = data["total_actions"]
            unique_users = data["unique_users"]
            text += f"• <b>{action_name}</b>\n"
            text += f"  📊 Событий: {total_actions}\n"
            text += f"  👥 Уникальных пользователей: {unique_users}\n\n"

    try:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=nav_kb
        )
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "no text" in error_msg or "message to edit" in error_msg:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=nav_kb, disable_web_page_preview=True)
        elif "message is not modified" in error_msg:
            pass
        else:
            raise
