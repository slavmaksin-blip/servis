import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(i.strip())
    for i in os.getenv("ADMIN_IDS", "").split(",")
    if i.strip().isdigit()
]

SMSSEND_API_KEY: str = os.getenv("SMSSEND_API_KEY", "")
SMSSEND_API_URL: str = os.getenv("SMSSEND_API_URL", "https://sms-send.cc/api")

MAILBUY_API_KEY: str = os.getenv("MAILBUY_API_KEY", "")
MAILBUY_API_URL: str = os.getenv("MAILBUY_API_URL", "https://api.mailbuy.cc")

DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/bot.db")
