# Multi-Tool & Shop — Telegram Bot

A feature-rich Telegram bot built with Python 3.10+, aiogram 3.x and SQLite (aiosqlite).

## Features

- **Mandatory channel subscription** — users must subscribe before using the bot
- **Main menu** with photo (`start.png`) and inline buttons
- **Modules**:
  - 📨 SMS — send SMS via SMSSEND API (Switzerland only)
  - 📧 Mailer / 🖥 Screen / 🔗 Proxy — stubs (in development)
- **Shop**:
  - 📧 Buy mail — purchase email accounts via MAILBUY API
  - 🛍 Products — digital goods with unique file delivery (stock management)
- **Profile**:
  - Balance top-up via CryptoBot or xRocket (strict double-credit protection)
  - Subscription plans (1 day / 3 days / 15 days)
  - Promo codes
- **Admin panel** (`/admin`):
  - Ban / Unban users
  - Broadcast (text or photo)
  - Manage categories, products, stock files
  - Manage balances
  - Promo codes management
- **Help section** with Contact Support button (https://t.me/mensorsim)
- **Back to Main Menu** button in every sub-menu
- **FSM** for all multi-step scenarios

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
4. Place your `start.png` image in the project root
5. Run:
   ```bash
   python main.py
   ```

## Environment Variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `ADMIN_ID` | Your Telegram user ID |
| `CHANNEL_ID` | Channel ID for subscription check |
| `CHANNEL_USERNAME` | Channel username (without @) |
| `DATABASE_URL` | SQLite file path (default: `database.db`) |
| `SMSSEND_ACCOUNT` | SMSSEND API account |
| `SMSSEND_PASSWORD` | SMSSEND API password |
| `SMSSEND_API_URL` | SMSSEND base URL |
| `MAILBUY_API_URL` | MAILBUY base URL |
| `MAILBUY_TOKEN` | MAILBUY API token |
| `CRYPTOBOT_TOKEN` | CryptoBot payment token |
| `XROCKET_API_KEY` | xRocket payment API key |
| `MAIL_PRICE_MULTIPLIER` | Price multiplier for mail accounts (default: 3) |

## API Documentation

- **SMSSEND**: `http://47.236.91.242:20003` — account/password auth
- **MAILBUY**: `https://api.anymessage.shop` — Bearer token auth
