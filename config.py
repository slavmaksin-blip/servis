import os
from dotenv import load_dotenv

load_dotenv()

# Bot
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

# Channel
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "@your_channel")
CHANNEL_URL: str = os.getenv("CHANNEL_URL", "https://t.me/your_channel")

# SMSSEND API
SMSSEND_ACCOUNT: str = os.getenv("SMSSEND_ACCOUNT", "")
SMSSEND_PASSWORD: str = os.getenv("SMSSEND_PASSWORD", "")
SMSSEND_API_URL: str = "https://smssend.ch/api/"

# MailBuy API
MAILBUY_TOKEN: str = os.getenv("MAILBUY_TOKEN", "")
MAILBUY_API_URL: str = "https://mailbuy.cc/api"

# CryptoBot
CRYPTOBOT_TOKEN: str = os.getenv("CRYPTOBOT_TOKEN", "")
CRYPTOBOT_API_URL: str = "https://pay.crypt.bot/api"

# xRocket
XROCKET_TOKEN: str = os.getenv("XROCKET_TOKEN", "")
XROCKET_API_URL: str = "https://pay.xrocket.tg"

# Database
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "database.db")

# Subscription prices (USD)
SUBSCRIPTION_PRICES: dict = {
    1: 1.99,
    3: 4.99,
    15: 14.99,
}

# MailBuy markup multiplier
MAILBUY_MARKUP: float = 3.0

# Supported SMS countries
SMS_COUNTRIES: dict = {
    "🇨🇭 Швейцария": {"code": "CH", "prefix": "+41", "digits": 9},
    "🇩🇪 Германия": {"code": "DE", "prefix": "+49", "digits": 10},
}
