from flask import Flask
import os
import daily_bot  # ایمپورت ربات

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

if __name__ == '__main__':
    # فقط فلاسک رو اجرا کن - ربات در فایل جداگانه خودش اجرا میشه
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)







