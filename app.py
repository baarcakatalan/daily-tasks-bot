import asyncio
import threading
import os
from flask import Flask
import daily_bot  # اگر فایلت daily_bot2.py هست، اینجا بنویس: import daily_bot2 as daily_bot

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

# --- اجرای ربات در یک ترد جداگانه بدون تداخل event loop ---
def run_bot():
    asyncio.run(daily_bot.main_async())

if __name__ == '__main__':
    print("🚀 Starting Telegram bot and Flask server...")

    # اجرای ربات در ترد جدا تا با Flask تداخل نداشته باشد
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)







