# servis — Telegram Prank Bot

Шуточный Telegram-бот на [aiogram 3](https://docs.aiogram.dev/) для розыгрышей друзей.
Генерирует стилизованное изображение "истории транзакций" с заметным водяным знаком
**РОЗЫГРЫШ / FAKE**.

## Функционал

| Шаг | Описание |
|-----|----------|
| `/start` | Главное меню с кнопкой **Screen** |
| Screen | Выбор страны: 🇨🇭 Швейцария |
| Страна | Выбор платформы: 🏦 Bank |
| Bank | Ввод названия сервиса |
| Сервис | Ввод суммы списания (CHF) |
| Готово | Бот отправляет PNG со светлым iOS-стилем истории транзакций и водяным знаком |

## Требования

- Python 3.10+
- Зависимости из `requirements.txt`

## Установка и запуск

```bash
# 1. Клонируй репо
git clone https://github.com/slavmaksin-blip/servis.git
cd servis

# 2. Создай виртуальное окружение (рекомендуется)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Создай .env и добавь токен бота
cp .env.example .env
# Открой .env и вставь свой BOT_TOKEN

# 5. Запусти
python -m app.main
```

## Структура проекта

```
servis/
├── app/
│   ├── __init__.py
│   ├── main.py          # точка входа, polling
│   ├── config.py        # загрузка .env
│   ├── states.py        # FSM-состояния (ScreenFlow)
│   ├── keyboards.py     # InlineKeyboard
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py     # /start, главное меню
│   │   └── screen.py    # FSM-цепочка Screen → страна → платформа → сервис → сумма
│   └── services/
│       ├── __init__.py
│       └── prank_image.py   # генерация PNG (Pillow)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |

## Важно

Бот создан исключительно для шуточных розыгрышей. На каждом сгенерированном изображении
присутствует заметный водяной знак **«РОЗЫГРЫШ / FAKE»**, чтобы изображение нельзя было
использовать как настоящий банковский документ.