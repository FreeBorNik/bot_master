"""Общие обработчики."""
import asyncio
from urllib.parse import parse_qs, unquote_plus

from aiogram import Router, Bot
from aiogram.types import Message, ChatJoinRequest, ChatMemberUpdated
from aiogram.filters import Command, CommandStart, ChatMemberUpdatedFilter
from aiogram.filters.chat_member_updated import IS_MEMBER, IS_NOT_MEMBER
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from bot.database.db import Database
from bot.database.repositories import (
    UserRepository,
    StartMessageRepository,
    WelcomeMessageRepository,
    ChainMessageRepository,
    SettingsRepository,
    SimpleWelcomeMessageRepository,
    NoQuestionnaireMessageRepository,
)
from bot.database.action_logs_repository import UserActionLogRepository
from bot.keyboards.user_kb import (
    get_subscription_check_keyboard,
    get_fill_questionnaire_keyboard,
    get_no_questionnaire_keyboard,
)
from bot.utils.helpers import parse_entities_from_json, apply_welcome_placeholders
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)

router = Router(name="common")

UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")


def _parse_start_param_and_utm(full_command: str) -> tuple[str | None, dict[str, str]]:
    """
    Извлекает start_param и UTM из текста команды /start.
    Примеры: /start ref123, /start utm_source=google&utm_medium=cpc
    Возвращает (start_param_raw, utm_dict).
    """
    if not full_command or not full_command.strip().lower().startswith("/start"):
        return None, {}
    raw = full_command.strip()[6:].strip()  # после "/start"
    if not raw:
        return None, {}
    utm: dict[str, str] = {}
    # Пробуем разобрать как query-строку (utm_source=x&utm_medium=y)
    if "=" in raw:
        try:
            parsed = parse_qs(raw, keep_blank_values=False)
            for key in UTM_KEYS:
                if key in parsed and parsed[key]:
                    val = parsed[key][0]
                    if isinstance(val, str):
                        utm[key] = unquote_plus(val).strip()
        except Exception:
            pass
    # Один параметр без "=" можно записать как start_param
    start_param = raw if raw else None
    return start_param, utm


@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_NOT_MEMBER)
)
async def on_my_chat_member_left(event: ChatMemberUpdated, db: Database) -> None:
    """
    Пользователь заблокировал бота или вышел из чата (обновление статуса бота в чате).
    В личке chat.id == user_id. Помечаем is_in_bot=False.
    """
    logger.debug(
        "my_chat_member: chat_id=%s type=%s old=%s new=%s",
        event.chat.id,
        event.chat.type,
        getattr(event.old_chat_member, "status", None),
        getattr(event.new_chat_member, "status", None),
    )
    if event.chat.type != "private":
        return
    user_id = event.chat.id
    try:
        user_repo = UserRepository(db)
        await user_repo.update_user_is_in_bot(user_id, False)
        log_repo = UserActionLogRepository(db)
        await log_repo.create_log(
            user_id=user_id,
            action_type="bot_blocked",
            message_text="Заблокировал бота",
            action_data={"source": "my_chat_member", "new_status": event.new_chat_member.status},
        )
        logger.info(f"Пользователь {user_id} заблокировал бота (my_chat_member), is_in_bot=0")
    except Exception as e:
        logger.warning(f"Не удалось обновить is_in_bot для {user_id}: {e}")


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, bot: Bot, state: FSMContext, command: CommandStart) -> None:
    """
    Обработчик команды /start.
    
    Args:
        message: Объект сообщения
        db: База данных
        bot: Экземпляр бота
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    # Получаем полный текст команды для логирования
    full_command = message.text or ""
    logger.info(f"Пользователь {user_id} вызвал команду: {full_command}")
    
    # Создание/обновление пользователя; при возврате после блокировки (is_in_bot=False) — полный стартовый алгоритм заново
    user_repo = UserRepository(db)
    existing_user = await user_repo.get_user(user_id)
    is_new_user = existing_user is None
    is_returned_after_block = existing_user is not None and not getattr(existing_user, "is_in_bot", True)
    await user_repo.create_user(user_id, username, full_name)

    if is_returned_after_block:
        await state.clear()
        await user_repo.clear_questionnaire(user_id)

    # Детальное логирование входа в бот (start_param и UTM из ссылки t.me/bot?start=...)
    start_param, utm = _parse_start_param_and_utm(full_command)
    action_data: dict = {
        "command": "/start",
        "is_new_user": is_new_user,
        "is_returned_after_block": is_returned_after_block,
        "username": username,
        "full_name": full_name,
    }
    if start_param is not None:
        action_data["start_param"] = start_param
    if utm:
        action_data["utm"] = utm
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=user_id,
        action_type="bot_entry",
        message_text="Зашёл в бот",
        action_data=action_data,
    )
    
    # Отправляем сообщение после /start, если оно включено (самое первое)
    start_repo = StartMessageRepository(db)
    start_msg = await start_repo.get_start_message()
    if start_msg and start_msg.text and start_msg.is_active:
        first_name = message.from_user.first_name or ""
        full_name = message.from_user.full_name or ""
        username = message.from_user.username
        text_with_name, entities = apply_welcome_placeholders(
            start_msg.text,
            first_name=first_name,
            full_name=full_name,
            username=username,
            entities=parse_entities_from_json(start_msg.entities_json),
        )
        if entities:
            await message.answer(
                text_with_name,
                entities=entities,
                parse_mode=None,
                disable_web_page_preview=True,
            )
        else:
            await message.answer(
                text_with_name,
                disable_web_page_preview=True,
            )

    # Режим «приветствие + анкета первой»: своё приветствие и кнопка «Заполнить анкету», без проверки подписки
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    if getattr(settings, "welcome_mode", "subscription_first") == "questionnaire_first":
        # Цепочка запускается после «Сообщения после анкеты», т.е. после нажатия «Проверить подписку»
        simple_repo = SimpleWelcomeMessageRepository(db)
        simple_msg = await simple_repo.get_simple_welcome_message()
        first_name = message.from_user.first_name or ""
        full_name = message.from_user.full_name or ""
        username = message.from_user.username
        if simple_msg and simple_msg.text and simple_msg.is_active:
            text_with_name, entities = apply_welcome_placeholders(
                simple_msg.text,
                first_name=first_name,
                full_name=full_name,
                username=username,
                entities=parse_entities_from_json(simple_msg.entities_json),
            )
            if entities:
                await message.answer(
                    text_with_name,
                    entities=entities,
                    parse_mode=None,
                    reply_markup=get_fill_questionnaire_keyboard(),
                    disable_web_page_preview=True,
                )
            else:
                await message.answer(
                    text_with_name,
                    reply_markup=get_fill_questionnaire_keyboard(),
                    disable_web_page_preview=True,
                )
        else:
            await message.answer(
                "👋 Добро пожаловать! Нажмите кнопку ниже, чтобы заполнить анкету.",
                reply_markup=get_fill_questionnaire_keyboard(),
                disable_web_page_preview=True,
            )
        return

    # Режим «без анкеты»: сообщение администратора + кнопка «Получить ссылку»,
    # затем пользователь получает сообщение после анкеты по нажатию кнопки.
    if getattr(settings, "welcome_mode", "subscription_first") == "no_questionnaire":
        no_q_repo = NoQuestionnaireMessageRepository(db)
        no_q_msg = await no_q_repo.get_no_questionnaire_message()
        first_name = message.from_user.first_name or ""
        full_name = message.from_user.full_name or ""
        username = message.from_user.username
        if no_q_msg and no_q_msg.text and no_q_msg.is_active:
            text_with_name, entities = apply_welcome_placeholders(
                no_q_msg.text,
                first_name=first_name,
                full_name=full_name,
                username=username,
                entities=parse_entities_from_json(no_q_msg.entities_json),
            )
            if entities:
                await message.answer(
                    text_with_name,
                    entities=entities,
                    parse_mode=None,
                    reply_markup=get_no_questionnaire_keyboard(),
                    disable_web_page_preview=True,
                )
            else:
                await message.answer(
                    text_with_name,
                    reply_markup=get_no_questionnaire_keyboard(),
                    disable_web_page_preview=True,
                )
        else:
            await message.answer(
                "👋 Добро пожаловать!\n\nНажмите кнопку ниже, чтобы продолжить.",
                reply_markup=get_no_questionnaire_keyboard(),
                disable_web_page_preview=True,
            )
        from bot.handlers.user_router import send_chain_messages
        asyncio.create_task(send_chain_messages(bot, user_id, db))
        return

    # Порядок типов: 1=Приветствие, 2=Старт анкеты, 3=Сообщение после анкеты, 4=Цепочка
    # Цепочка всегда запускается при /start отдельно; первый шаг для пользователя — только 1, 2 или 3
    from bot.handlers.user_router import send_chain_messages
    chain_repo = ChainMessageRepository(db)
    flow_order = await chain_repo.get_flow_order()
    first_step = next((x for x in (flow_order or [1]) if x in (1, 2, 3)), 1)

    if first_step == 2:
        # Первый шаг — анкета: показываем анкету сразу, без проверки подписки (кнопка только в приветствии)
        from bot.handlers.user_router import start_questionnaire_at_start
        asyncio.create_task(send_chain_messages(bot, user_id, db))
        await start_questionnaire_at_start(bot, user_id, db, state, message)
        return

    if first_step == 3:
        from bot.handlers.user_router import send_post_questionnaire_message
        asyncio.create_task(send_chain_messages(bot, user_id, db))
        await send_post_questionnaire_message(bot, user_id, db)
        return

    # first_step == 1: Приветствие с кнопкой проверки подписки
    welcome_repo = WelcomeMessageRepository(db)
    welcome_msg = await welcome_repo.get_welcome_message()
    first_name = message.from_user.first_name or ""
    full_name = message.from_user.full_name or ""
    username = message.from_user.username

    if welcome_msg and welcome_msg.text:
        text_with_name, entities = apply_welcome_placeholders(
            welcome_msg.text,
            first_name=first_name,
            full_name=full_name,
            username=username,
            entities=parse_entities_from_json(welcome_msg.entities_json),
        )
        if entities:
            await message.answer(
                text_with_name,
                reply_markup=get_subscription_check_keyboard(),
                entities=entities,
                parse_mode=None,
                disable_web_page_preview=True,
            )
        else:
            await message.answer(
                text_with_name,
                reply_markup=get_subscription_check_keyboard(),
                disable_web_page_preview=True,
            )
    else:
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для продолжения подпишитесь на каналы и нажмите кнопку ниже.",
            reply_markup=get_subscription_check_keyboard(),
            disable_web_page_preview=True,
        )
    asyncio.create_task(send_chain_messages(bot, user_id, db))


@router.message(Command("help"))
async def cmd_help(message: Message, db: Database) -> None:
    """
    Обработчик команды /help.
    
    Args:
        message: Объект сообщения
        db: База данных
    """
    # Логирование запроса помощи
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=message.from_user.id,
        action_type="help_request",
        message_text="Запросил помощь",
        action_data={"command": "/help"}
    )
    
    await message.answer("Список доступных команд:\n/start - Начать работу с ботом")


@router.message(Command("cancel"))
async def cmd_cancel_user(message: Message, state: FSMContext, db: Database) -> None:
    """
    Обработчик команды /cancel для пользователей - отмена заполнения анкеты.
    
    Args:
        message: Объект сообщения
        state: FSM контекст
        db: База данных
    """
    current_state = await state.get_state()
    was_in_questionnaire = current_state and "questionnaire" in str(current_state).lower()
    
    # Логирование отмены действия
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=message.from_user.id,
        action_type="cancel_action",
        message_text="Отменил действие" + (" (анкета)" if was_in_questionnaire else ""),
        action_data={
            "command": "/cancel",
            "was_in_questionnaire": was_in_questionnaire,
            "previous_state": str(current_state) if current_state else None
        }
    )
    
    await state.clear()
    await message.answer("❌ Заполнение анкеты отменено.\n\nИспользуйте /start для начала работы с ботом.")


@router.chat_join_request()
async def handle_chat_join_request(
    chat_join_request: ChatJoinRequest,
    bot: Bot,
    db: Database
) -> None:
    """
    Обработчик запроса на вступление в канал/группу.
    Автоматически одобряет запрос и фиксирует подписку.
    
    Args:
        chat_join_request: Запрос на вступление
        bot: Экземпляр бота
        db: База данных
    """
    user_id = chat_join_request.from_user.id
    chat_id = chat_join_request.chat.id
    chat_title = chat_join_request.chat.title
    
    logger.info(
        f"🔔 Получен запрос на вступление: пользователь {user_id} в канал '{chat_title}' (ID: {chat_id})"
    )
    
    try:
        # Автоматически одобряем запрос на вступление
        await chat_join_request.approve()
        logger.info(f"✅ Запрос на вступление одобрен: пользователь {user_id} в канал '{chat_title}'")
        
        # Получаем информацию о канале
        try:
            chat = await bot.get_chat(chat_id)
            
            # Пытаемся найти invite-ссылку в базе данных каналов
            from bot.database.repositories import ChannelRepository
            channel_repo = ChannelRepository(db)
            db_channels = await channel_repo.get_all_channels()
            
            invite_link = None
            channel_identifier = None
            
            # Ищем канал в БД по chat_id или username
            logger.debug(f"Поиск канала в БД: chat_id={chat_id}, всего каналов в БД: {len(db_channels)}")
            
            # Сначала пытаемся найти по chat_id
            for db_channel in db_channels:
                logger.debug(f"Проверка канала из БД: chat_id={db_channel.chat_id} (тип: {type(db_channel.chat_id)}), username={db_channel.username}")
                
                # Проверяем совпадение по chat_id (сравниваем как строки)
                db_chat_id_str = str(db_channel.chat_id) if db_channel.chat_id else None
                chat_id_str = str(chat_id)
                
                if db_chat_id_str == chat_id_str:
                    logger.info(f"✅ Найден канал в БД по chat_id: {db_channel.title}, username={db_channel.username}")
                    # Нашли канал в БД, используем его invite-ссылку если есть
                    if db_channel.username and db_channel.username.startswith("+"):
                        invite_link = db_channel.username
                        channel_identifier = db_channel.username
                        logger.info(f"Используем invite-ссылку из БД: {invite_link}")
                        break
                    elif db_channel.username:
                        invite_link = f"@{db_channel.username}"
                        channel_identifier = f"@{db_channel.username}"
                        break
            
            # Если не нашли по chat_id, пытаемся найти по username из chat
            if not channel_identifier and hasattr(chat, 'username') and chat.username:
                logger.debug(f"Поиск канала по username из chat: {chat.username}")
                for db_channel in db_channels:
                    if db_channel.username == chat.username:
                        logger.info(f"✅ Найден канал в БД по username: {db_channel.title}")
                        if db_channel.username.startswith("+"):
                            invite_link = db_channel.username
                            channel_identifier = db_channel.username
                            break
                        else:
                            invite_link = f"@{db_channel.username}"
                            channel_identifier = f"@{db_channel.username}"
                            break
            
            # Если не нашли в БД по chat_id, пытаемся найти канал по invite-ссылке через API
            if not channel_identifier or not invite_link:
                logger.warning(f"⚠️ Канал с chat_id={chat_id} не найден в БД каналов, пытаемся получить invite-ссылку через API")
                
                # Пытаемся получить invite-ссылку через API
                try:
                    # Пробуем экспортировать invite-ссылку
                    exported_invite = await bot.export_chat_invite_link(chat_id)
                    if hasattr(exported_invite, 'invite_link'):
                        invite_link_full = exported_invite.invite_link
                    else:
                        invite_link_full = str(exported_invite)
                    
                    logger.info(f"Получена invite-ссылка через API: {invite_link_full}")
                    
                    # Извлекаем invite-код из полной ссылки (https://t.me/+XXXXX -> +XXXXX)
                    invite_code = None
                    if invite_link_full.startswith("https://t.me/+"):
                        invite_code = "+" + invite_link_full.split("+")[-1]
                    elif invite_link_full.startswith("+"):
                        invite_code = invite_link_full.split()[0]  # Берём первую часть до пробела
                    
                    logger.debug(f"Извлечённый invite-код: {invite_code}")
                    
                    # Если это invite-ссылка с +, ищем канал в БД по этой invite-ссылке
                    if invite_code and invite_code.startswith("+"):
                        invite_link = invite_code
                        
                        # Ищем канал в БД по invite-ссылке (username)
                        for db_channel in db_channels:
                            if db_channel.username == invite_code:
                                logger.info(f"✅ Найден канал в БД по invite-ссылке: {db_channel.title}")
                                # Обновляем chat_id в БД, если его не было
                                if not db_channel.chat_id:
                                    logger.info(f"Обновляем chat_id для канала {db_channel.id}: {chat_id}")
                                    await channel_repo.update_channel_chat_id(db_channel.id, str(chat_id))
                                
                                channel_identifier = invite_code
                                logger.info(f"Используем invite-ссылку: {invite_code}")
                                break
                        
                        # Если не нашли в БД по точному совпадению, проверяем все приватные каналы без chat_id
                        if not channel_identifier:
                            private_channels_without_chat_id = [
                                ch for ch in db_channels 
                                if ch.username and ch.username.startswith("+") and not ch.chat_id
                            ]
                            if len(private_channels_without_chat_id) == 1:
                                # Если только один приватный канал без chat_id, обновляем его
                                db_channel = private_channels_without_chat_id[0]
                                logger.info(f"Обновляем chat_id для единственного приватного канала без chat_id: {db_channel.title}")
                                await channel_repo.update_channel_chat_id(db_channel.id, str(chat_id))
                                channel_identifier = db_channel.username
                                invite_link = db_channel.username
                            else:
                                # Используем invite-код из API как идентификатор
                                channel_identifier = invite_code
                                invite_link = invite_code
                                logger.info(f"Используем invite-ссылку из API: {invite_code}")
                    elif not channel_identifier:
                        # Если не получили invite-ссылку, используем chat_id
                        channel_identifier = str(chat_id)
                except Exception as e:
                    logger.warning(f"Не удалось получить invite-ссылку через API: {e}")
                    # Если не удалось получить через API, ищем каналы без chat_id и обновляем первый найденный
                    # (на случай если это единственный приватный канал)
                    private_channels_without_chat_id = [
                        ch for ch in db_channels 
                        if ch.username and ch.username.startswith("+") and not ch.chat_id
                    ]
                    if len(private_channels_without_chat_id) == 1:
                        # Если только один приватный канал без chat_id, обновляем его
                        db_channel = private_channels_without_chat_id[0]
                        logger.info(f"Обновляем chat_id для единственного приватного канала без chat_id: {db_channel.title}")
                        await channel_repo.update_channel_chat_id(db_channel.id, str(chat_id))
                        channel_identifier = db_channel.username
                        invite_link = db_channel.username
                    elif not channel_identifier:
                        channel_identifier = str(chat_id)
            
            # Создаём/обновляем пользователя
            user_repo = UserRepository(db)
            await user_repo.create_user(
                user_id=user_id,
                username=chat_join_request.from_user.username,
                full_name=chat_join_request.from_user.full_name or ""
            )
            
            # Логируем подтверждение подписки через chat_join_request
            log_repo = UserActionLogRepository(db)
            log_data = {
                "channel_id": str(chat_id),
                "channel_title": chat_title,
                "channel_identifier": channel_identifier,
                "invite_link": invite_link,
                "method": "chat_join_request"
            }
            
            await log_repo.create_log(
                user_id=user_id,
                action_type="private_subscription_confirmed",
                message_text=f"Подтвердил подписку на канал {chat_title} через запрос на вступление",
                action_data=log_data
            )
            
            logger.info(
                f"✅ Подписка пользователя {user_id} на канал '{chat_title}' "
                f"зафиксирована через chat_join_request. Данные: {log_data}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о канале: {e}")
            # Всё равно логируем подтверждение подписки
            log_repo = UserActionLogRepository(db)
            await log_repo.create_log(
                user_id=user_id,
                action_type="private_subscription_confirmed",
                message_text=f"Подтвердил подписку на канал {chat_title} через запрос на вступление",
                action_data={
                    "channel_id": str(chat_id),
                    "channel_title": chat_title,
                    "method": "chat_join_request",
                    "error": str(e)
                }
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на вступление: {e}")
        # Пытаемся одобрить запрос вручную через API
        try:
            await bot.approve_chat_join_request(
                chat_id=chat_id,
                user_id=user_id
            )
            logger.info(f"Запрос одобрен через API: пользователь {user_id} в канал {chat_id}")
        except Exception as api_error:
            logger.error(f"Не удалось одобрить запрос через API: {api_error}")
