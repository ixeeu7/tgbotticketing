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

# اپلیکیشن ربات را می‌سازیم (بدون استارت polling)
telegram_app = build_application()

# آدرس پایه سرویس – Render به صورت خودکار متغیر RENDER_EXTERNAL_URL را می‌دهد
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://tgbotticketing.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

# ثبت webhook در تلگرام
def set_webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable not set")
        return
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={WEBHOOK_URL}"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info(f"✅ Webhook registered successfully at {WEBHOOK_URL}")
        else:
            logger.error(f"❌ Failed to set webhook: {resp.text}")
    except Exception as e:
        logger.exception("Exception while setting webhook")

# صفحه اصلی برای سلامت
@app.route('/', methods=['GET'])
def home():
    return "ربات WooCommerce (webhook mode) در حال اجرا است.", 200

# اندپوینت webhook
@app.route(WEBHOOK_PATH, methods=['POST'])
async def webhook():
    try:
        update_data = request.get_json(force=True)
        from telegram import Update
        update = Update.de_json(update_data, telegram_app.bot)
        # پردازش آسنکرون
        await telegram_app.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.exception("Error in webhook handler")
        return "Error", 500

# در زمان شروع برنامه، webhook را ثبت می‌کنیم
set_webhook()

if __name__ == "__main__":
    # برای تست لوکال (اختیاری)
    app.run(port=5000, debug=True)
