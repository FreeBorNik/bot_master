"""Вспомогательные функции."""
from typing import Optional, List, Tuple
from aiogram.types import MessageEntity
import json
import re
from urllib.parse import urlsplit

from bot.utils.logger import setup_logger

logger = setup_logger(__name__)

TELEGRAM_CAPTION_MAX_LENGTH = 1024


def _utf16_len(s: str) -> int:
    """Длина строки в UTF-16 code units (как offset/length в Telegram MessageEntity)."""
    return len(s.encode("utf-16-le")) // 2


def exceeds_telegram_caption_limit(text: str, limit: int = TELEGRAM_CAPTION_MAX_LENGTH) -> bool:
    """Проверка превышения лимита caption для photo/video в Telegram."""
    return _utf16_len(text) > limit


def _python_slice_to_utf16_offset(text: str, py_end_exclusive: int) -> int:
    """UTF-16-длина префикса text[:py_end_exclusive] (py_end_exclusive — индекс в Python-символах)."""
    if py_end_exclusive <= 0:
        return 0
    return _utf16_len(text[:py_end_exclusive])


def _entity_with_offset_length(entity: MessageEntity, offset: int, length: int) -> MessageEntity:
    """Копия сущности с новыми offset/length (остальные поля без изменений)."""
    if hasattr(entity, "model_copy"):
        return entity.model_copy(update={"offset": offset, "length": length})
    return MessageEntity(
        type=entity.type,
        offset=offset,
        length=length,
        url=getattr(entity, "url", None),
        language=getattr(entity, "language", None),
        custom_emoji_id=getattr(entity, "custom_emoji_id", None),
        user=getattr(entity, "user", None),
    )


def _is_valid_entity_for_send(entity: MessageEntity) -> bool:
    """Проверка обязательных полей entity перед отправкой в Telegram API."""
    if entity.type == "custom_emoji" and not entity.custom_emoji_id:
        return False
    if entity.type == "text_link" and not entity.url:
        return False
    if entity.type == "text_mention" and not entity.user:
        return False
    return True


def message_entity_to_dict(entity: MessageEntity) -> dict:
    """Сериализация MessageEntity в dict для хранения в БД."""
    entity_dict: dict = {
        "type": entity.type,
        "offset": entity.offset,
        "length": entity.length,
    }
    if entity.url is not None:
        entity_dict["url"] = entity.url
    if entity.language is not None:
        entity_dict["language"] = entity.language
    if entity.custom_emoji_id is not None:
        entity_dict["custom_emoji_id"] = entity.custom_emoji_id
    if entity.user is not None:
        if hasattr(entity.user, "model_dump"):
            entity_dict["user"] = entity.user.model_dump(exclude_none=True)
        else:
            entity_dict["user"] = entity.user.dict(exclude_none=True)
    return entity_dict


def message_entities_to_json(entities: Optional[List[MessageEntity]]) -> Optional[str]:
    """Сериализация списка entities в JSON-строку."""
    if not entities:
        return None
    return json.dumps([message_entity_to_dict(e) for e in entities], ensure_ascii=False)


def extract_entities_json_from_message(message) -> Optional[str]:
    """Извлечение entities из текста или caption сообщения и сериализация в JSON."""
    entities = message.entities or message.caption_entities or []
    return message_entities_to_json(entities)


def _utf16_units_prefix_to_python_end(text: str, u16_count: int) -> int:
    """
    Номер Python-среза text[:j], где j такой что UTF-16 длина префикса == u16_count.
    Если u16_count выходит за длину текста — len(text).
    """
    if u16_count <= 0:
        return 0
    acc = 0
    for i, ch in enumerate(text):
        cu = _utf16_len(ch)
        if acc + cu > u16_count:
            logger.warning(
                "MessageEntity offset попал внутрь символа (UTF-16), срез по границе символа: pos=%s",
                i,
            )
            return i
        acc += cu
        if acc == u16_count:
            return i + 1
    return len(text)


def sort_and_sanitize_entities(
    text: str, entities: Optional[List[MessageEntity]]
) -> Optional[List[MessageEntity]]:
    """
    Сортировка по offset (так ожидает клиент) и обрезка сущностей по фактической UTF-16 длине текста.
    Убирает выход за границы после подстановок/рассинхрона с БД.
    """
    if not entities:
        return None
    t_u16 = _utf16_len(text)
    out: List[MessageEntity] = []
    for e in sorted(entities, key=lambda x: (int(x.offset), int(x.length))):
        off, ln = int(e.offset), int(e.length)
        if ln <= 0 or off < 0:
            continue
        if off >= t_u16:
            continue
        if off + ln > t_u16:
            new_len = t_u16 - off
            if new_len <= 0:
                continue
            logger.debug(
                "Обрезана сущность %s: offset=%s len %s -> %s (текст UTF-16 len=%s)",
                e.type,
                off,
                ln,
                new_len,
                t_u16,
            )
            e = _entity_with_offset_length(e, off, new_len)
        if not _is_valid_entity_for_send(e):
            logger.warning(
                "Пропущена невалидная entity type=%s (нет обязательных полей для Telegram API)",
                e.type,
            )
            continue
        out.append(e)
    return out or None


# Плейсхолдеры для приветственного сообщения (админ подставляет в текст)
WELCOME_PLACEHOLDERS = {
    "{first_name}": "имя пользователя (как в Telegram)",
    "{full_name}": "полное имя пользователя",
    "{username}": "username без @ (или пусто, если нет)",
}


def apply_welcome_placeholders(
    text: str,
    first_name: str,
    full_name: Optional[str] = None,
    username: Optional[str] = None,
    entities: Optional[List[MessageEntity]] = None,
) -> Tuple[str, Optional[List[MessageEntity]]]:
    """
    Подставляет в текст приветствия имя/username пользователя и корректирует entities.

    Плейсхолдеры: {first_name}, {full_name}, {username}
    """
    replacements = [
        ("{first_name}", first_name or ""),
        ("{full_name}", (full_name or first_name or "").strip()),
        ("{username}", (username or "").strip()),
    ]

    result_text = text
    result_entities: Optional[List[MessageEntity]] = list(entities) if entities else None

    for placeholder, value in replacements:
        while placeholder in result_text:
            start_py = result_text.find(placeholder)
            if start_py == -1:
                break

            ph_u16_start = _python_slice_to_utf16_offset(result_text, start_py)
            ph_u16_old_len = _utf16_len(placeholder)
            ph_u16_end = ph_u16_start + ph_u16_old_len
            val_u16_len = _utf16_len(value)
            delta_u16 = val_u16_len - ph_u16_old_len

            result_text = result_text.replace(placeholder, value, 1)

            if result_entities and delta_u16 != 0:
                new_entities: List[MessageEntity] = []
                for e in result_entities:
                    e_end = e.offset + e.length
                    if e_end <= ph_u16_start:
                        new_entities.append(e)
                    elif e.offset >= ph_u16_end:
                        new_entities.append(
                            _entity_with_offset_length(e, e.offset + delta_u16, e.length)
                        )
                    else:
                        new_offset = e.offset if e.offset < ph_u16_start else ph_u16_start + val_u16_len
                        new_length = max(0, e.length + delta_u16)
                        new_entities.append(
                            _entity_with_offset_length(e, new_offset, new_length)
                        )
                result_entities = new_entities

    result_entities = sort_and_sanitize_entities(result_text, result_entities)
    return result_text, result_entities


def resolve_button_url(
    url: str,
    first_name: str = "",
    full_name: Optional[str] = None,
    username: Optional[str] = None,
) -> Optional[str]:
    """Подставляет плейсхолдеры в URL кнопки и проверяет валидность."""
    if not url or not url.strip():
        return None
    raw = url.strip()

    if raw.startswith("@"):
        username_only = raw.lstrip("@").strip()
        if not username_only:
            return None
        return f"https://t.me/{username_only}"

    resolved, _ = apply_welcome_placeholders(
        raw,
        first_name or "",
        (full_name or first_name or "").strip(),
        (username or "").strip(),
        None,
    )
    if "{" in resolved or "}" in resolved:
        return None

    resolved = resolved.strip()
    if not resolved or any(ch.isspace() for ch in resolved):
        return None

    lower = resolved.lower()
    if lower.startswith("//"):
        resolved = "https:" + resolved
        lower = resolved.lower()
    resolved = re.sub(r"^(https?://)/+", r"\1", resolved, flags=re.IGNORECASE)
    lower = resolved.lower()

    allowed = ("http://", "https://", "tg://")
    if not any(lower.startswith(s) for s in allowed):
        return None
    if lower.startswith(("http://", "https://")):
        parts = urlsplit(resolved)
        if not parts.netloc or "@" in parts.netloc:
            return None
    return resolved


def extract_channel_links(
    text: str,
    entities: Optional[List] = None,
    entities_json: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Извлечение ссылок на каналы и боты из текста сообщения."""
    channels = []

    if entities_json and not entities:
        try:
            entities_data = json.loads(entities_json)
            entities = entities_data
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Ошибка парсинга entities_json: {e}")
            return channels

    if not entities or not text:
        return channels

    for entity in entities:
        if isinstance(entity, dict):
            entity_type = entity.get("type")
            entity_offset = entity.get("offset", 0)
            entity_length = entity.get("length", 0)
            entity_url = entity.get("url")
        else:
            entity_type = entity.type
            entity_offset = entity.offset
            entity_length = entity.length
            entity_url = getattr(entity, "url", None)

        if entity_type == "url":
            url = text[entity_offset:entity_offset + entity_length]
            if "t.me/" in url:
                url_part = url.split("t.me/")[-1].split("?")[0]
                if url_part.startswith("+"):
                    channels.append((url_part, "channel_invite"))
                else:
                    username = url_part.split("/")[0].replace("@", "")
                    if username:
                        channels.append((username, "channel"))
            elif url.startswith("@"):
                channels.append((url[1:], "bot"))
        elif entity_type == "mention":
            username = text[entity_offset + 1:entity_offset + entity_length]
            channels.append((username, "bot"))
        elif entity_type == "text_link":
            if entity_url and "t.me/" in entity_url:
                url_part = entity_url.split("t.me/")[-1].split("?")[0]
                if url_part.startswith("+"):
                    channels.append((url_part, "channel_invite"))
                else:
                    username = url_part.split("/")[0].replace("@", "")
                    if username:
                        channels.append((username, "channel"))

    return list(set(channels))


def parse_entities_from_json(entities_json: Optional[str]) -> Optional[List[MessageEntity]]:
    """Преобразование entities из JSON в объекты MessageEntity."""
    if not entities_json:
        return None

    try:
        entities_data = json.loads(entities_json)
        entities = []
        for entity_data in entities_data:
            entity_type = entity_data.get("type")
            if entity_type == "custom_emoji" and not entity_data.get("custom_emoji_id"):
                logger.warning(
                    "Пропущена entity custom_emoji без custom_emoji_id (offset=%s)",
                    entity_data.get("offset"),
                )
                continue
            entity_kwargs = {
                "type": entity_type,
                "offset": int(entity_data.get("offset", 0)),
                "length": int(entity_data.get("length", 0)),
            }
            if entity_data.get("url"):
                entity_kwargs["url"] = entity_data["url"]
            if entity_data.get("language") is not None:
                entity_kwargs["language"] = entity_data["language"]
            if entity_data.get("custom_emoji_id") is not None:
                entity_kwargs["custom_emoji_id"] = entity_data["custom_emoji_id"]
            if entity_data.get("user") is not None:
                entity_kwargs["user"] = entity_data["user"]

            entity = MessageEntity(**entity_kwargs)
            if not _is_valid_entity_for_send(entity):
                logger.warning("Пропущена невалидная entity type=%s после парсинга JSON", entity_type)
                continue
            entities.append(entity)

        logger.debug(f"Распарсено {len(entities)} entities из JSON")
        return entities
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Ошибка парсинга entities_json: {e}")
        logger.error(f"Проблемный JSON: {entities_json[:200] if entities_json else 'None'}...")
        return None


def entities_to_html(text: str, entities: Optional[List[MessageEntity]]) -> str:
    """Конвертирует текст с entities в HTML-форматированный текст."""
    if not entities or not text:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def get_escaped_offset_from_u16(u16_offset: int) -> int:
        py_end = _utf16_units_prefix_to_python_end(text, u16_offset)
        pos = 0
        for i, char in enumerate(text):
            if i >= py_end:
                return pos
            if char == "&":
                pos += 5
            elif char == "<":
                pos += 4
            elif char == ">":
                pos += 4
            else:
                pos += 1
        return pos

    def get_escaped_length_u16(start_u16: int, length_u16: int) -> int:
        return get_escaped_offset_from_u16(start_u16 + length_u16) - get_escaped_offset_from_u16(
            start_u16
        )

    sorted_entities = sorted(entities, key=lambda e: (e.offset, -e.length), reverse=True)

    html_text = escaped_text
    for entity in sorted_entities:
        start = get_escaped_offset_from_u16(int(entity.offset))
        length = get_escaped_length_u16(int(entity.offset), int(entity.length))
        end = start + length

        if start < 0 or end > len(html_text) or start >= end:
            continue

        entity_text = html_text[start:end]

        if entity.type == "bold":
            replacement = f"<b>{entity_text}</b>"
        elif entity.type == "italic":
            replacement = f"<i>{entity_text}</i>"
        elif entity.type == "underline":
            replacement = f"<u>{entity_text}</u>"
        elif entity.type == "strikethrough":
            replacement = f"<s>{entity_text}</s>"
        elif entity.type == "code":
            replacement = f"<code>{entity_text}</code>"
        elif entity.type == "pre":
            replacement = f"<pre>{entity_text}</pre>"
        elif entity.type == "text_link" and hasattr(entity, "url") and entity.url:
            url = str(entity.url).replace("&", "&amp;").replace('"', "&quot;")
            replacement = f'<a href="{url}">{entity_text}</a>'
        elif entity.type == "url":
            replacement = f'<a href="{entity_text}">{entity_text}</a>'
        else:
            replacement = entity_text

        html_text = html_text[:start] + replacement + html_text[end:]

    return html_text
