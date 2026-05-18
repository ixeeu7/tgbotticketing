import os
import logging
import asyncio
import requests
from flask import Flask, request, jsonify
from bot import build_application, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# یک بار دیتابیس را می‌سازیم
init_db()

# اپلیکیشن ربات را می‌سازیم (همان که در bot.py تعریف شده)
telegram_app = build_application()

# آدرس پایه سرویس (Render به صورت خودکار این متغیر را می‌دهد)
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://tgbotticketing.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

def set_webhook():
    """تنظیم وب‌هوک در تلگرام (فقط یک بار در هنگام استارت سرور)"""
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

# فقط در صورتی که در محیط گانیکورن (Render) هستیم، وب‌هوک را تنظیم کن
# برای جلوگیری از ثبت چندباره، از یک متغیر محیطی یا فایل لاک استفاده نمی‌کنیم.
# گانیکورن فقط یک بار این کد را اجرا می‌کند (در زمان بارگذاری ماژول).
set_webhook()

@app.route('/', methods=['GET'])
def home():
    return "ربات ووکامرس (حالت وب‌هوک) در حال اجرا است.", 200

@app.route(WEBHOOK_PATH, methods=['POST'])
async def webhook():
    try:
        # دریافت داده از تلگرام
        update_data = request.get_json(force=True)
        from telegram import Update
        update = Update.de_json(update_data, telegram_app.bot)
        # پردازش آسنکرون درخواست
        await telegram_app.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.exception("خطا در پردازش وب‌هوک")
        return "Internal Server Error", 500

if __name__ == "__main__":
    # برای تست لوکال (اختیاری)
    app.run(port=5000, debug=True)
