import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]

SMTP_HOST: str = os.getenv("SMTP_HOST", "send.smtp.dev")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.environ["SMTP_USER"]
SMTP_PASS: str = os.environ["SMTP_PASS"]
