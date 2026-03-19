# Servis Bot

Многофункциональный Telegram-бот с интеграцией **SMSSEND** и **mailbuy** (AnyMessage Shop) API.

## Возможности

- 📱 **SMS модуль** — отправка SMS через SMSSend API (формат номера `+41XXXXXXXXX`)
- 📧 **Магазин почты** — заказ временных email-адресов через AnyMessage Shop API
- 👤 **Профиль** — просмотр баланса и истории операций
- 🛠 **Админ-панель** — управление пользователями, пополнение баланса, рассылка

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/slavmaksin-blip/servis.git
cd servis

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate   # Windows

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env
# Заполните .env своими данными
```

## Конфигурация (.env)

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
SMSSEND_ACCOUNT=your_account
SMSSEND_PASSWORD=your_password
MAILBUY_TOKEN=your_token
DATABASE_PATH=bot.db
```

## Запуск

```bash
python main.py
```

## Формат номера телефона

SMS-модуль принимает номера в швейцарском формате:

```
+41XXXXXXXXX
```

- `+41` — код страны (Швейцария)
- `XXXXXXXXX` — ровно 9 цифр
- Пример: `+41791234567`

## API

### SMSSend API
- Базовый URL: `http://47.236.91.242:20003`
- Методы: `getbalance`, `sendsms`, `getreport`, `getsms`, `smsjob`

### MailBuy (AnyMessage Shop) API
- Базовый URL: `https://api.anymessage.shop`
- Методы: `user/balance`, `email/quantity`, `email/order`, `email/getmessage`, `email/reorder`, `email/cancel`

## Структура проекта

```
servis/
├── main.py              # Точка входа
├── config.py            # Конфигурация из .env
├── database.py          # SQLite хелперы
├── handlers/
│   ├── admin.py         # Администрирование
│   ├── menu.py          # Навигация главного меню
│   ├── modules.py       # SMS модуль
│   ├── profile.py       # Профиль пользователя
│   ├── shop.py          # Магазин почты
│   └── start.py         # /start и /help
├── utils/
│   ├── api.py           # SMSSEND и MailBuy API клиенты
│   ├── keyboards.py     # Клавиатуры
│   ├── states.py        # FSM состояния
│   └── validators.py    # Валидация ввода
├── requirements.txt
├── .env.example
└── .gitignore
```