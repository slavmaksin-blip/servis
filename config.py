import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]

# SMTP defaults (can be overridden at runtime via /smtp command)
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.mail.ch")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER: str = os.environ["SMTP_USER"]
SMTP_PASS: str = os.environ["SMTP_PASS"]

# Comma-separated list of Telegram user IDs that may use /smtp
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]
