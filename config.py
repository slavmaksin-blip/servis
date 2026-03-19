import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
CHANNEL_USERNAME: str = os.getenv("CHANNEL_USERNAME", "")

DATABASE_URL: str = os.getenv("DATABASE_URL", "database.db")

# SMSSEND API
SMSSEND_ACCOUNT: str = os.getenv("SMSSEND_ACCOUNT", "")
SMSSEND_PASSWORD: str = os.getenv("SMSSEND_PASSWORD", "")
SMSSEND_API_URL: str = os.getenv("SMSSEND_API_URL", "http://47.236.91.242:20003")

# MAILBUY API
MAILBUY_API_URL: str = os.getenv("MAILBUY_API_URL", "https://api.anymessage.shop")
MAILBUY_TOKEN: str = os.getenv("MAILBUY_TOKEN", "")

# Payment systems
CRYPTOBOT_TOKEN: str = os.getenv("CRYPTOBOT_TOKEN", "")
XROCKET_API_KEY: str = os.getenv("XROCKET_API_KEY", "")

# Business
MAIL_PRICE_MULTIPLIER: float = float(os.getenv("MAIL_PRICE_MULTIPLIER", "3"))
