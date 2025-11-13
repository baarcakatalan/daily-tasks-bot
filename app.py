from flask import Flask
import os
import threading
import asyncio
import daily_bot  # اگه اسم فایل رباتت daily_bot2.py هست، اینجا هم daily_bot2 بنویس

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

def run_bot():
    print("🚀 Starting Telegram bot...")
    asyncio.run(daily_bot.main_async())

if __name__ == '__main__':
    # اجرای ربات در ترد جداگانه تا Flask همزمان کار کنه
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)






