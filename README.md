# Multi-Tool & Shop — Telegram Bot

Многофункциональный Telegram-бот с магазином, SMS-модулем, системой подписок и панелью администратора.

## Стек технологий

- **aiogram 3.2** — асинхронный фреймворк для Telegram Bot API
- **aiosqlite** — асинхронная работа с SQLite
- **aiohttp** — HTTP-клиент для внешних API
- **python-dotenv** — управление переменными окружения

## Структура проекта

```
├── main.py                 # Точка входа
├── config.py               # Конфигурация (токены, цены, API URL)
├── database.py             # Работа с БД (SQLite через aiosqlite)
├── requirements.txt        # Зависимости
├── .env.example            # Пример переменных окружения
├── handlers/
│   ├── start.py            # /start, проверка подписки, регистрация
│   ├── menu.py             # Главное меню, навигация
│   ├── modules.py          # SMS-модуль + заглушки (Mailer, Screen, Proxy)
│   ├── shop.py             # Магазин почты и товаров
│   ├── profile.py          # Профиль, баланс, подписка, промокоды
│   └── admin.py            # Панель администратора
└── utils/
    ├── api.py              # SMSSendAPI, MailBuyAPI
    ├── keyboards.py        # Все inline-клавиатуры
    ├── states.py           # FSM-состояния
    └── validators.py       # Валидаторы входных данных
```

## Установка

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/slavmaksin-blip/servis.git
cd servis
```

### 2. Создайте виртуальное окружение и установите зависимости

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate.bat     # Windows

pip install -r requirements.txt
```

### 3. Настройте переменные окружения

```bash
cp .env.example .env
```

Откройте `.env` и заполните все поля:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Telegram ID администратора |
| `CHANNEL_ID` | ID/username канала (например `@my_channel`) |
| `CHANNEL_URL` | Ссылка на канал |
| `SMSSEND_ACCOUNT` | Аккаунт [SMSSEND](https://smssend.ch) |
| `SMSSEND_PASSWORD` | Пароль SMSSEND |
| `MAILBUY_TOKEN` | API-токен [MailBuy](https://mailbuy.cc) |
| `CRYPTOBOT_TOKEN` | Токен [CryptoBot](https://t.me/CryptoBot) |
| `XROCKET_TOKEN` | Токен [xRocket](https://t.me/xRocketBot) |
| `DATABASE_PATH` | Путь к файлу БД (по умолчанию `database.db`) |

### 4. Запустите бота

```bash
python main.py
```

## Функциональность

### Пользователи
- `/start` — регистрация, проверка подписки на канал
- **Модули** — SMS (Швейцария, Германия), Mailer, Screen, Proxy (в разработке)
- **Магазин** — покупка почтовых ящиков (через MailBuy API с наценкой ×3), товары по категориям
- **Профиль** — баланс, подписка (1/3/15 дней), пополнение через CryptoBot/xRocket, промокоды

### Администратор
Команда `/admin` открывает панель с возможностями:
- **Баны/разбаны** пользователей по ID
- **Рассылка** текста или фото всем пользователям
- **Управление категориями и товарами**
- **Выдача/списание баланса** пользователям
- **Просмотр списка** пользователей с балансом
- **Статистика** (всего пользователей, активных подписок)
- **Создание промокодов** с настройкой суммы и количества использований

## Цены подписки

| Срок | Цена |
|---|---|
| 1 день | $1.99 |
| 3 дня | $4.99 |
| 15 дней | $14.99 |
