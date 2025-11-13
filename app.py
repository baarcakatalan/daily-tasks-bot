from flask import Flask
import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import jdatetime
import json
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

app = Flask(__name__)

# ============================ 
# کدهای ربات (از daily_bot.py)
# ============================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# حالت‌های مکالمه
MAIN_MENU, MANAGE_TASKS_MENU, ADD_TASK_DATE_SELECT, ADD_TASK_CONTENT, \
EDIT_TASK_SELECT, EDIT_TASK_ACTION, DELETE_TASK_SELECT, VIEW_TASKS_DATE_SELECT, \
TASK_CHECKLIST, STATS_PERIOD = range(10)

DB_FILE = 'users_data.json'
TOKEN = os.environ.get('BOT_TOKEN', '')

class Database:
    @staticmethod
    def load():
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading database: {e}")
        return {}
    
    @staticmethod
    def save(data):
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving database: {e}")

users_db = Database.load()

def get_three_calendars():
    now = datetime.now()
    jdate = jdatetime.datetime.now()
    
    hijri_date = "۱۴۴۵/۰۶/۲۳"
    
    persian_days = {
        'Saturday': 'شنبه', 'Sunday': 'یکشنبه', 'Monday': 'دوشنبه',
        'Tuesday': 'سه‌شنبه', 'Wednesday': 'چهارشنبه',
        'Thursday': 'پنجشنبه', 'Friday': 'جمعه'
    }
    
    english_day = now.strftime('%A')
    persian_day = persian_days.get(english_day, english_day)
    
    return f"""
📅 **تاریخ امروز:**

🇮🇷 **شمسی:** {jdate.strftime('%Y/%m/%d')} - {jdate.strftime('%A')}
🌍 **میلادی:** {now.strftime('%Y-%m-%d')} - {persian_day}
🌙 **قمری:** {hijri_date} - الجمعة
"""

def get_date_key(date_obj=None):
    if date_obj is None:
        date_obj = datetime.now()
    return date_obj.strftime("%Y-%m-%d")

# همه توابع ربات اینجا می‌آیند (start, show_main_menu, etc.)
# [بقیه کدهای ربات رو اینجا کپی کنین]

async def start(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    logging.info(f"User {user_id} ({user_name}) started the bot")
    
    if user_id not in users_db:
        users_db[user_id] = {
            "daily_tasks": [],
            "dated_tasks": {},
            "checklist_responses": {},
            "created_at": get_date_key(),
            "user_name": user_name
        }
        Database.save(users_db)
    
    welcome_text = f"""
👋 **سلام {user_name} عزیز!**

راستش من برای این اینجام تا هم توی مصرف کاغذ صرفه جویی بشه هم چیزی از قلم نیفته
هر کاری که می‌خوای توی هر روزی انجام بدی رو بنویس 
نگران نباش اگه چیزی از قلم افتاد میتونی دوباره بهش اضافه کنی یا ویرایش و حذف کنی
همچنین امکاناتی مثل چک لیست و گزارش گیری هم برای شما در نظر گرفته شده

🏠 **منوی اصلی شامل:**

📅 **برنامه امروز** - مشاهده کارهای امروز
🔧 **مدیریت کارها** - اضافه/ویرایش/حذف کارها
📋 **مشاهده برنامه** - کارهای تاریخ مشخص
✅ **چک لیست امروز** - ثبت انجام کارها
📊 **آمار و گزارش** - عملکرد شما

💡 **اول برو به «🔧 مدیریت کارها» و کارهایت رو اضافه کن!**
"""
    await update.message.reply_text(welcome_text, reply_markup=ReplyKeyboardRemove())
    return await show_main_menu(update, context)

async def show_main_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("📅 برنامه امروز"), KeyboardButton("🔧 مدیریت کارها")],
        [KeyboardButton("📋 مشاهده برنامه کاری"), KeyboardButton("✅ چک لیست امروز")],
        [KeyboardButton("📊 آمار و گزارش")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🏠 **منوی اصلی**\n\n"
        "لطفاً یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=reply_markup
    )
    return MAIN_MENU

# [بقیه توابع رو اینجا کپی کنین...]

# ============================
# راه‌اندازی ربات
# ============================

def setup_handlers(application):
    """تنظیم handlerهای ربات"""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.Regex("^🏠 منوی اصلی$"), show_main_menu),
                MessageHandler(filters.Regex("^📅 برنامه امروز$"), show_today_tasks),
                MessageHandler(filters.Regex("^🔧 مدیریت کارها$"), show_manage_tasks_menu),
                MessageHandler(filters.Regex("^📋 مشاهده برنامه کاری$"), view_tasks_select_date),
                MessageHandler(filters.Regex("^✅ چک لیست امروز$"), show_checklist),
                MessageHandler(filters.Regex("^📊 آمار و گزارش$"), show_stats)
            ],
            # [بقیه states رو اینجا اضافه کنین]
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("today", show_today_tasks))
    application.add_handler(CommandHandler("add", lambda u, c: select_year(u, c, "add")))
    application.add_handler(CommandHandler("view", view_tasks_select_date))
    application.add_handler(CommandHandler("checklist", show_checklist))
    application.add_handler(CommandHandler("stats", show_stats))

def run_bot():
    """اجرای ربات در background"""
    print("🚀 Starting Telegram Bot...")
    
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN not set!")
        return
    
    # ایجاد application
    application = Application.builder().token(TOKEN).build()
    
    # تنظیم handlerها
    setup_handlers(application)
    
    # اجرای ربات
    try:
        application.run_polling()
    except Exception as e:
        print(f"❌ Bot error: {e}")

# ============================
# Routes فلاسک
# ============================

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Render!"

@app.route('/health')
def health():
    return "✅ Bot is healthy!"

# ============================
# راه‌اندازی اصلی
# ============================

if __name__ == '__main__':
    # اجرای ربات در thread جداگانه
    import threading
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # اجرای Flask
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)








