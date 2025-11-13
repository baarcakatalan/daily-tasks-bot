from flask import Flask
import os
import asyncio
import daily_bot  # فایل ربات

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

async def main():
    print("🚀 Starting Telegram bot...")
    # اجرای هم‌زمان Flask و ربات در یک حلقه
    bot_task = asyncio.create_task(daily_bot.main_async())

    port = int(os.environ.get('PORT', 10000))
    # Flask را در یک ترد جدا راه‌اندازی می‌کنیم ولی در همان event loop
    loop = asyncio.get_running_loop()
    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()

    await bot_task  # منتظر اجرای ربات بمان

if __name__ == '__main__':
    asyncio.run(main())







