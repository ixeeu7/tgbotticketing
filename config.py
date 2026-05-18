import os

# متغیرهای تلگرام
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMINS = [int(x.strip()) for x in os.environ.get("ADMINS", "").split(",") if x.strip()]

# متغیرهای ووکامرس
WC_URL = os.environ.get("WC_URL", "")
WC_CONSUMER_KEY = os.environ.get("WC_CONSUMER_KEY", "")
WC_CONSUMER_SECRET = os.environ.get("WC_CONSUMER_SECRET", "")

# دیتابیس
DB_NAME = "orders_cache.db"

# حالت دیباگ
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
