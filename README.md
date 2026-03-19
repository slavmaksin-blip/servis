# Servis Bot

Многофункциональный Telegram-бот на Python (aiogram 3.x).

## Возможности

- 🔧 **Модули**: SMS-рассылка (SMSSEND API), Mailer, Screen, Proxy
- 🛒 **Магазин**: покупка email-аккаунтов (mailbuy API), цифровые товары
- 👤 **Профиль**: баланс ($), подписка, промокоды, пополнение (CryptoBot / xRocket)
- 🔐 **Админ-панель**: бан/разбан, рассылка, управление товарами, промокоды, балансы

## Быстрый старт

1. Клонируйте репозиторий и установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Создайте файл `.env` (пример в `.env.example`):
   ```env
   BOT_TOKEN=your_bot_token
   ADMIN_ID=123456789
   CHANNEL_ID=@your_channel
   SMSSEND_API_KEY=your_key
   MAILBUY_API_KEY=your_key
   CRYPTOBOT_TOKEN=your_token
   XROCKET_TOKEN=your_token
   ```

3. Запустите бота:
   ```bash
   python main.py
   ```

## Структура проекта

```
├── main.py              # Точка входа
├── .env                 # Переменные окружения (не в git)
├── .env.example         # Пример .env
├── requirements.txt     # Зависимости
├── start.png            # Фото для главного меню
├── database.db          # SQLite база данных (создаётся автоматически)
├── database/
│   ├── __init__.py
│   └── db.py            # Работа с БД (SQLite / aiosqlite)
├── handlers/
│   ├── __init__.py
│   ├── states.py        # FSM-состояния
│   ├── start.py         # /start, подписка на канал
│   ├── modules.py       # Модули (SMS, Mailer, Screen, Proxy)
│   ├── shop.py          # Магазин (почта, товары)
│   ├── profile.py       # Профиль, баланс, подписка, промокоды
│   ├── admin.py         # Админ-панель (/admin)
│   └── help.py          # Помощь
└── utils/
    ├── __init__.py
    ├── keyboards.py     # Клавиатуры (inline + reply)
    ├── smssend.py       # SMSSEND API
    ├── mailbuy.py       # mailbuy API
    └── cryptobot.py     # CryptoBot / xRocket API
```

## БД

Используется SQLite (файл `database.db`). Создаётся автоматически при первом запуске.

Таблицы:
- `users` — пользователи (баланс, подписка, бан)
- `promo_codes` / `promo_uses` — промокоды
- `categories` / `products` — магазин
- `purchases` — история покупок

## Требования

- Python 3.10+
- Зависимости: см. `requirements.txt`

## API

| Сервис | Переменная | Документация |
|--------|-----------|-------------|
| Telegram Bot | `BOT_TOKEN` | [BotFather](https://t.me/BotFather) |
| SMSSEND | `SMSSEND_API_KEY` | smssend.su |
| mailbuy | `MAILBUY_API_KEY` | mailbuy.ru |
| CryptoBot | `CRYPTOBOT_TOKEN` | [@CryptoBot](https://t.me/CryptoBot) |
| xRocket | `XROCKET_TOKEN` | [@xRocket](https://t.me/xRocket) |
