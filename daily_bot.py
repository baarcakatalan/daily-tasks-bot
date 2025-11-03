import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import jdatetime
import json
import os
import threading
from flask import Flask  # ✅ این خط رو اضافه کن

# ✅ این بخش رو اضافه کن
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running!"

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
# تنظیمات پیشرفته لاگ
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

# دیتابیس فایل‌محور
DB_FILE = 'users_data.json'

# 🔥 تغییر ۱: توکن از متغیر محیطی بخونه
TOKEN = os.environ.get('BOT_TOKEN', '')  # توکن از محیط میاد

class Database:
    @staticmethod
    def load():
        """لود داده‌ها از فایل"""
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading database: {e}")
        return {}
    
    @staticmethod
    def save(data):
        """ذخیره داده‌ها در فایل"""
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving database: {e}")

# لود دیتابیس
users_db = Database.load()

# توابع کمکی برای تاریخ
def get_all_dates():
    """برگرداندن همه تاریخ‌های امروز"""
    now = datetime.now()
    jdate = jdatetime.datetime.now()
    
    # نام روزهای فارسی
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
🗓️ **هفته:** {get_week_number()}
"""

def get_date_key():
    """کلید یکتا برای تاریخ امروز"""
    return datetime.now().strftime("%Y-%m-%d")

def get_week_number():
    """شماره هفته جاری"""
    return datetime.now().strftime("%U")

def format_task_list(tasks, show_completion=True):
    """فرمت‌دهی لیست کارها"""
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
    
    # بررسی اگر کاربر بعد از چند روز برگشته
    today_key = get_date_key()
    last_active = user_data.get("last_active_date")
    
    if last_active and last_active != today_key:
        await handle_missing_days(update, user_data, last_active, today_key)
    
    user_data["last_active_date"] = today_key
    Database.save(users_db)
    
    if not user_data["setup_complete"]:
        welcome_text = f"""
👋 **سلام {user_name} عزیز!**

📅 **به ربات مدیریت کارهای روزانه خوش اومدی!**

این ربات بهت کمک می‌کنه:
✅ کارهای روزانه‌ات رو مدیریت کنی
📊 پیشرفتت رو دنبال کنی  
⏰ کارهای عقب‌افتاده رو پیگیری کنی

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

async def handle_missing_days(update: Update, user_data: dict, last_active: str, today: str):
    """مدیریت روزهای از دست رفته کاربر"""
    try:
        last_date = datetime.strptime(last_active, "%Y-%m-%d")
        current_date = datetime.strptime(today, "%Y-%m-%d")
        days_missing = (current_date - last_date).days - 1
        
        if days_missing > 0:
            for i in range(1, days_missing + 1):
                missing_date = last_date + timedelta(days=i)
                date_key = missing_date.strftime("%Y-%m-%d")
                
                if date_key not in user_data["dated_tasks"]:
                    user_data["dated_tasks"][date_key] = []
                
                for task in user_data["daily_tasks"]:
                    user_data["dated_tasks"][date_key].append({
                        "name": f"{task['name']} (تعویق افتاده)",
                        "completed": False,
                        "type": "pending",
                        "original_date": last_active
                    })
            
            if days_missing == 1:
                message = "📅 **یادآوری:** دیروز رو از دست دادی! کارهای دیروز به امروز اضافه شد."
            else:
                message = f"📅 **یادآوری:** {days_missing} روز رو از دست دادی! کارهای عقب‌افتاده اضافه شد."
            
            await update.message.reply_text(message)
            Database.save(users_db)
    
    except Exception as e:
        logging.error(f"Error handling missing days: {e}")

# حالت ثبت کارها
async def setup_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    task_text = update.message.text.strip()
    
    if task_text:
        users_db[user_id]["daily_tasks"].append({
            "name": task_text,
            "completed": False,
            "created_at": get_date_key(),
            "completed_dates": []
        })
        
        Database.save(users_db)
        tasks_count = len(users_db[user_id]["daily_tasks"])
        
        if tasks_count < 8:
            await update.message.reply_text(
                f"✅ **'{task_text}' ثبت شد!**\n\n"
                f"📋 تا الان {tasks_count} کار ثبت کردی\n\n"
                f"➡️ کار بعدی رو بنویس یا /done بزن برای اتمام...",
                reply_markup=ReplyKeyboardRemove()
            )
            return SETUP_TASKS
        else:
            keyboard = [[KeyboardButton("✅ اتمام تنظیمات")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"✅ **'{task_text}' ثبت شد!**\n\n"
                f"📋 تا الان {tasks_count} کار ثبت کردی\n\n"
                f"🎯 برای اتمام «✅ اتمام تنظیمات» رو بزن...",
                reply_markup=reply_markup
            )
            return SETUP_TASKS

# اتمام ثبت کارها
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

🏠 **دستورات موجود:**

📋 /today - کارهای امروز
➕ /add - اضافه کردن کار جدید
➡️ /tomorrow - کارهای فردا
📊 /report - گزارش عملکرد
✅ /complete - تکمیل کارها
⚙️ /settings - تنظیمات

🚀 **برای شروع /today رو بزن!**
    """
    
    await update.message.reply_text(completion_text, reply_markup=ReplyKeyboardRemove())
    return MAIN_MENU

# نمایش کارهای امروز
async def show_today_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    today_key = get_date_key()
    user_data["last_active_date"] = today_key
    Database.save(users_db)
    
    # کارهای روزانه
    daily_tasks = format_task_list(user_data["daily_tasks"])
    
    # کارهای تاریخ‌دار امروز
    dated_tasks = ""
    if today_key in user_data["dated_tasks"]:
        dated_tasks = f"\n📌 **کارهای خاص امروز:**\n{format_task_list(user_data['dated_tasks'][today_key])}"
    
    if not user_data["daily_tasks"] and today_key not in user_data["dated_tasks"]:
        message_text = f"""
{get_all_dates()}

📝 **هیچ کاری برای امروز ثبت نشده.**

💡 از /add برای اضافه کردن کار استفاده کن.
        """
    else:
        message_text = f"""
{get_all_dates()}

📋 **کارهای امروز:**
{daily_tasks}{dated_tasks}

💡 از /complete برای تکمیل کارها استفاده کن.
        """
    
    # دکمه‌های سریع
    keyboard = [
        [KeyboardButton("✅ تکمیل کارها"), KeyboardButton("➕ اضافه کردن کار")],
        [KeyboardButton("📊 گزارش امروز"), KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message_text, reply_markup=reply_markup)
    return MAIN_MENU

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
        return MAIN_MENU
    
    # ایجاد دکمه‌های کارها
    keyboard = []
    for i, (task_type, task) in enumerate(all_tasks, 1):
        status = "✅" if task.get("completed", False) else "◻️"
        keyboard.append([KeyboardButton(f"{status} کار {i}: {task['name'][:30]}...")])
    
    keyboard.append([KeyboardButton("🏠 بازگشت به منوی اصلی")])
    
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
    
    if "بازگشت" in message_text:
        await show_main_menu(update, context)
        return MAIN_MENU
    
    if "کار" in message_text:
        try:
            # استخراج شماره کار از متن
            task_number = int(message_text.split("کار")[1].split(":")[0].strip())
            all_tasks = context.user_data.get("current_tasks", [])
            
            if 1 <= task_number <= len(all_tasks):
                task_type, task = all_tasks[task_number - 1]
                task["completed"] = not task.get("completed", False)
                
                if task["completed"]:
                    task["completed_at"] = get_date_key()
                    if "completed_dates" not in task:
                        task["completed_dates"] = []
                    task["completed_dates"].append(get_date_key())
                
                Database.save(users_db)
                await update.message.reply_text(f"✅ وضعیت کار به روز شد!")
            
            return await complete_tasks(update, context)
            
        except Exception as e:
            logging.error(f"Error completing task: {e}")
            await update.message.reply_text("❌ خطا در به روزرسانی کار")
    
    return await complete_tasks(update, context)

# اضافه کردن کار با تاریخ
async def add_task(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("امروز 📅"), KeyboardButton("فردا ⏭️")],
        [KeyboardButton("پس فردا 📆"), KeyboardButton("هفته بعد 🗓️")],
        [KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"{get_all_dates()}\n\n"
        "📅 **برای کدوم تاریخ می‌خوای کار اضافه کنی؟**",
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
    elif "فردا" in date_choice:
        selected_date = today + timedelta(days=1)
        date_display = "فردا"
    elif "پس فردا" in date_choice:
        selected_date = today + timedelta(days=2)
        date_display = "پس فردا"
    elif "هفته" in date_choice:
        selected_date = today + timedelta(days=7)
        date_display = "هفته بعد"
    else:
        await update.message.reply_text(
            "❌ لطفاً از دکمه‌ها استفاده کن.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_TASK_DATE
    
    date_key = selected_date.strftime("%Y-%m-%d")
    context.user_data["selected_date"] = date_key
    context.user_data["date_display"] = date_display
    
    # نمایش تاریخ انتخابی
    jdate = jdatetime.datetime.fromgregorian(
        year=selected_date.year,
        month=selected_date.month, 
        day=selected_date.day
    )
    
    date_info = f"""
📅 **تاریخ انتخابی:** {date_display}
🇮🇷 **شمسی:** {jdate.strftime('%Y/%m/%d')} - {jdate.strftime('%A')}
🌍 **میلادی:** {selected_date.strftime('%Y-%m-%d')} - {selected_date.strftime('%A')}
    """
    
    await update.message.reply_text(
        f"{date_info}\n\n"
        "📝 **حالا نام کار رو وارد کن:**",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_TASK_NAME

# ثبت نام کار جدید
async def handle_task_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    task_name = update.message.text.strip()
    selected_date = context.user_data.get("selected_date")
    date_display = context.user_data.get("date_display", "نامشخص")
    
    if not selected_date:
        await update.message.reply_text("❌ خطا در ثبت تاریخ. لطفا دوباره امتحان کن.")
        return await add_task(update, context)
    
    # ذخیره کار
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
        f"📅 **تاریخ:** {date_display}",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await show_main_menu(update, context)
    return MAIN_MENU

# نمایش منوی اصلی
async def show_main_menu(update: Update, context: CallbackContext) -> None:
    menu_text = f"""
🏠 **منوی اصلی**

{get_all_dates()}

📋 /today - کارهای امروز
➕ /add - اضافه کردن کار جدید  
➡️ /tomorrow - کارهای فردا
✅ /complete - تکمیل کارها
📊 /report - گزارش عملکرد
⚙️ /settings - تنظیمات

💡 **برای شروع /today رو بزن!**
    """
    await update.message.reply_text(menu_text)

# گزارش عملکرد
async def show_report(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    total_daily_tasks = len(user_data["daily_tasks"])
    completed_today = sum(1 for task in user_data["daily_tasks"] if task.get("completed", False))
    
    # محاسبه کارهای تاریخ‌دار امروز
    today_key = get_date_key()
    dated_today = user_data["dated_tasks"].get(today_key, [])
    completed_dated = sum(1 for task in dated_today if task.get("completed", False))
    
    total_today = total_daily_tasks + len(dated_today)
    completed_total = completed_today + completed_dated
    
    progress = round((completed_total / total_today) * 100) if total_today > 0 else 0
    
    # ایجاد نمودار پیشرفت
    progress_bar = "🟩" * (completed_total) + "⬜" * (total_today - completed_total)
    
    report_text = f"""
📊 **گزارش امروز**

{get_all_dates()}

{progress_bar}
✅ **کارهای انجام شده:** {completed_total} از {total_today}
📈 **پیشرفت:** {progress}%

📋 **کارهای روزانه:** {completed_today}/{total_daily_tasks}
📌 **کارهای خاص:** {completed_dated}/{len(dated_today)}

{"🎉 عالی! همه کارها انجام شد!" if completed_total == total_today else "🔴 هنوز کارهایی مونده..." if completed_total > 0 else "🚀 شروع کن!"}
    """
    
    await update.message.reply_text(report_text)
    return MAIN_MENU

# نمایش تنظیمات
async def show_settings(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_data = users_db[user_id]
    
    total_completed = sum(1 for task in user_data["daily_tasks"] if task.get("completed", False))
    total_dated_tasks = sum(len(tasks) for tasks in user_data["dated_tasks"].values())
    
    settings_text = f"""
⚙️ **تنظیمات کاربری**

👤 **کاربر:** {user_data.get('user_name', 'نامشخص')}
📅 **عضو since:** {user_data.get('created_at', 'نامشخص')}

📊 **آمار:**
📋 کارهای روزانه: {len(user_data["daily_tasks"])}
✅ تکمیل شده: {total_completed}
📌 کارهای تاریخ‌دار: {total_dated_tasks}
🕒 آخرین فعالیت: {user_data.get('last_active_date', 'نامشخص')}

🔄 /start - تنظیمات مجدد
🧹 /reset - پاک کردن همه داده‌ها (موقت)
    """
    
    await update.message.reply_text(settings_text)
    return MAIN_MENU

# پاک کردن داده‌ها
async def reset_data(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    
    keyboard = [[KeyboardButton("❌ بله، پاک کن"), KeyboardButton("🔙 لغو")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "⚠️ **هشدار!**\n\n"
        "آیا مطمئنی می‌خوای همه داده‌ها رو پاک کنی؟\n"
        "این عمل غیرقابل بازگشت است!",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def handle_reset_confirmation(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    choice = update.message.text
    
    if "بله" in choice:
        users_db[user_id] = {
            "setup_complete": False,
            "daily_tasks": [],
            "dated_tasks": {},
            "last_active_date": get_date_key(),
            "created_at": get_date_key(),
            "user_name": users_db[user_id].get('user_name', 'User')
        }
        Database.save(users_db)
        await update.message.reply_text("✅ همه داده‌ها پاک شدند! /start رو بزن برای شروع مجدد.")
    else:
        await update.message.reply_text("🔙 عمل پاک کردن لغو شد.")
    
    return await start(update, context)

def main():
    # 🔥 تغییر ۲: چک کردن توکن
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable is not set!")
        print("Please set BOT_TOKEN in Render environment variables")
        return
    
    # ایجاد فایل دیتابیس اگر وجود ندارد
    if not os.path.exists(DB_FILE):
        Database.save({})
    
    application = Application.builder().token(TOKEN).build()
    
    # هندلر مستقل برای دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", show_today_tasks))
    application.add_handler(CommandHandler("tomorrow", show_today_tasks))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("complete", complete_tasks))
    application.add_handler(CommandHandler("report", show_report))
    application.add_handler(CommandHandler("settings", show_settings))
    application.add_handler(CommandHandler("reset", reset_data))
    
    # ConversationHandler اصلی
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SETUP_TASKS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, setup_tasks),
                CommandHandler("done", done_setup)
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, show_main_menu),
                MessageHandler(filters.Regex("^🏠 منوی اصلی$"), show_main_menu),
                MessageHandler(filters.Regex("^📊 گزارش امروز$"), show_report),
                MessageHandler(filters.Regex("^✅ تکمیل کارها$"), complete_tasks),
                MessageHandler(filters.Regex("^➕ اضافه کردن کار$"), add_task),
                MessageHandler(filters.Regex("^❌ بله، پاک کن$"), handle_reset_confirmation),
                MessageHandler(filters.Regex("^🔙 لغو$"), show_main_menu)
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
    
    # هندلر برای پیام‌های متنی عمومی
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, show_main_menu))
    
    # 🔥 تغییر ۳: پیام متفاوت برای Render
    print("🤖 ربات روی Render فعال شد!")
    print("📊 دیتابیس: users_data.json")
    print("📝 لاگ‌ها: bot.log")
    print("🌐 ربات 24/7 در دسترس است!")
    print("-" * 50)
    
    application.run_polling()

if __name__ == '__main__':

    main()
