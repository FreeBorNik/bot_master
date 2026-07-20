"""Роутер для пользователей."""
import asyncio
import json
from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.enums import ParseMode

from bot.database.db import Database
from bot.database.repositories import (
    UserRepository,
    ChannelRepository,
    PostQuestionnaireMessageRepository,
    ChainMessageRepository,
    WelcomeMessageRepository,
    SettingsRepository,
    ChannelsListMessageRepository,
)
from bot.database.action_logs_repository import UserActionLogRepository
from bot.services.subscription import check_user_subscription
from bot.states.user_states import QuestionnaireStates
from bot.utils.helpers import (
    parse_entities_from_json,
    apply_welcome_placeholders,
    resolve_button_url,
    exceeds_telegram_caption_limit,
)
from bot.utils.logger import setup_logger
from bot.keyboards.user_kb import (
    get_i_subscribed_keyboard,
    get_age_keyboard,
    get_hours_keyboard,
    get_other_job_keyboard,
    get_subscription_check_keyboard,
)

logger = setup_logger(__name__)

# Предпросмотр ссылок всегда отключён для сообщений цепочки
_CHAIN_LINK_PREVIEW_DISABLED = LinkPreviewOptions(is_disabled=True)


async def _send_media_with_text(
    bot: Bot,
    chat_id: int,
    *,
    media_type: str | None,
    media_file_id: str | None,
    text: str,
    entities: list | None,
    reply_markup: InlineKeyboardMarkup | None,
    default_text: str,
    disable_link_preview: bool = False,
) -> None:
    """
    Отправка медиа с текстом.
    Если caption превышает лимит Telegram (1024) — медиа и текст двумя сообщениями.
    """
    message_text = text or default_text
    split_caption = bool(text) and exceeds_telegram_caption_limit(text)
    text_kwargs: dict = {
        "chat_id": chat_id,
        "text": message_text,
        "entities": entities if entities else None,
        "parse_mode": None if entities else ParseMode.HTML,
        "reply_markup": reply_markup,
    }
    if disable_link_preview:
        text_kwargs["link_preview_options"] = _CHAIN_LINK_PREVIEW_DISABLED
        text_kwargs["disable_web_page_preview"] = True

    if media_type == "photo" and media_file_id:
        if split_caption:
            await bot.send_photo(chat_id=chat_id, photo=media_file_id)
            await bot.send_message(**text_kwargs)
            return
        await bot.send_photo(
            chat_id=chat_id,
            photo=media_file_id,
            caption=text or "",
            caption_entities=entities if entities else None,
            parse_mode=None if entities else ParseMode.HTML,
            reply_markup=reply_markup,
        )
        return

    if media_type == "video" and media_file_id:
        if split_caption:
            await bot.send_video(chat_id=chat_id, video=media_file_id)
            await bot.send_message(**text_kwargs)
            return
        await bot.send_video(
            chat_id=chat_id,
            video=media_file_id,
            caption=text or "",
            caption_entities=entities if entities else None,
            parse_mode=None if entities else ParseMode.HTML,
            reply_markup=reply_markup,
        )
        return

    await bot.send_message(**text_kwargs)

router = Router(name="user")

# Таймеры: сообщение после анкеты (5 мин, если анкета не заполнена)
pending_questionnaire_timers: dict[int, asyncio.Task] = {}

# Мотивационное сообщение для неподписанных пользователей
MOTIVATION_MESSAGE = (
    "❌ К сожалению, вы не подписаны на все необходимые каналы.\n\n"
    "Для продолжения работы с ботом необходимо подписаться на указанные каналы.\n"
    "После подписки нажмите кнопку 'Проверить подписку' снова."
)


async def _get_user_placeholder_data(db: Database, user_id: int) -> tuple[str, str, str]:
    """Получить first_name, full_name, username для плейсхолдеров {first_name}, {full_name}, {username}."""
    user_repo = UserRepository(db)
    user = await user_repo.get_user(user_id)
    if not user:
        return "", "", ""
    full_name = (user.full_name or "").strip()
    username = (user.username or "").strip()
    first_name = full_name.split()[0] if full_name else ""
    return first_name, full_name, username


async def send_post_questionnaire_message(bot: Bot, user_id: int, db: Database) -> bool:
    """
    Отправка сообщения после анкеты из БД (если настроено и активно в админ-панели).
    Поддерживаются плейсхолдеры: {first_name}, {full_name}, {username}.

    Returns:
        True если сообщение из БД отправлено, False если не настроено или неактивно.
    """
    try:
        post_repo = PostQuestionnaireMessageRepository(db)
        msg = await post_repo.get_post_questionnaire_message()
        if not msg or not msg.is_active:
            return False

        entities = parse_entities_from_json(msg.entities_json)
        first_name, full_name, username = await _get_user_placeholder_data(db, user_id)
        text = msg.text or ""
        text, entities = apply_welcome_placeholders(
            text, first_name, full_name, username, entities
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
                            row_buttons.append(
                                InlineKeyboardButton(text=button["text"], url=button["url"])
                            )
                    if row_buttons:
                        keyboard_buttons.append(row_buttons)
                if keyboard_buttons:
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            except Exception as e:
                logger.error(f"Ошибка парсинга кнопок сообщения после анкеты: {e}")

        if msg.media_type == "photo" and msg.media_file_id:
            await _send_media_with_text(
                bot,
                user_id,
                media_type=msg.media_type,
                media_file_id=msg.media_file_id,
                text=text,
                entities=entities,
                reply_markup=reply_markup,
                default_text="Сообщение после анкеты",
            )
        elif msg.media_type == "video" and msg.media_file_id:
            await _send_media_with_text(
                bot,
                user_id,
                media_type=msg.media_type,
                media_file_id=msg.media_file_id,
                text=text,
                entities=entities,
                reply_markup=reply_markup,
                default_text="Сообщение после анкеты",
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=text or "Сообщение после анкеты",
                entities=entities if entities else None,
                parse_mode=None if entities else ParseMode.HTML,
                reply_markup=reply_markup,
            )
        logger.info(f"Отправлено сообщение после анкеты пользователю {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения после анкеты пользователю {user_id}: {e}")
        return False


async def send_post_questionnaire_message_delayed(bot: Bot, user_id: int, db: Database) -> None:
    """Отправка сообщения после анкеты (без задержки)."""
    try:
        await send_post_questionnaire_message(bot, user_id, db)
    except asyncio.CancelledError:
        logger.debug(f"Отправка сообщения после анкеты для пользователя {user_id} отменена")
    except Exception as e:
        logger.error(f"Ошибка в задаче отправки сообщения после анкеты пользователю {user_id}: {e}")


async def send_welcome_message_to_user(bot: Bot, user_id: int, db: Database) -> bool:
    """
    Отправка приветственного сообщения пользователю.
    Кнопка «Проверить подписку» всегда в приветствии — добавляем её сюда.
    Returns True если отправлено.
    """
    try:
        welcome_repo = WelcomeMessageRepository(db)
        welcome_msg = await welcome_repo.get_welcome_message()
        if not welcome_msg or not welcome_msg.text:
            return False
        entities = parse_entities_from_json(welcome_msg.entities_json)
        first_name, full_name, username = await _get_user_placeholder_data(db, user_id)
        text = welcome_msg.text or ""
        text, entities = apply_welcome_placeholders(
            text, first_name, full_name, username, entities
        )
        reply_markup = get_subscription_check_keyboard()
        if entities:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                entities=entities,
                parse_mode=None,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        logger.info(f"Отправлено приветственное сообщение пользователю {user_id} (по порядку шагов)")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки приветствия пользователю {user_id}: {e}")
        return False


async def start_questionnaire_at_start(
    bot: Bot, user_id: int, db: Database, state: FSMContext, message: Message
) -> None:
    """
    Запуск анкеты сразу при /start (когда первым в порядке стоит «Старт анкеты»).
    Проверка подписки не показывается — только приветствие содержит кнопку подписки.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_user(user_id)
    if user and user.age is not None:
        await message.answer("✅ Вы уже заполнили анкету. Спасибо за регистрацию!")
        return
    if user_id in pending_questionnaire_timers:
        pending_questionnaire_timers[user_id].cancel()
        del pending_questionnaire_timers[user_id]
    pending_questionnaire_timers[user_id] = asyncio.create_task(
        send_post_questionnaire_message_after_timeout(bot, user_id, db)
    )
    logger.info(f"Запущен таймер 5 мин для пользователя {user_id} (анкета с /start)")
    await state.set_state(QuestionnaireStates.age)
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=user_id,
        action_type="questionnaire_started",
        message_text="Старт анкеты с /start (без проверки подписки)",
        action_data={"source": "start_command"},
    )
    await message.answer(
        "✅ Переходим к заполнению анкеты.\n\n"
        "📝 Вопрос 1/3: Сколько вам лет?",
        reply_markup=get_age_keyboard(),
    )


@router.callback_query(F.data == "start_questionnaire_simple")
async def cmd_start_questionnaire_simple(
    callback: CallbackQuery, bot: Bot, db: Database, state: FSMContext
) -> None:
    """Запуск анкеты по кнопке «Заполнить анкету» (режим приветствия «анкета первой»)."""
    await callback.answer()
    await start_questionnaire_at_start(
        bot, callback.from_user.id, db, state, callback.message
    )


async def send_channels_list_message(bot: Bot, user_id: int, db: Database) -> bool:
    """
    Отправить сообщение со списком каналов (режим «анкета первой»).
    В тексте сообщения плейсхолдер {channels_list} заменяется на список каналов.
    """
    try:
        channels_repo = ChannelRepository(db)
        channels = await channels_repo.get_all_channels()
        lines = []
        for ch in channels:
            if ch.username:
                link = ch.username if ch.username.startswith("+") else f"https://t.me/{ch.username.lstrip('@')}"
                title = ch.title or ch.username
                lines.append(f"• {title}: {link}")
        channels_list = "\n".join(lines) if lines else "— каналы не добавлены —"

        list_repo = ChannelsListMessageRepository(db)
        msg = await list_repo.get_channels_list_message()
        if not msg or not msg.is_active:
            text = f"📢 Подпишитесь на наши каналы:\n\n{channels_list}"
        else:
            text = (msg.text or "").replace("{channels_list}", channels_list)
        if not text.strip():
            text = f"📢 Подпишитесь на наши каналы:\n\n{channels_list}"
        first_name, full_name, username = await _get_user_placeholder_data(db, user_id)
        entities = (
            parse_entities_from_json(msg.entities_json)
            if msg and getattr(msg, "entities_json", None)
            else None
        )
        text, entities = apply_welcome_placeholders(text, first_name, full_name, username, entities)
        await bot.send_message(
            chat_id=user_id,
            text=text,
            entities=entities,
            parse_mode=None if entities else ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения со списком каналов пользователю {user_id}: {e}")
        return False


async def run_flow_steps_after_questionnaire(bot: Bot, user_id: int, db: Database) -> None:
    """
    Отправить пользователю шаги после анкеты.
    В режиме questionnaire_first: приветственное сообщение с кнопкой «Проверить подписку».
    После нажатия кнопки (в process_subscription_check) — сообщение после анкеты.
    В режиме subscription_first: сразу сообщение после анкеты.
    """
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    if getattr(settings, "welcome_mode", "subscription_first") == "questionnaire_first":
        await send_welcome_message_to_user(bot, user_id, db)
        return
    chain_repo = ChainMessageRepository(db)
    flow_order = await chain_repo.get_flow_order()
    remaining = [x for x in flow_order if x not in [1, 2, 4]]
    for step in remaining:
        if step == 3:
            asyncio.create_task(send_post_questionnaire_message_delayed(bot, user_id, db))


async def send_post_questionnaire_message_after_timeout(bot: Bot, user_id: int, db: Database) -> None:
    """Отправка сообщения после анкеты через 5 минут, если анкета не заполнена."""
    try:
        await asyncio.sleep(300)  # 5 минут
        if user_id in pending_questionnaire_timers:
            del pending_questionnaire_timers[user_id]
        user_repo = UserRepository(db)
        user = await user_repo.get_user(user_id)
        if user and user.age is not None:
            logger.debug(f"Анкета пользователя {user_id} уже заполнена, не отправляем по таймауту")
            return
        await run_flow_steps_after_questionnaire(bot, user_id, db)
    except asyncio.CancelledError:
        logger.debug(f"Таймер отправки сообщения после анкеты для пользователя {user_id} отменен")
        if user_id in pending_questionnaire_timers:
            del pending_questionnaire_timers[user_id]
    except Exception as e:
        logger.error(f"Ошибка в таймере отправки сообщения после анкеты пользователю {user_id}: {e}")
        if user_id in pending_questionnaire_timers:
            del pending_questionnaire_timers[user_id]


async def send_chain_message(bot: Bot, user_id: int, db: Database, chain_message) -> bool:
    """
    Отправка одного сообщения из цепочки.
    Поддерживаются плейсхолдеры: {first_name}, {full_name}, {username}.
    Предпросмотр ссылок всегда отключён.

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        db: База данных
        chain_message: Объект ChainMessage

    Returns:
        True если сообщение отправлено, False если не отправлено
    """
    try:
        # Проверяем активность сообщения (по объекту и повторно из БД — на случай деактивации после старта задачи)
        if not chain_message.is_active:
            logger.debug(f"Сообщение {chain_message.message_number} цепочки неактивно, пропускаем")
            return False
        chain_repo = ChainMessageRepository(db)
        current_msg = await chain_repo.get_chain_message(chain_message.message_number)
        if not current_msg or not current_msg.is_active:
            logger.info(
                f"Сообщение {chain_message.message_number} цепочки деактивировано в БД, пропускаем отправку пользователю {user_id}"
            )
            return False

        # Парсим entities и подставляем плейсхолдеры
        entities = parse_entities_from_json(chain_message.entities_json)
        first_name, full_name, username = await _get_user_placeholder_data(db, user_id)
        text = chain_message.text or ""
        text, entities = apply_welcome_placeholders(
            text, first_name, full_name, username, entities
        )

        # Формируем клавиатуру из кнопок (подставляем плейсхолдеры в URL — Telegram не принимает невалидные ссылки)
        reply_markup = None
        if chain_message.buttons_json:
            try:
                buttons_data = json.loads(chain_message.buttons_json)
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
                                    text=button["text"],
                                    url=resolved_url
                                ))
                    if row_buttons:
                        keyboard_buttons.append(row_buttons)
                if keyboard_buttons:
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            except Exception as e:
                logger.error(f"Ошибка парсинга кнопок для сообщения цепочки: {e}")

        await _send_media_with_text(
            bot,
            user_id,
            media_type=chain_message.media_type,
            media_file_id=chain_message.media_file_id,
            text=text,
            entities=entities,
            reply_markup=reply_markup,
            default_text="Сообщение цепочки",
            disable_link_preview=True,
        )

        logger.info(f"Отправлено сообщение {chain_message.message_number} цепочки пользователю {user_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения {chain_message.message_number} цепочки пользователю {user_id}: {e}")
        return False


async def send_chain_messages(bot: Bot, user_id: int, db: Database) -> None:
    """
    Отправка цепочки сообщений. Время отсчитывается от момента после «Сообщения после анкеты».
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        db: База данных
    """
    try:
        chain_repo = ChainMessageRepository(db)
        chain_is_active = await chain_repo.get_chain_is_active()
        if not chain_is_active:
            logger.info(
                f"Цепочка сообщений выключена (chain_settings.is_active=0), "
                f"пропускаем отправку для пользователя {user_id}"
            )
            return
        chain_messages = await chain_repo.get_active_chain_messages()
        if not chain_messages:
            logger.warning(
                f"Нет активных сообщений в цепочке (все is_active=0 или цепочка пуста), "
                f"пропускаем отправку для пользователя {user_id}"
            )
            return
        logger.info(
            f"Найдено {len(chain_messages)} активных сообщений цепочки для пользователя {user_id}: "
            f"номера {[m.message_number for m in chain_messages]}"
        )
        
        # Сортируем по номеру сообщения
        chain_messages.sort(key=lambda x: x.message_number)
        
        logger.info(f"Начинаем отправку цепочки сообщений для пользователя {user_id}: сообщения {[m.message_number for m in chain_messages]}")
        
        # Отправляем сообщения с интервалами относительно предыдущего
        # delay_minutes: первый — от момента после анкеты, остальные — от предыдущего сообщения цепочки
        for i, chain_msg in enumerate(chain_messages):
            if i == 0:
                logger.info(
                    f"Ожидание {chain_msg.delay_minutes} мин. перед первым сообщением #{chain_msg.message_number} "
                    f"цепочки пользователю {user_id} (от «Сообщения после анкеты»)"
                )
                await asyncio.sleep(chain_msg.delay_minutes * 60)  # Преобразуем минуты в секунды
            else:
                # Последующие сообщения: delay_minutes от предыдущего сообщения цепочки
                logger.info(
                    f"Ожидание {chain_msg.delay_minutes} минут перед отправкой сообщения {chain_msg.message_number} "
                    f"цепочки пользователю {user_id} (относительно предыдущего сообщения)"
                )
                await asyncio.sleep(chain_msg.delay_minutes * 60)  # Преобразуем минуты в секунды
            
            # Отправляем сообщение с отключённым предпросмотром ссылок
            logger.info(f"Отправка сообщения {chain_msg.message_number} цепочки пользователю {user_id}")
            result = await send_chain_message(bot, user_id, db, chain_msg)
            if not result:
                logger.warning(f"Не удалось отправить сообщение {chain_msg.message_number} цепочки пользователю {user_id}")
        
        logger.info(f"Завершена отправка цепочки сообщений пользователю {user_id}")
        
    except asyncio.CancelledError:
        logger.debug(f"Отправка цепочки сообщений для пользователя {user_id} отменена")
    except Exception as e:
        logger.error(f"Ошибка при отправке цепочки сообщений пользователю {user_id}: {e}")


async def process_subscription_check(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    state: FSMContext
) -> None:
    """
    Общая логика проверки подписки.
    В режиме questionnaire_first после заполнения анкеты: при подписке — сообщение после анкеты.
    В режиме subscription_first: при подписке — старт анкеты.
    """
    user_id = callback.from_user.id
    settings_repo = SettingsRepository(db)
    settings = await settings_repo.get_settings()
    welcome_mode = getattr(settings, "welcome_mode", "subscription_first")
    user_repo = UserRepository(db)
    user = await user_repo.get_user(user_id)

    # Режим «без анкеты»: активация считается по нажатию кнопки и показу сообщения после анкеты
    if welcome_mode == "no_questionnaire":
        sent = await send_post_questionnaire_message(bot, user_id, db)
        log_repo = UserActionLogRepository(db)
        if sent:
            await log_repo.create_log(
                user_id=user_id,
                action_type="questionnaire_started",
                message_text="Активация в режиме без анкеты: нажал «Проверить подписку» и получил сообщение",
                action_data={
                    "source": "no_questionnaire_mode",
                    "button": "check_subscription",
                    "post_questionnaire_message_sent": True,
                },
            )
        else:
            await log_repo.create_log(
                user_id=user_id,
                action_type="no_questionnaire_check_clicked",
                message_text="Нажал «Проверить подписку» в режиме без анкеты, но сообщение после анкеты не отправлено",
                action_data={
                    "source": "no_questionnaire_mode",
                    "button": "check_subscription",
                    "post_questionnaire_message_sent": False,
                },
            )
        return

    # Режим «анкета первой»: пользователь уже заполнил анкету, ждёт проверки подписки
    if welcome_mode == "questionnaire_first" and user and user.age is not None:
        channel_repo = ChannelRepository(db)
        db_channels = await channel_repo.get_channels_for_check()
        channels_to_check = []
        private_channels = []
        for channel in db_channels:
            if channel.username:
                if channel.username.startswith("+"):
                    private_channels.append(channel)
                    channels_to_check.append((channel.username, "channel_invite"))
                else:
                    channels_to_check.append((channel.username, channel.type))
            elif channel.chat_id:
                channels_to_check.append((channel.chat_id, channel.type))

        if not channels_to_check:
            await send_post_questionnaire_message(bot, user_id, db)
            asyncio.create_task(send_chain_messages(bot, user_id, db))
            return

        is_subscribed = await check_user_subscription(bot, user_id, channels_to_check, db)
        if not is_subscribed and private_channels:
            missing_private = []
            for ch in private_channels:
                if ch.username.startswith("+"):
                    missing_private.append({"invite": ch.username, "title": ch.title or "Приватный канал"})
            if missing_private:
                invite_link = missing_private[0]["invite"]
                channel_url = f"https://t.me/{invite_link}"
                await callback.message.answer(
                    f"Вы не подписаны на канал {channel_url}\n\n"
                    "Пожалуйста, подпишитесь и нажмите на кнопку «Я подписчик»",
                    reply_markup=get_i_subscribed_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
                return

        await user_repo.set_subscription_status(user_id, is_subscribed)
        log_repo = UserActionLogRepository(db)
        await log_repo.create_log(
            user_id=user_id,
            action_type="subscription_check_result",
            message_text=f"Проверка подписки: {'подписан' if is_subscribed else 'не подписан'}",
            action_data={"is_subscribed": is_subscribed, "channels_checked": len(channels_to_check)},
        )
        if is_subscribed:
            await send_post_questionnaire_message(bot, user_id, db)
            asyncio.create_task(send_chain_messages(bot, user_id, db))
        else:
            await callback.message.answer(MOTIVATION_MESSAGE)
        return

    # Получаем каналы из БД для проверки подписки
    channel_repo = ChannelRepository(db)
    # Получаем только каналы, для которых нужно проверять подписку
    db_channels = await channel_repo.get_channels_for_check()
    
    channels_to_check = []
    private_channels = []  # Список приватных каналов с invite-ссылками
    
    for channel in db_channels:
        if channel.username:
            # Проверяем, является ли это invite-ссылкой
            if channel.username.startswith("+"):
                private_channels.append(channel)
                channels_to_check.append((channel.username, "channel_invite"))
            else:
                channels_to_check.append((channel.username, channel.type))
        elif channel.chat_id:
            channels_to_check.append((channel.chat_id, channel.type))
    
    # Если каналов нет, сразу переходим к заполнению анкеты
    if not channels_to_check:
        logger.info("Нет каналов для проверки подписки, переходим к заполнению анкеты")
        user = await user_repo.get_user(user_id)
        
        # Проверяем, заполнена ли уже анкета
        if user and user.age is not None:
            await callback.message.answer(
                "✅ Вы уже заполнили анкету. Спасибо за регистрацию!"
            )
        else:
            # Устанавливаем статус подписки как True (так как каналов нет для проверки)
            await user_repo.set_subscription_status(user_id, True)
            
            # Логируем отсутствие каналов
            log_repo = UserActionLogRepository(db)
            await log_repo.create_log(
                user_id=user_id,
                action_type="subscription_check_result",
                message_text="Проверка подписки: каналы не настроены, переход к анкете",
                action_data={
                    "is_subscribed": True,
                    "channels_checked": 0,
                    "channels_list": [],
                    "reason": "no_channels_configured"
                }
            )
            if user_id in pending_questionnaire_timers:
                pending_questionnaire_timers[user_id].cancel()
                del pending_questionnaire_timers[user_id]
            pending_questionnaire_timers[user_id] = asyncio.create_task(
                send_post_questionnaire_message_after_timeout(bot, user_id, db)
            )
            logger.info(f"Запущен таймер 5 мин (сообщение после анкеты) для пользователя {user_id}")
            await state.set_state(QuestionnaireStates.age)
            await log_repo.create_log(
                user_id=user_id,
                action_type="questionnaire_started",
                message_text="Увидел анкету (активация бота)",
                action_data={"source": "no_channels"},
            )
            await callback.message.answer(
                "✅ Отлично! Переходим к заполнению анкеты.\n\n"
                "📝 Вопрос 1/3: Сколько вам лет?",
                reply_markup=get_age_keyboard()
            )
        return
    
    # Проверка подписки (передаём db для проверки подтверждённых подписок через chat_join_request)
    is_subscribed = await check_user_subscription(bot, user_id, channels_to_check, db)
    
    # Если есть приватные каналы и пользователь не подписан, формируем сообщение с инструкцией
    if not is_subscribed and private_channels:
        missing_private = []
        for channel in private_channels:
            if channel.username.startswith("+"):
                missing_private.append({
                    "invite": channel.username,
                    "title": channel.title or "Приватный канал"
                })
        
        if missing_private:
            # Формируем сообщение с кликабельной ссылкой
            invite_link = missing_private[0]["invite"]
            channel_url = f"https://t.me/{invite_link}"
            text = (
                f"Вы не подписаны на канал {channel_url}\n\n"
                "Пожалуйста, подпишитесь и нажмите на кнопку \"Я подписчик\""
            )
            
            await callback.message.answer(
                text,
                reply_markup=get_i_subscribed_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
    
    await user_repo.set_subscription_status(user_id, is_subscribed)
    
    # Детальное логирование проверки подписки
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=user_id,
        action_type="subscription_check_result",
        message_text=f"Проверка подписки: {'подписан' if is_subscribed else 'не подписан'}",
        action_data={
            "is_subscribed": is_subscribed,
            "channels_checked": len(channels_to_check),
            "channels_list": [ch[0] for ch in channels_to_check]
        }
    )
    
    if is_subscribed:
        # Пользователь подписан - начинаем анкету
        user = await user_repo.get_user(user_id)
        
        # Проверяем, заполнена ли уже анкета
        if user and user.age is not None:
            await callback.message.answer(
                "✅ Вы уже заполнили анкету. Спасибо за регистрацию!"
            )
        else:
            if user_id in pending_questionnaire_timers:
                pending_questionnaire_timers[user_id].cancel()
                del pending_questionnaire_timers[user_id]
            pending_questionnaire_timers[user_id] = asyncio.create_task(
                send_post_questionnaire_message_after_timeout(bot, user_id, db)
            )
            logger.info(f"Запущен таймер 5 мин (сообщение после анкеты) для пользователя {user_id}")
            await state.set_state(QuestionnaireStates.age)
            await log_repo.create_log(
                user_id=user_id,
                action_type="questionnaire_started",
                message_text="Увидел анкету (активация бота)",
                action_data={"source": "after_subscription"},
            )
            await callback.message.answer(
                "✅ Отлично! Вы подписаны на все каналы.\n\n"
                "Теперь давайте заполним небольшую анкету.\n\n"
                "📝 Вопрос 1/3: Сколько вам лет?",
                reply_markup=get_age_keyboard()
            )
    else:
        # Пользователь не подписан
        await callback.message.answer(MOTIVATION_MESSAGE)


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    state: FSMContext
) -> None:
    """
    Обработчик проверки подписки.
    
    Args:
        callback: Callback запрос
        bot: Экземпляр бота
        db: База данных
        state: FSM контекст
    """
    await callback.answer()
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=callback.from_user.id,
        action_type="subscription_check_clicked",
        message_text="Нажал кнопку «Проверить подписку»",
        action_data={"button": "check_subscription"},
    )
    await process_subscription_check(callback, bot, db, state)


@router.callback_query(F.data == "i_subscribed")
async def i_subscribed_callback(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    state: FSMContext
) -> None:
    """
    Обработчик кнопки "Я подписчик".
    
    Args:
        callback: Callback запрос
        bot: Экземпляр бота
        db: База данных
        state: FSM контекст
    """
    await callback.answer()
    await process_subscription_check(callback, bot, db, state)


@router.callback_query(F.data.startswith("questionnaire_age_"), StateFilter(QuestionnaireStates.age))
async def process_age(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """
    Обработка ответа на вопрос о возрасте через кнопку.
    
    Args:
        callback: Callback запрос
        state: FSM контекст
        db: База данных
    """
    await callback.answer()
    
    # Извлекаем диапазон возраста из callback_data
    age_range = callback.data.replace("questionnaire_age_", "")
    
    await state.update_data(age=age_range)
    await state.set_state(QuestionnaireStates.hours_per_day)
    
    # Логирование ответа на вопрос анкеты
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=callback.from_user.id,
        action_type="questionnaire_answer",
        message_text=f"Ответил на вопрос анкеты: возраст = {age_range}",
        action_data={
            "question": "age",
            "answer": age_range,
            "question_number": 1
        }
    )
    
    await callback.message.edit_text(
        "✅ Возраст сохранен.\n\n"
        "📝 Вопрос 2/3: Сколько часов в день вы готовы уделять нашей работе?",
        reply_markup=get_hours_keyboard()
    )


@router.callback_query(F.data.startswith("questionnaire_hours_"), StateFilter(QuestionnaireStates.hours_per_day))
async def process_hours(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """
    Обработка ответа на вопрос о часах работы через кнопку.
    
    Args:
        callback: Callback запрос
        state: FSM контекст
        db: База данных
    """
    await callback.answer()
    
    # Извлекаем диапазон часов из callback_data и преобразуем в читаемый формат
    hours_code = callback.data.replace("questionnaire_hours_", "")
    hours_mapping = {
        "up_to_2": "до 2 часов в день",
        "2_to_4": "от 2 до 4 часов в день",
        "more_than_4": "более 4 часов в день"
    }
    hours_range = hours_mapping.get(hours_code, hours_code)
    
    await state.update_data(hours_per_day=hours_range)
    await state.set_state(QuestionnaireStates.has_other_job)
    
    # Логирование ответа на вопрос анкеты
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=callback.from_user.id,
        action_type="questionnaire_answer",
        message_text=f"Ответил на вопрос анкеты: часов в день = {hours_range}",
        action_data={
            "question": "hours_per_day",
            "answer": hours_range,
            "question_number": 2
        }
    )
    
    await callback.message.edit_text(
        "✅ Количество часов сохранено.\n\n"
        "📝 Вопрос 3/3: У вас есть другая работа?",
        reply_markup=get_other_job_keyboard()
    )


@router.callback_query(F.data.startswith("questionnaire_job_"), StateFilter(QuestionnaireStates.has_other_job))
async def process_other_job(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot
) -> None:
    """
    Обработка ответа на вопрос о другой работе через кнопку и сохранение анкеты.
    
    Args:
        callback: Callback запрос
        state: FSM контекст
        db: База данных
        bot: Экземпляр бота
    """
    await callback.answer()
    
    # Извлекаем ответ из callback_data
    job_answer = callback.data.replace("questionnaire_job_", "")
    has_other_job = job_answer == "yes"
    
    # Логирование ответа на последний вопрос анкеты
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=callback.from_user.id,
        action_type="questionnaire_answer",
        message_text=f"Ответил на вопрос анкеты: другая работа = {has_other_job}",
        action_data={
            "question": "has_other_job",
            "answer": has_other_job,
            "question_number": 3
        }
    )
    
    # Получение данных из состояния
    data = await state.get_data()
    age = data.get("age")
    hours_per_day = data.get("hours_per_day")
    
    # Сохранение анкеты в БД
    user_repo = UserRepository(db)
    await user_repo.update_user_questionnaire(
        user_id=callback.from_user.id,
        age=str(age) if age else None,
        hours_per_day=str(hours_per_day) if hours_per_day else None,
        has_other_job=has_other_job
    )
    
    # Завершение состояния
    await state.clear()
    
    # Детальное логирование заполнения анкеты
    log_repo = UserActionLogRepository(db)
    await log_repo.create_log(
        user_id=callback.from_user.id,
        action_type="questionnaire_completed",
        message_text="Заполнил анкету полностью",
        action_data={
            "age": age,
            "hours_per_day": hours_per_day,
            "has_other_job": has_other_job,
            "questionnaire_status": "completed"
        }
    )
    
    await callback.message.delete()
    user_id = callback.from_user.id
    logger.info(
        f"Пользователь {user_id} заполнил анкету: "
        f"возраст={age}, часов={hours_per_day}, другая работа={has_other_job}"
    )

    if user_id in pending_questionnaire_timers:
        pending_questionnaire_timers[user_id].cancel()
        del pending_questionnaire_timers[user_id]

    await run_flow_steps_after_questionnaire(bot, user_id, db)
