from flask import Flask
import os
import threading
import daily_bot
import asyncio

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

if __name__ == '__main__':
    # اجرای Flask در thread جدا (برعکس حالت قبلی)
    def run_flask():
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # اجرای ربات در main thread
    print("🤖 ربات فعال شد! (Polling Mode)")
    asyncio.set_event_loop(asyncio.new_event_loop())
    daily_bot.main()


