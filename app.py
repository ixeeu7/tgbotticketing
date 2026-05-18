import os
import logging
import asyncio
from flask import Flask, request
from bot import build_application, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# مقداردهی اولیه دیتابیس
init_db()

# ساخت اپلیکیشن ربات (فقط handlerها)
telegram_app = build_application()

# ایجاد یک حلقه رویداد مستقل برای ربات
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# مقداردهی اولیه و استارت اپلیکیشن (این کارها فقط یک بار در هنگام راه‌اندازی انجام شود)
def init_bot():
    try:
        loop.run_until_complete(telegram_app.initialize())
        loop.run_until_complete(telegram_app.start())
        logger.info("✅ ربات با موفقیت مقداردهی اولیه شد")
    except Exception as e:
        logger.exception("خطا در مقداردهی اولیه ربات")

# اجرای مقداردهی اولیه
init_bot()

BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://tgbotticketing.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

def set_webhook():
    import requests
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN تنظیم نشده است")
        return
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={WEBHOOK_URL}"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info(f"✅ وب‌هوک با موفقیت در {WEBHOOK_URL} ثبت شد")
        else:
            logger.error(f"❌ خطا در ثبت وب‌هوک: {resp.text}")
    except Exception as e:
        logger.exception("خطا در هنگام ثبت وب‌هوک")

set_webhook()

@app.route('/', methods=['GET'])
def home():
    return "ربات ووکامرس (حالت وب‌هوک) در حال اجرا است.", 200

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    try:
        update_data = request.get_json(force=True)
        # پردازش درخواست با استفاده از حلقه رویداد موجود
        future = asyncio.run_coroutine_threadsafe(
            telegram_app.process_update(update_data),
            loop
        )
        future.result(timeout=5)  # حداکثر 5 ثانیه صبر
        return "OK", 200
    except Exception as e:
        logger.exception("خطا در پردازش وب‌هوک")
        return "Internal Server Error", 500
