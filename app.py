from flask import Flask
import os
import asyncio
import threading
import daily_bot  # یا daily_bot2 اگر اسم فایلت اینه

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

def run_bot():
    asyncio.new_event_loop().run_until_complete(daily_bot.main_async())

if __name__ == '__main__':
    # اجرای ربات در ترد جداگانه
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)







