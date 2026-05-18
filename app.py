import os
import logging
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# توکن ربات را از متغیر محیطی بخوانید
TOKEN = os.environ.get("BOT_TOKEN", "")

@app.route('/', methods=['GET'])
def home():
    return "ربات در حال اجراست", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # دریافت داده از تلگرام
        update_data = request.get_json(force=True)
        logger.info(f"دریافت درخواست: {update_data}")

        # استخراج chat_id و متن پیام
        chat_id = None
        text = None
        if 'message' in update_data:
            chat_id = update_data['message'].get('chat', {}).get('id')
            text = update_data['message'].get('text', '')

        # پاسخ ساده (برای تست)
        if chat_id and TOKEN:
            import requests
            send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(send_url, json={
                'chat_id': chat_id,
                'text': 'ربات فعال است و پیام شما را دریافت کرد!'
            })
        return "OK", 200
    except Exception as e:
        logger.exception("خطا در پردازش وب‌هوک")
        return "Internal Server Error", 500

# تنظیم وب‌هوک در زمان استارت (فقط در پروسه اصلی)
def set_webhook():
    import requests
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://tgbotticketing.onrender.com")
    webhook_url = f"{render_url}/webhook"
    api_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info(f"✅ Webhook تنظیم شد: {webhook_url}")
        else:
            logger.error(f"❌ خطا در تنظیم وب‌هوک: {resp.text}")
    except Exception as e:
        logger.exception("Exception while setting webhook")

if __name__ != '__main__':
    set_webhook()
