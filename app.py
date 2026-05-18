import os
import threading
import logging
from flask import Flask
from bot import main as bot_main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "ربات WooCommerce من در حال اجراست!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    try:
        logger.info("Starting bot main function...")
        # بررسی وجود توکن
        token = os.environ.get("BOT_TOKEN")
        if not token:
            logger.error("BOT_TOKEN environment variable not set!")
            return
        logger.info("BOT_TOKEN found, starting bot...")
        bot_main()
    except Exception as e:
        logger.exception(f"Failed to start bot: {e}")

# فقط در صورتی که این فایل به عنوان main اجرا نشده باشد (یعنی در محیط گانیکورن)
# از ترد استفاده می‌کنیم. در غیر این صورت، خود گانیکورن یک بار تابع run_bot را صدا می‌زند.
if __name__ != '__main__':
    # تاخیر کوتاه برای اطمینان از آماده شدن محیط
    import time
    time.sleep(2)
    threading.Thread(target=run_bot, daemon=True).start()
else:
    # برای اجرای لوکال (python app.py)
    run_bot()
