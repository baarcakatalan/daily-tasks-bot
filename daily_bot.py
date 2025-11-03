import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import jdatetime
import json
import os
import threading
from flask import Flask

# ✅ بخش Flask برای Render
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running!"

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# حالت‌های مکالمه
SETUP_TASKS, MAIN_MENU, ADD_TASK_DATE, ADD_TASK_NAME, COMPLETE_TASKS = range(5)

# دیتابیس
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

# لود دیتابیس
users_db = Database.load()

# توابع کمکی برای تاریخ
def get_all_dates():
    now = datetime.now()
    jdate = jdatetime.datetime.now()
    
    persian_days = {
        'Saturday': 'شنبه',
        'Sunday': 'یکشنبه', 
        'Monday': 'دوشنبه',
        'Tuesday': 'سه‌شنبه',
        'Wednesday': 'چهارشنبه',
        'Thursday': 'پنجشنبه',
        'Friday': 'جمعه'
    }
    
    english_day = now.strftime('%A')
    persian_day = persian_days.get(english_day, english_day)
    
    return f"""
📅 **تاریخ امروز:**

🇮🇷 **شمسی:** {jdate.strftime('%Y/%m/%d')} - {jdate.strftime('%A')}
🌍 **میلادی:** {now.strftime('%Y-%m-%d')} - {persian_day}
"""

def get_date_key():
    return datetime.now().strftime("%Y-%m-%d")

def format_task_list(tasks, show_completion=True):
    if not tasks:
        return "📝 هیچ کاری ثبت نشده"
    
    result = ""
    for i, task in enumerate(tasks, 1):
        if show_completion:
            status = "✅" if task.get("completed", False) else "◻️"
            result += f"{i}. {status} {task['name']}\n"
        else:
            result += f"{i}. {task['name']}\n"
    return result

# دستور start
async def start(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    logging.info(f"User {user_id} ({user_name}) started the bot")
    
    if user_id not in users_db:
        users_db[user_id] = {
            "setup_complete": False,
            "daily_tasks": [],
            "dated_tasks": {},
            "last_active_date": get_date_key(),
            "created_at": get_date_key(),
            "user_name": user_name
        }
        Database.save(users_db)
    
    user_data = users_db[user_id]
    
    if not user_data["setup_complete"]:
        welcome_text = f"""
👋 **سلام {user_name} عزیز!**

📅 **به ربات مدیریت کارهای روزانه خوش اومدی!**

**حالا کارهای روزانه‌ات رو تعریف کن:**
هر کاری که می‌خوای هر روز انجام بدی رو یکی یکی بنویس

📝 **مثال:**
• ورزش صبحگاهی
• مطالعه ۳۰ دقیقه
• برنامه نویسی

➡️ **اولین کار روزانه‌ات رو بنویس...**
        """
        await update.message.reply_text(welcome_text, reply_markup=ReplyKeyboardRemove())
        return SETUP_TASKS
    else:
        await show_main_menu(update, context)
        return MAIN_MENU

# حالت ثبت کارها - ✅ اصلاح شده
async def setup_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    task_text = update.message.text.strip()
    
    if task_text.lower() in ['/done', 'اتمام', 'تمام']:
        return await done_setup(update, context)
    
    if task_text:
        users_db[user_id]["daily_tasks"].append({
            "name": task_text,
            "completed": False,
            "created_at": get_date_key()
        })
        
        Database.save(users_db)
        tasks_count = len(users_db[user_id]["daily_tasks"])
        
        # نمایش کارهای اضافه شده
        tasks_list = format_task_list(users_db[user_id]["daily_tasks"], show_completion=False)
        
        if tasks_count < 5:
            await update.message.reply_text(
                f"✅ **'{task_text}' ثبت شد!**\n\n"
                f"📋 **کارهای ثبت شده:**\n{tasks_list}\n\n"
                f"➡️ کار بعدی رو بنویس یا 'اتمام' بفرست...",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            keyboard = [[KeyboardButton("✅ اتمام تنظیمات")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"✅ **'{task_text}' ثبت شد!**\n\n"
                f"📋 **کارهای ثبت شده:**\n{tasks_list}\n\n"
                f"🎯 برای اتمام «✅ اتمام تنظیمات» رو بزن...",
                reply_markup=reply_markup
            )
        return SETUP_TASKS
    
    await update.message.reply_text("لطفاً یک کار معتبر وارد کن:")
    return SETUP_TASKS

# اتمام ثبت کارها - ✅ اصلاح شده
async def done_setup(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    
    if len(users_db[user_id]["daily_tasks"]) < 1:
        await update.message.reply_text(
            "❌ **حداقل یک کار باید ثبت کنی!**\n\nاولین کارت رو بنویس...",
            reply_markup=ReplyKeyboardRemove()
        )
        return SETUP_TASKS
    
    users_db[user_id]["setup_complete"] = True
    Database.save(users_db)
    
    tasks_list = format_task_list(users_db[user_id]["daily_tasks"], show_completion=False)
    tasks_count = len(users_db[user_id]["daily_tasks"])
    
    completion_text = f"""
🎉 **تنظیمات تکمیل شد!**

{get_all_dates()}

📋 **کارهای ثبت شده ({tasks_count}):**
{tasks_list}

🏠 از منوی زیر استفاده کن:
    """
    
    await update.message.reply_text(completion_text, reply_markup=ReplyKeyboardRemove())
    return await show_main_menu(update, context)

# نمایش منوی اصلی - ✅ اصلاح شده
async def show_main_menu(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db.get(user_id, {})
    
    # آمار سریع
    total_tasks = len(user_data.get("daily_tasks", []))
    completed_tasks = sum(1 for task in user_data.get("daily_tasks", []) if task.get("completed", False))
    
    menu_text = f"""
🏠 **منوی اصلی**

{get_all_dates()}

📊 **وضعیت امروز:** {completed_tasks} از {total_tasks} تکمیل شده

🎯 **گزینه‌های موجود:**
    """
    
    keyboard = [
        [KeyboardButton("📋 کارهای امروز"), KeyboardButton("✅ تکمیل کارها")],
        [KeyboardButton("➕ اضافه کردن کار"), KeyboardButton("📊 گزارش امروز")],
        [KeyboardButton("⚙️ تنظیمات")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(menu_text, reply_markup=reply_markup)
    return MAIN_MENU

# نمایش کارهای امروز - ✅ اصلاح شده
async def show_today_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    today_key = get_date_key()
    user_data["last_active_date"] = today_key
    Database.save(users_db)
    
    daily_tasks = format_task_list(user_data["daily_tasks"])
    
    message_text = f"""
{get_all_dates()}

📋 **کارهای امروز:**
{daily_tasks}

💡 از دکمه «✅ تکمیل کارها» استفاده کن.
    """
    
    keyboard = [
        [KeyboardButton("✅ تکمیل کارها"), KeyboardButton("➕ اضافه کردن کار")],
        [KeyboardButton("📊 گزارش امروز"), KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message_text, reply_markup=reply_markup)
    return MAIN_MENU

# اضافه کردن کار - ✅ ساده‌سازی شده
async def add_task(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("📅 امروز"), KeyboardButton("🗓️ تاریخ مشخص")],
        [KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"{get_all_dates()}\n\n"
        "📅 **برای کدوم تاریخ می‌خوای کار اضافه کنی؟**\n\n"
        "• 📅 امروز: برای کارهای امروز\n"
        "• 🗓️ تاریخ مشخص: برای تاریخ‌های دیگر",
        reply_markup=reply_markup
    )
    return ADD_TASK_DATE

# مدیریت تاریخ برای کار جدید - ✅ ساده‌سازی شده
async def handle_task_date(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    date_choice = update.message.text
    
    if "منوی اصلی" in date_choice:
        await show_main_menu(update, context)
        return MAIN_MENU
    
    today = datetime.now()
    
    if "امروز" in date_choice:
        selected_date = today
        date_display = "امروز"
        date_key = selected_date.strftime("%Y-%m-%d")
        
        # مستقیماً برای امروز کار اضافه می‌کنیم
        context.user_data["selected_date"] = date_key
        context.user_data["date_display"] = date_display
        
        await update.message.reply_text(
            f"📅 **تاریخ:** {date_display}\n\n"
            "📝 **حالا نام کار رو وارد کن:**",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_TASK_NAME
        
    elif "تاریخ مشخص" in date_choice:
        await update.message.reply_text(
            "🗓️ **تاریخ مورد نظرت رو به این فرمت وارد کن:**\n\n"
            "📌 **مثال‌ها:**\n"
            "• 1403/10/15\n"
            "• 2024-01-05\n"
            "• فردا\n"
            "• هفته بعد",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_TASK_NAME
    
    await update.message.reply_text(
        "❌ لطفاً از دکمه‌ها استفاده کن.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_TASK_DATE

# ثبت نام کار جدید - ✅ اصلاح شده
async def handle_task_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    task_name = update.message.text.strip()
    
    # اگر تاریخ از قبل انتخاب شده (امروز)
    if context.user_data.get("selected_date"):
        selected_date = context.user_data["selected_date"]
        date_display = context.user_data.get("date_display", "نامشخص")
        
        # ذخیره کار برای تاریخ مشخص
        if selected_date not in users_db[user_id]["dated_tasks"]:
            users_db[user_id]["dated_tasks"][selected_date] = []
        
        users_db[user_id]["dated_tasks"][selected_date].append({
            "name": task_name,
            "completed": False,
            "created_at": get_date_key(),
            "type": "special"
        })
        
        Database.save(users_db)
        
        await update.message.reply_text(
            f"✅ **کار با موفقیت ثبت شد!**\n\n"
            f"📝 **کار:** {task_name}\n"
            f"📅 **تاریخ:** {date_display}"
        )
    else:
        # برای تاریخ‌های دیگر (ساده‌سازی: فقط برای امروز ذخیره می‌کنه)
        today_key = get_date_key()
        if today_key not in users_db[user_id]["dated_tasks"]:
            users_db[user_id]["dated_tasks"][today_key] = []
        
        users_db[user_id]["dated_tasks"][today_key].append({
            "name": task_name,
            "completed": False,
            "created_at": get_date_key(),
            "type": "special"
        })
        
        Database.save(users_db)
        
        await update.message.reply_text(
            f"✅ **کار با موفقیت برای امروز ثبت شد!**\n\n"
            f"📝 **کار:** {task_name}\n"
            f"📅 **تاریخ:** امروز"
        )
    
    return await show_main_menu(update, context)

# تکمیل کارها - ✅ اصلاح شده
async def complete_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    today_key = get_date_key()
    all_tasks = []
    
    # جمع‌آوری همه کارهای امروز
    for task in user_data["daily_tasks"]:
        all_tasks.append(("daily", task))
    
    if today_key in user_data["dated_tasks"]:
        for task in user_data["dated_tasks"][today_key]:
            all_tasks.append(("dated", task))
    
    if not all_tasks:
        await update.message.reply_text("📝 امروز هیچ کاری برای تکمیل وجود نداره!")
        return await show_main_menu(update, context)
    
    # ایجاد دکمه‌های کارها
    keyboard = []
    for i, (task_type, task) in enumerate(all_tasks, 1):
        status = "✅" if task.get("completed", False) else "◻️"
        task_name = task['name'][:20] + "..." if len(task['name']) > 20 else task['name']
        keyboard.append([KeyboardButton(f"{i}. {status} {task_name}")])
    
    keyboard.append([KeyboardButton("🏠 منوی اصلی")])
    
    context.user_data["current_tasks"] = all_tasks
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✅ **کدام کار رو تکمیل کردی؟**\n\n"
        "روی کار مورد نظر کلیک کن تا وضعیتش تغییر کنه:",
        reply_markup=reply_markup
    )
    return COMPLETE_TASKS

async def handle_task_completion(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    if "منوی اصلی" in message_text:
        return await show_main_menu(update, context)
    
    if message_text and message_text[0].isdigit():
        try:
            task_number = int(message_text.split(".")[0])
            all_tasks = context.user_data.get("current_tasks", [])
            
            if 1 <= task_number <= len(all_tasks):
                task_type, task = all_tasks[task_number - 1]
                task["completed"] = not task.get("completed", False)
                
                Database.save(users_db)
                status = "تکمیل شد ✅" if task["completed"] else "در انتظار ◻️"
                await update.message.reply_text(f"✅ کار '{task['name']}' {status}!")
            
            return await complete_tasks(update, context)
            
        except Exception as e:
            logging.error(f"Error completing task: {e}")
            await update.message.reply_text("❌ خطا در به روزرسانی کار")
    
    return await complete_tasks(update, context)

# گزارش عملکرد
async def show_report(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    total_daily_tasks = len(user_data["daily_tasks"])
    completed_today = sum(1 for task in user_data["daily_tasks"] if task.get("completed", False))
    
    today_key = get_date_key()
    dated_today = user_data["dated_tasks"].get(today_key, [])
    completed_dated = sum(1 for task in dated_today if task.get("completed", False))
    
    total_today = total_daily_tasks + len(dated_today)
    completed_total = completed_today + completed_dated
    
    progress = round((completed_total / total_today) * 100) if total_today > 0 else 0
    
    progress_bar = "🟩" * (completed_total) + "⬜" * (total_today - completed_total)
    
    report_text = f"""
📊 **گزارش امروز**

{get_all_dates()}

{progress_bar}
✅ **کارهای انجام شده:** {completed_total} از {total_today}
📈 **پیشرفت:** {progress}%

{"🎉 عالی! همه کارها انجام شد!" if completed_total == total_today else "💪 ادامه بده!" if completed_total > 0 else "🚀 شروع کن!"}
    """
    
    await update.message.reply_text(report_text)
    return MAIN_MENU

# تنظیمات
async def show_settings(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    total_completed = sum(1 for task in user_data["daily_tasks"] if task.get("completed", False))
    
    settings_text = f"""
⚙️ **تنظیمات کاربری**

👤 **کاربر:** {user_data.get('user_name', 'نامشخص')}
📅 **عضو since:** {user_data.get('created_at', 'نامشخص')}

📊 **آمار:**
📋 کارهای روزانه: {len(user_data["daily_tasks"])}
✅ تکمیل شده: {total_completed}
📌 کارهای تاریخ‌دار: {sum(len(tasks) for tasks in user_data["dated_tasks"].values())}

🔄 /start - تنظیمات مجدد
    """
    
    await update.message.reply_text(settings_text)
    return MAIN_MENU

def main():
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable is not set!")
        return
    
    if not os.path.exists(DB_FILE):
        Database.save({})
    
    application = Application.builder().token(TOKEN).build()
    
    # هندلر مستقل
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", show_today_tasks))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("complete", complete_tasks))
    application.add_handler(CommandHandler("report", show_report))
    application.add_handler(CommandHandler("settings", show_settings))
    
    # ConversationHandler اصلی
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SETUP_TASKS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, setup_tasks)
            ],
            MAIN_MENU: [
                MessageHandler(filters.Regex("^🏠 منوی اصلی$"), show_main_menu),
                MessageHandler(filters.Regex("^📋 کارهای امروز$"), show_today_tasks),
                MessageHandler(filters.Regex("^📊 گزارش امروز$"), show_report),
                MessageHandler(filters.Regex("^✅ تکمیل کارها$"), complete_tasks),
                MessageHandler(filters.Regex("^➕ اضافه کردن کار$"), add_task),
                MessageHandler(filters.Regex("^⚙️ تنظیمات$"), show_settings)
            ],
            ADD_TASK_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_date)
            ],
            ADD_TASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_name)
            ],
            COMPLETE_TASKS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_completion)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # راه‌اندازی سرور وب برای Render
    print("🚀 Starting web server for Render...")
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    print("🤖 ربات فعال شد!")
    application.run_polling()

if __name__ == '__main__':
    main()
مهم‌ترین تغییرات:

رفع مشکل ثبت کارها: حالا وقتی کار اضافه می‌کنی، لیست کارها رو نشون میده

ساده‌سازی گزینه‌های تاریخ: فقط "امروز" و "تاریخ مشخص"

بهبود مدیریت حالت‌ها: مکالمات بهتر مدیریت می‌شن

نمایش بهتر کارها: همیشه لیست کارهای ثبت شده رو نشون میده

امکانات جدید:

✅ می‌تونی کارها رو اضافه کنی و ببینی

📅 فقط دو گزینه ساده برای تاریخ

📋 نمایش لحظه‌ای کارهای ثبت شده

🎯 مدیریت آسان‌تر کارها

حالا باید بتونی کارهات رو اضافه کنی و ببینی! مشکلت حل شد؟

خب اپدیت کردم
الان یه پیام خوشامد میگه بعد میگه اولین کار روزانت رو بنویس بعد که مینویسم دیگه هیچ اتفاقی نمی افته
مشکل رو پیدا کردم! وقتی کار رو می‌نویسی، هندلر درستی برای پردازش اون در حالت SETUP_TASKS وجود نداره. باید ConversationHandler رو اصلاح کنم.

کد اصلاح شده - قسمت اصلی:

python
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import jdatetime
import json
import os
import threading
from flask import Flask

# ✅ بخش Flask برای Render
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running!"

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# حالت‌های مکالمه
SETUP_TASKS, MAIN_MENU, ADD_TASK_DATE, ADD_TASK_NAME, COMPLETE_TASKS = range(5)

# دیتابیس
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

# لود دیتابیس
users_db = Database.load()

# توابع کمکی برای تاریخ
def get_all_dates():
    now = datetime.now()
    jdate = jdatetime.datetime.now()
    
    persian_days = {
        'Saturday': 'شنبه',
        'Sunday': 'یکشنبه', 
        'Monday': 'دوشنبه',
        'Tuesday': 'سه‌شنبه',
        'Wednesday': 'چهارشنبه',
        'Thursday': 'پنجشنبه',
        'Friday': 'جمعه'
    }
    
    english_day = now.strftime('%A')
    persian_day = persian_days.get(english_day, english_day)
    
    return f"""
📅 **تاریخ امروز:**

🇮🇷 **شمسی:** {jdate.strftime('%Y/%m/%d')} - {jdate.strftime('%A')}
🌍 **میلادی:** {now.strftime('%Y-%m-%d')} - {persian_day}
"""

def get_date_key():
    return datetime.now().strftime("%Y-%m-%d")

def format_task_list(tasks, show_completion=True):
    if not tasks:
        return "📝 هیچ کاری ثبت نشده"
    
    result = ""
    for i, task in enumerate(tasks, 1):
        if show_completion:
            status = "✅" if task.get("completed", False) else "◻️"
            result += f"{i}. {status} {task['name']}\n"
        else:
            result += f"{i}. {task['name']}\n"
    return result

# دستور start
async def start(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    logging.info(f"User {user_id} ({user_name}) started the bot")
    
    if user_id not in users_db:
        users_db[user_id] = {
            "setup_complete": False,
            "daily_tasks": [],
            "dated_tasks": {},
            "last_active_date": get_date_key(),
            "created_at": get_date_key(),
            "user_name": user_name
        }
        Database.save(users_db)
    
    user_data = users_db[user_id]
    
    if not user_data["setup_complete"]:
        welcome_text = f"""
👋 **سلام {user_name} عزیز!**

📅 **به ربات مدیریت کارهای روزانه خوش اومدی!**

**حالا کارهای روزانه‌ات رو تعریف کن:**
هر کاری که می‌خوای هر روز انجام بدی رو یکی یکی بنویس

📝 **مثال:**
• ورزش صبحگاهی
• مطالعه ۳۰ دقیقه
• برنامه نویسی

➡️ **اولین کار روزانه‌ات رو بنویس...**
        """
        await update.message.reply_text(welcome_text, reply_markup=ReplyKeyboardRemove())
        return SETUP_TASKS
    else:
        await show_main_menu(update, context)
        return MAIN_MENU

# حالت ثبت کارها - ✅ اصلاح شده
async def setup_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    task_text = update.message.text.strip()
    
    # اگر کاربر می‌خواد تمام کنه
    if task_text.lower() in ['/done', 'اتمام', 'تمام', 'done', 'پایان']:
        return await done_setup(update, context)
    
    if task_text and len(task_text) > 1:
        # اضافه کردن کار جدید
        users_db[user_id]["daily_tasks"].append({
            "name": task_text,
            "completed": False,
            "created_at": get_date_key()
        })
        
        Database.save(users_db)
        tasks_count = len(users_db[user_id]["daily_tasks"])
        
        # نمایش کارهای اضافه شده
        tasks_list = format_task_list(users_db[user_id]["daily_tasks"], show_completion=False)
        
        if tasks_count < 3:
            response_text = f"""
✅ **'{task_text}' ثبت شد!**

📋 **کارهای ثبت شده ({tasks_count}):**
{tasks_list}

➡️ **کار بعدی رو بنویس یا 'اتمام' بفرست...**
            """
            await update.message.reply_text(response_text, reply_markup=ReplyKeyboardRemove())
        else:
            keyboard = [[KeyboardButton("✅ اتمام تنظیمات")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            response_text = f"""
✅ **'{task_text}' ثبت شد!**

📋 **کارهای ثبت شده ({tasks_count}):**
{tasks_list}

🎯 **برای اتمام «✅ اتمام تنظیمات» رو بزن...**
            """
            await update.message.reply_text(response_text, reply_markup=reply_markup)
        
        return SETUP_TASKS
    else:
        await update.message.reply_text("❌ لطفاً یک کار معتبر وارد کن (حداقل ۲ حرف):")
        return SETUP_TASKS

# اتمام ثبت کارها - ✅ اصلاح شده
async def done_setup(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    
    if len(users_db[user_id]["daily_tasks"]) < 1:
        await update.message.reply_text(
            "❌ **حداقل یک کار باید ثبت کنی!**\n\nاولین کارت رو بنویس...",
            reply_markup=ReplyKeyboardRemove()
        )
        return SETUP_TASKS
    
    users_db[user_id]["setup_complete"] = True
    Database.save(users_db)
    
    tasks_list = format_task_list(users_db[user_id]["daily_tasks"], show_completion=False)
    tasks_count = len(users_db[user_id]["daily_tasks"])
    
    completion_text = f"""
🎉 **تنظیمات تکمیل شد!**

{get_all_dates()}

📋 **کارهای ثبت شده ({tasks_count}):**
{tasks_list}

🏠 **حالا می‌تونی از منوی اصلی استفاده کنی:**
    """
    
    await update.message.reply_text(completion_text, reply_markup=ReplyKeyboardRemove())
    return await show_main_menu(update, context)

# نمایش منوی اصلی - ✅ اصلاح شده
async def show_main_menu(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db.get(user_id, {})
    
    # آمار سریع
    total_tasks = len(user_data.get("daily_tasks", []))
    completed_tasks = sum(1 for task in user_data.get("daily_tasks", []) if task.get("completed", False))
    
    menu_text = f"""
🏠 **منوی اصلی**

{get_all_dates()}

📊 **وضعیت امروز:** {completed_tasks} از {total_tasks} تکمیل شده

🎯 **گزینه‌های موجود:**
    """
    
    keyboard = [
        [KeyboardButton("📋 کارهای امروز"), KeyboardButton("✅ تکمیل کارها")],
        [KeyboardButton("➕ اضافه کردن کار"), KeyboardButton("📊 گزارش امروز")],
        [KeyboardButton("⚙️ تنظیمات")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(menu_text, reply_markup=reply_markup)
    return MAIN_MENU

# نمایش کارهای امروز
async def show_today_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    today_key = get_date_key()
    user_data["last_active_date"] = today_key
    Database.save(users_db)
    
    daily_tasks = format_task_list(user_data["daily_tasks"])
    
    message_text = f"""
{get_all_dates()}

📋 **کارهای امروز:**
{daily_tasks}

💡 از دکمه «✅ تکمیل کارها» استفاده کن.
    """
    
    keyboard = [
        [KeyboardButton("✅ تکمیل کارها"), KeyboardButton("➕ اضافه کردن کار")],
        [KeyboardButton("📊 گزارش امروز"), KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message_text, reply_markup=reply_markup)
    return MAIN_MENU

# اضافه کردن کار
async def add_task(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("📅 امروز"), KeyboardButton("🗓️ تاریخ مشخص")],
        [KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📅 **برای کدوم تاریخ می‌خوای کار اضافه کنی؟**\n\n"
        "• 📅 امروز: برای کارهای امروز\n"
        "• 🗓️ تاریخ مشخص: برای تاریخ‌های دیگر",
        reply_markup=reply_markup
    )
    return ADD_TASK_DATE

# مدیریت تاریخ برای کار جدید
async def handle_task_date(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    date_choice = update.message.text
    
    if "منوی اصلی" in date_choice:
        await show_main_menu(update, context)
        return MAIN_MENU
    
    today = datetime.now()
    
    if "امروز" in date_choice:
        selected_date = today
        date_display = "امروز"
        date_key = selected_date.strftime("%Y-%m-%d")
        
        context.user_data["selected_date"] = date_key
        context.user_data["date_display"] = date_display
        
        await update.message.reply_text(
            f"📅 **تاریخ:** {date_display}\n\n"
            "📝 **حالا نام کار رو وارد کن:**",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_TASK_NAME
        
    elif "تاریخ مشخص" in date_choice:
        await update.message.reply_text(
            "🗓️ **تاریخ مورد نظرت رو به این فرمت وارد کن:**\n\n"
            "📌 **مثال‌ها:**\n"
            "• فردا\n"
            "• 1403/10/15\n"
            "• 2024-01-05",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_TASK_NAME
    
    await update.message.reply_text(
        "❌ لطفاً از دکمه‌ها استفاده کن.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_TASK_DATE

# ثبت نام کار جدید
async def handle_task_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    task_name = update.message.text.strip()
    
    if not task_name or len(task_name) < 2:
        await update.message.reply_text("❌ لطفاً یک نام معتبر برای کار وارد کن (حداقل ۲ حرف):")
        return ADD_TASK_NAME
    
    # اگر تاریخ از قبل انتخاب شده (امروز)
    if context.user_data.get("selected_date"):
        selected_date = context.user_data["selected_date"]
        date_display = context.user_data.get("date_display", "نامشخص")
        
        # ذخیره کار برای تاریخ مشخص
        if selected_date not in users_db[user_id]["dated_tasks"]:
            users_db[user_id]["dated_tasks"][selected_date] = []
        
        users_db[user_id]["dated_tasks"][selected_date].append({
            "name": task_name,
            "completed": False,
            "created_at": get_date_key(),
            "type": "special"
        })
        
        Database.save(users_db)
        
        await update.message.reply_text(
            f"✅ **کار با موفقیت ثبت شد!**\n\n"
            f"📝 **کار:** {task_name}\n"
            f"📅 **تاریخ:** {date_display}"
        )
    else:
        # برای تاریخ‌های دیگر (ساده‌سازی: فقط برای امروز ذخیره می‌کنه)
        today_key = get_date_key()
        if today_key not in users_db[user_id]["dated_tasks"]:
            users_db[user_id]["dated_tasks"][today_key] = []
        
        users_db[user_id]["dated_tasks"][today_key].append({
            "name": task_name,
            "completed": False,
            "created_at": get_date_key(),
            "type": "special"
        })
        
        Database.save(users_db)
        
        await update.message.reply_text(
            f"✅ **کار با موفقیت برای امروز ثبت شد!**\n\n"
            f"📝 **کار:** {task_name}"
        )
    
    return await show_main_menu(update, context)

# تکمیل کارها
async def complete_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    today_key = get_date_key()
    all_tasks = []
    
    # جمع‌آوری همه کارهای امروز
    for task in user_data["daily_tasks"]:
        all_tasks.append(("daily", task))
    
    if today_key in user_data["dated_tasks"]:
        for task in user_data["dated_tasks"][today_key]:
            all_tasks.append(("dated", task))
    
    if not all_tasks:
        await update.message.reply_text("📝 امروز هیچ کاری برای تکمیل وجود نداره!")
        return await show_main_menu(update, context)
    
    # ایجاد دکمه‌های کارها
    keyboard = []
    for i, (task_type, task) in enumerate(all_tasks, 1):
        status = "✅" if task.get("completed", False) else "◻️"
        task_name = task['name'][:20] + "..." if len(task['name']) > 20 else task['name']
        keyboard.append([KeyboardButton(f"{i}. {status} {task_name}")])
    
    keyboard.append([KeyboardButton("🏠 منوی اصلی")])
    
    context.user_data["current_tasks"] = all_tasks
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✅ **کدام کار رو تکمیل کردی؟**\n\n"
        "روی کار مورد نظر کلیک کن تا وضعیتش تغییر کنه:",
        reply_markup=reply_markup
    )
    return COMPLETE_TASKS

async def handle_task_completion(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    if "منوی اصلی" in message_text:
        return await show_main_menu(update, context)
    
    if message_text and message_text[0].isdigit():
        try:
            task_number = int(message_text.split(".")[0])
            all_tasks = context.user_data.get("current_tasks", [])
            
            if 1 <= task_number <= len(all_tasks):
                task_type, task = all_tasks[task_number - 1]
                task["completed"] = not task.get("completed", False)
                
                Database.save(users_db)
                status = "تکمیل شد ✅" if task["completed"] else "در انتظار ◻️"
                await update.message.reply_text(f"✅ کار '{task['name']}' {status}!")
            
            return await complete_tasks(update, context)
            
        except Exception as e:
            logging.error(f"Error completing task: {e}")
            await update.message.reply_text("❌ خطا در به روزرسانی کار")
    
    return await complete_tasks(update, context)

# گزارش عملکرد
async def show_report(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    total_daily_tasks = len(user_data["daily_tasks"])
    completed_today = sum(1 for task in user_data["daily_tasks"] if task.get("completed", False))
    
    today_key = get_date_key()
    dated_today = user_data["dated_tasks"].get(today_key, [])
    completed_dated = sum(1 for task in dated_today if task.get("completed", False))
    
    total_today = total_daily_tasks + len(dated_today)
    completed_total = completed_today + completed_dated
    
    progress = round((completed_total / total_today) * 100) if total_today > 0 else 0
    
    progress_bar = "🟩" * completed_total + "⬜" * (total_today - completed_total)
    
    report_text = f"""
📊 **گزارش امروز**

{get_all_dates()}

{progress_bar}
✅ **کارهای انجام شده:** {completed_total} از {total_today}
📈 **پیشرفت:** {progress}%

{"🎉 عالی! همه کارها انجام شد!" if completed_total == total_today else "💪 ادامه بده!" if completed_total > 0 else "🚀 شروع کن!"}
    """
    
    await update.message.reply_text(report_text)
    return MAIN_MENU

# تنظیمات
async def show_settings(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    total_completed = sum(1 for task in user_data["daily_tasks"] if task.get("completed", False))
    
    settings_text = f"""
⚙️ **تنظیمات کاربری**

👤 **کاربر:** {user_data.get('user_name', 'نامشخص')}
📅 **عضو since:** {user_data.get('created_at', 'نامشخص')}

📊 **آمار:**
📋 کارهای روزانه: {len(user_data["daily_tasks"])}
✅ تکمیل شده: {total_completed}
    """
    
    await update.message.reply_text(settings_text)
    return MAIN_MENU

def main():
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable is not set!")
        return
    
    if not os.path.exists(DB_FILE):
        Database.save({})
    
    application = Application.builder().token(TOKEN).build()
    
    # ✅ ConversationHandler اصلی با تنظیمات اصلاح شده
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SETUP_TASKS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, setup_tasks)
            ],
            MAIN_MENU: [
                MessageHandler(filters.Regex("^🏠 منوی اصلی$"), show_main_menu),
                MessageHandler(filters.Regex("^📋 کارهای امروز$"), show_today_tasks),
                MessageHandler(filters.Regex("^📊 گزارش امروز$"), show_report),
                MessageHandler(filters.Regex("^✅ تکمیل کارها$"), complete_tasks),
                MessageHandler(filters.Regex("^➕ اضافه کردن کار$"), add_task),
                MessageHandler(filters.Regex("^⚙️ تنظیمات$"), show_settings)
            ],
            ADD_TASK_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_date)
            ],
            ADD_TASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_name)
            ],
            COMPLETE_TASKS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_completion)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # هندلرهای مستقل برای دستورات
    application.add_handler(CommandHandler("today", show_today_tasks))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("complete", complete_tasks))
    application.add_handler(CommandHandler("report", show_report))
    application.add_handler(CommandHandler("settings", show_settings))
    
    # راه‌اندازی سرور وب برای Render
    print("🚀 Starting web server for Render...")
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    print("🤖 ربات فعال شد!")
    application.run_polling()

if __name__ == '__main__':
    main()
