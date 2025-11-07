from flask import Flask
import os
import threading
import time
import requests
import daily_bot

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

def run_bot():
    import asyncio
    while True:
        try:
            print("🚀 Starting Telegram bot...")
            asyncio.set_event_loop(asyncio.new_event_loop())
            daily_bot.main()
        except Exception as e:
            print(f"💥 Bot crashed with error: {e}")
            print("⏳ Restarting bot in 10 seconds...")
            time.sleep(10)

def keep_alive():
    url = "https://daily-tasks-bot.onrender.com/health"  # آدرس پروژه‌ی خودت در Render
    while True:
        try:
            requests.get(url)
            print("🔁 Self-ping sent successfully!")
        except Exception as e:
            print(f"⚠️ Self-ping failed: {e}")
        time.sleep(300)  # هر 5 دقیقه

if __name__ == '__main__':
    # Thread برای اجرای ربات
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Thread برای بیدار نگه داشتن سرور
    ping_thread = threading.Thread(target=keep_alive)
    ping_thread.daemon = True
    ping_thread.start()

    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)



