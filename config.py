import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")
PUBLIC_CHANNEL_ID = os.getenv("PUBLIC_CHANNEL_ID", "")
COMPLAINT_CHANNEL_ID = os.getenv("COMPLAINT_CHANNEL_ID", "")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/telegram")
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "https://mocktestbot.github.io/Webapp01/?test_id=")

DEFAULT_POSITIVE_MARK = 2.0
DEFAULT_NEGATIVE_MARK = 0.25
