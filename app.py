import os
import logging
from flask import Flask
import threading
from bot import main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def start_bot():
    logger.info("Starting bot in background thread...")
    main()  # این تابع در bot.py وجود دارد (همان run_polling)

# اجرای ربات در یک ترد جداگانه
threading.Thread(target=start_bot, daemon=True).start()

@app.route('/')
def home():
    return "ربات ووکامرس (حالت Polling) در حال اجرا است.", 200

if __name__ == "__main__":
    app.run(port=5000)
