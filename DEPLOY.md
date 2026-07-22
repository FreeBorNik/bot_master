# Деплой bot_master

Multi-bot runner: один процесс обслуживает все child-боты из реестра `bot_sender`.

## Требования

- Python 3.10+
- Работающий `bot_sender` с заполненной таблицей `recipient_bots`
- Доступ к файлам:
  - `bot_sender/data/bot_sender.db`
  - `bot_sender/data/encryption.key`
  - `bot_sender/data/recipients/*.db` (child SQLite)

## Установка

```bash
cd /opt/bot_master
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install aiogram3-calendar==0.1.2 --no-deps
cp .env.example .env
# отредактировать .env
```

## Переменные окружения (.env)

| Переменная | Описание |
|------------|----------|
| `SENDER_DB_PATH` | Абсолютный путь к `bot_sender.db` |
| `SENDER_ENCRYPTION_KEY` | Абсолютный путь к `encryption.key` |
| `RECIPIENTS_DB_DIR` | Опционально: база для относительных `db_path` в `recipient_bots` |
| `LOG_LEVEL` | INFO / DEBUG |
| `LOG_FILE` | Путь к файлу логов |
| `MAILING_DELAY` | Задержка локальных рассылок (сек) |

## Запуск

```bash
python -m bot.main
```

При старте выводится healthcheck-таблица загруженных ботов.

## systemd

```bash
sudo cp deploy/bot_master.service /etc/systemd/system/
# отредактировать пути в unit-файле
sudo systemctl daemon-reload
sudo systemctl enable bot_master
sudo systemctl start bot_master
sudo systemctl status bot_master
```

## Миграция с 20 процессов

**Важно:** нельзя одновременно запускать polling на одном токене в двух процессах.

1. Подготовить `.env` и проверить healthcheck локально (на staging или с остановленными prod-ботами).
2. Остановить все 20 systemd/supervisor unit'ов child-ботов.
3. Запустить `bot_master`.
4. Проверить `/start` и админ-панель в нескольких ботах.
5. `bot_sender` не трогать — рассылки и упаковка работают как раньше.

## Добавление нового child-бота

1. Зарегистрировать бота в `bot_sender` (recipients).
2. Убедиться, что child SQLite содержит таблицу `admins` с ID администраторов.
3. Перезапустить `bot_master`: `sudo systemctl restart bot_master`.

## Чеклист тестирования

| Сценарий | Ожидание |
|----------|----------|
| `/start` в bot_1 и bot_2 одним user_id | Разные welcome, разные FSM |
| Админ-панель | Доступ только если user в `admins` child DB |
| Рассылка из bot_sender | Работает как раньше |
| MailingScheduler (локальная рассылка) | Каждый scheduler шлёт только своим users |
| Блокировка бота | `is_in_bot=0` только в DB этого бота |
| Новый бот в recipient_bots | После restart появляется в healthcheck |

## Логи

Логи содержат префикс `[bot_name (@username)]` для идентификации child-бота.

```bash
tail -f logs/bot_master.log
journalctl -u bot_master -f
```
