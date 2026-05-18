import os
import threading
from flask import Flask
from bot import main as bot_main

app = Flask(__name__)

@app.route('/')
def home():
    return "ربات WooCommerce من در حال اجراست!", 200

def run_bot():
    bot_main()

# وقتی برنامه روی Render اجرا می‌شود (نه در حالت local)
if __name__ != '__main__':
    threading.Thread(target=run_bot).start()