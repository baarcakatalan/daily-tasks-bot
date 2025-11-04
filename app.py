from flask import Flask
import os
import threading
import daily_bot  # اضافه کن تا فایل daily_bot.py ایمپورت بشه

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

def run_bot():
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    daily_bot.main()  # اجرای تابع اصلی ربات

if __name__ == '__main__':
    # اجرای ربات در thread جدا
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

