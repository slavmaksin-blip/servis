import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# SMSSEND API
SMSSEND_API_URL = os.getenv("SMSSEND_API_URL", "https://smssend.ch/api")
SMSSEND_ACCOUNT = os.getenv("SMSSEND_ACCOUNT", "")
SMSSEND_PASSWORD = os.getenv("SMSSEND_PASSWORD", "")

# MAILBUY API
MAILBUY_API_URL = os.getenv("MAILBUY_API_URL", "https://api.anymessage.shop")
MAILBUY_TOKEN = os.getenv("MAILBUY_TOKEN", "")

# Admin IDs (comma-separated)
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]
