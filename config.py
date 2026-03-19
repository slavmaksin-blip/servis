"""
Bot configuration loaded from environment variables / .env file.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Check your .env file."
        )
    return value


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
BOT_TOKEN: str = _require("BOT_TOKEN")
ADMIN_IDS: list = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

# Channel ID/username for subscription check (e.g. "@mychannel" or "-100123456789")
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")

# ---------------------------------------------------------------------------
# SMSSend
# ---------------------------------------------------------------------------
SMSSEND_API_URL: str = "http://47.236.91.242:20003"
SMSSEND_ACCOUNT: str = os.getenv("SMSSEND_ACCOUNT", "")
SMSSEND_PASSWORD: str = os.getenv("SMSSEND_PASSWORD", "")

# ---------------------------------------------------------------------------
# MailBuy (AnyMessage Shop)
# ---------------------------------------------------------------------------
MAILBUY_API_URL: str = "https://api.anymessage.shop"
MAILBUY_TOKEN: str = os.getenv("MAILBUY_TOKEN", "")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot.db")
