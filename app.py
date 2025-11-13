from flask import Flask
import os
import asyncio
import daily_bot  # اگه اسم فایلت daily_bot.py هست همین رو daily_bot کن

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

async def start_bot():
    print("🚀 Starting Telegram bot...")
    await daily_bot.main_async()  # تابع async در فایل daily_bot2.py

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    app.run(host='0.0.0.0', port=port)





