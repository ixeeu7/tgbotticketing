import os

# متغیرهای تلگرام
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8986110840:AAE3f_GEf4yXgTQO07OBZUODLT70affs15k")
ADMINS = [int(x.strip()) for x in os.environ.get("ADMINS", "93363020").split(",") if x.strip()]

# متغیرهای ووکامرس
WC_URL = os.environ.get("WC_URL", "")
WC_CONSUMER_KEY = os.environ.get("WC_CONSUMER_KEY", "ck_1e0a83512833dc40d0d0902e005e7a8076c7d1d7")
WC_CONSUMER_SECRET = os.environ.get("WC_CONSUMER_SECRET", "cs_d595e637ccedbfc7b4d18e0355ff682e31ff606d")

# دیتابیس
DB_NAME = "orders_cache.db"

# حالت دیباگ
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
