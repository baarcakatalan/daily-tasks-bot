import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import jdatetime
import json
import os
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz


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

async def show_manage_tasks_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("➕ اضافه کار جدید"), KeyboardButton("✏️ ویرایش کار موجود")],
        [KeyboardButton("🗑️ حذف کار"), KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔧 **مدیریت کارها**\n\n"
        "چه کاری می‌خوای انجام بدی؟",
        reply_markup=reply_markup
    )
    return MANAGE_TASKS_MENU

# سیستم انتخاب تاریخ پله‌ای
async def select_year(update: Update, context: CallbackContext, purpose="add"):
    keyboard = [
        [KeyboardButton("📅 ۱۴۰۴ (سال جاری)"), KeyboardButton("📅 ۱۴۰۵ (سال آینده)")],
        [KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    context.user_data["date_purpose"] = purpose
    
    await update.message.reply_text(
        "📅 **انتخاب سال**\n\n"
        "برای کدوم سال می‌خوای برنامه‌ریزی کنی؟",
        reply_markup=reply_markup
    )
    return ADD_TASK_DATE_SELECT

async def select_month(update: Update, context: CallbackContext, year):
    context.user_data["selected_year"] = year
    
    keyboard = [
        [KeyboardButton("فروردین"), KeyboardButton("اردیبهشت"), KeyboardButton("خرداد")],
        [KeyboardButton("تیر"), KeyboardButton("مرداد"), KeyboardButton("شهریور")],
        [KeyboardButton("مهر"), KeyboardButton("آبان"), KeyboardButton("آذر")],
        [KeyboardButton("دی"), KeyboardButton("بهمن"), KeyboardButton("اسفند")],
        [KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"📅 **انتخاب ماه - سال {year}**\n\n"
        "کدوم ماه رو انتخاب می‌کنی؟",
        reply_markup=reply_markup
    )
    return ADD_TASK_DATE_SELECT

async def select_day(update: Update, context: CallbackContext, year, month):
    context.user_data["selected_month"] = month
    
    month_numbers = {
        "فروردین": 1, "اردیبهشت": 2, "خرداد": 3,
        "تیر": 4, "مرداد": 5, "شهریور": 6,
        "مهر": 7, "آبان": 8, "آذر": 9,
        "دی": 10, "بهمن": 11, "اسفند": 12
    }
    month_num = month_numbers.get(month, 1)
    
    keyboard = []
    row = []
    
    days_in_month = 31 if month_num <= 6 else 30
    if month_num == 12:
        days_in_month = 29
    
    for day in range(1, days_in_month + 1):
        row.append(KeyboardButton(str(day)))
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([KeyboardButton("🏠 منوی اصلی")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"📅 **انتخاب روز - {month} {year}**\n\n"
        "روز مورد نظرت رو انتخاب کن:",
        reply_markup=reply_markup
    )
    return ADD_TASK_DATE_SELECT

async def handle_date_selection(update: Update, context: CallbackContext) -> int:
    selection = update.message.text
    purpose = context.user_data.get("date_purpose", "add")
    
    if "منوی اصلی" in selection:
        return await show_main_menu(update, context)
    
    if "۱۴۰۴" in selection or "۱۴۰۵" in selection:
        year = 1404 if "۱۴۰۴" in selection else 1405
        return await select_month(update, context, year)
    
    months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", 
              "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    if selection in months:
        year = context.user_data.get("selected_year", 1404)
        return await select_day(update, context, year, selection)
    
    if selection.isdigit():
        day = int(selection)
        year = context.user_data.get("selected_year", 1404)
        month = context.user_data.get("selected_month", "فروردین")
        
        month_numbers = {
            "فروردین": 1, "اردیبهشت": 2, "خرداد": 3,
            "تیر": 4, "مرداد": 5, "شهریور": 6,
            "مهر": 7, "آبان": 8, "آذر": 9,
            "دی": 10, "بهمن": 11, "اسفند": 12
        }
        month_num = month_numbers.get(month, 1)
        
        try:
            jdate = jdatetime.date(year, month_num, day)
            gregorian_date = jdate.togregorian()
            date_key = get_date_key(gregorian_date)
            
            context.user_data["selected_date"] = date_key
            context.user_data["date_display"] = f"{day} {month} {year}"
            
            if purpose == "add":
                await update.message.reply_text(
                    f"📝 **کارهای {day} {month} {year}**\n\n"
                    "کارهایت رو به صورت خط به خط وارد کن:\n\n"
                    "📌 **مثال:**\n"
                    "ورزش صبحگاهی\n"
                    "مطالعه ۳۰ دقیقه\n"
                    "پروژه برنامه‌نویسی\n\n"
                    "پس از اتمام «✅ ثبت نهایی» رو بفرست.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return ADD_TASK_CONTENT
            elif purpose == "edit":
                return await show_edit_tasks(update, context, date_key)
            elif purpose == "delete":
                return await show_delete_tasks(update, context, date_key)
            elif purpose == "view":
                return await show_tasks_for_date(update, context, date_key, f"{day} {month} {year}")
            
        except Exception as e:
            logging.error(f"Error converting date: {e}")
            await update.message.reply_text("❌ تاریخ نامعتبر!")
            return await show_main_menu(update, context)
    
    return ADD_TASK_DATE_SELECT

async def handle_add_task_content(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    tasks_text = update.message.text.strip()
    
    if tasks_text == "✅ ثبت نهایی":
        await update.message.reply_text("❌ هیچ کاری وارد نکردی!")
        return ADD_TASK_CONTENT
    
    tasks_list = [task.strip() for task in tasks_text.split('\n') if task.strip()]
    
    if not tasks_list:
        await update.message.reply_text("❌ هیچ کار معتبری وارد نکردی!")
        return ADD_TASK_CONTENT
    
    date_key = context.user_data.get("selected_date", get_date_key())
    date_display = context.user_data.get("date_display", "امروز")
    
    if date_key not in users_db[user_id]["dated_tasks"]:
        users_db[user_id]["dated_tasks"][date_key] = []
    
    for task_name in tasks_list:
        users_db[user_id]["dated_tasks"][date_key].append({
            "name": task_name,
            "completed": False,
            "created_at": get_date_key(),
            "type": "special"
        })
    
    Database.save(users_db)
    
    tasks_count = len(tasks_list)
    tasks_preview = "\n".join([f"• {task}" for task in tasks_list[:5]])
    if tasks_count > 5:
        tasks_preview += f"\n• و {tasks_count - 5} کار دیگر..."
    
    await update.message.reply_text(
        f"✅ **{tasks_count} کار با موفقیت ثبت شد!**\n\n"
        f"📅 **تاریخ:** {date_display}\n"
        f"📋 **کارها:**\n{tasks_preview}"
    )
    
    return await show_main_menu(update, context)

async def show_edit_tasks(update: Update, context: CallbackContext, date_key):
    user_id = str(update.effective_user.id)
    
    tasks = []
    if date_key in users_db[user_id].get("dated_tasks", {}):
        tasks = users_db[user_id]["dated_tasks"][date_key]
    
    if not tasks:
        await update.message.reply_text("📝 هیچ کاری برای ویرایش وجود نداره!")
        return await show_main_menu(update, context)
    
    keyboard = []
    for i, task in enumerate(tasks, 1):
        keyboard.append([KeyboardButton(f"{i}. ✏️ {task['name'][:30]}")])
    
    keyboard.append([KeyboardButton("🏠 منوی اصلی")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    tasks_list = "\n".join([f"{i}. {task['name']}" for i, task in enumerate(tasks, 1)])
    
    await update.message.reply_text(
        f"✏️ **ویرایش کارها**\n\n"
        f"کدوم کار رو می‌خوای ویرایش کنی؟\n\n"
        f"{tasks_list}",
        reply_markup=reply_markup
    )
    
    context.user_data["edit_tasks"] = tasks
    context.user_data["edit_date_key"] = date_key
    return EDIT_TASK_SELECT

async def handle_edit_task_select(update: Update, context: CallbackContext) -> int:
    selection = update.message.text
    
    if "منوی اصلی" in selection:
        return await show_main_menu(update, context)
    
    if selection and selection[0].isdigit():
        try:
            task_number = int(selection.split(".")[0])
            tasks = context.user_data.get("edit_tasks", [])
            
            if 1 <= task_number <= len(tasks):
                context.user_data["editing_task_index"] = task_number - 1
                old_task_name = tasks[task_number - 1]["name"]
                
                await update.message.reply_text(
                    f"✏️ **ویرایش کار**\n\n"
                    f"کار فعلی: {old_task_name}\n\n"
                    f"نام جدید رو وارد کن:",
                    reply_markup=ReplyKeyboardRemove()
                )
                return EDIT_TASK_ACTION
        except Exception as e:
            logging.error(f"Error in edit selection: {e}")
    
    await update.message.reply_text("❌ لطفاً از گزینه‌ها استفاده کن")
    return EDIT_TASK_SELECT

async def handle_edit_task_action(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    new_task_name = update.message.text.strip()
    
    if not new_task_name:
        await update.message.reply_text("❌ نام کار نمی‌تونه خالی باشه!")
        return EDIT_TASK_ACTION
    
    task_index = context.user_data.get("editing_task_index")
    date_key = context.user_data.get("edit_date_key")
    tasks = context.user_data.get("edit_tasks", [])
    
    if task_index is not None and date_key and tasks:
        old_name = tasks[task_index]["name"]
        tasks[task_index]["name"] = new_task_name
        
        # آپدیت در دیتابیس
        users_db[user_id]["dated_tasks"][date_key] = tasks
        Database.save(users_db)
        
        await update.message.reply_text(
            f"✅ **کار ویرایش شد!**\n\n"
            f"📝 **قدیمی:** {old_name}\n"
            f"📝 **جدید:** {new_task_name}"
        )
    
    return await show_main_menu(update, context)

async def show_delete_tasks(update: Update, context: CallbackContext, date_key):
    user_id = str(update.effective_user.id)
    
    tasks = []
    if date_key in users_db[user_id].get("dated_tasks", {}):
        tasks = users_db[user_id]["dated_tasks"][date_key]
    
    if not tasks:
        await update.message.reply_text("📝 هیچ کاری برای حذف وجود نداره!")
        return await show_main_menu(update, context)
    
    keyboard = []
    for i, task in enumerate(tasks, 1):
        keyboard.append([KeyboardButton(f"{i}. 🗑️ {task['name'][:30]}")])
    
    keyboard.append([KeyboardButton("🏠 منوی اصلی")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    tasks_list = "\n".join([f"{i}. {task['name']}" for i, task in enumerate(tasks, 1)])
    
    await update.message.reply_text(
        f"🗑️ **حذف کارها**\n\n"
        f"کدوم کار رو می‌خوای حذف کنی؟\n\n"
        f"{tasks_list}",
        reply_markup=reply_markup
    )
    
    context.user_data["delete_tasks"] = tasks
    context.user_data["delete_date_key"] = date_key
    return DELETE_TASK_SELECT

async def handle_delete_task_select(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    selection = update.message.text
    
    if "منوی اصلی" in selection:
        return await show_main_menu(update, context)
    
    if selection and selection[0].isdigit():
        try:
            task_number = int(selection.split(".")[0])
            tasks = context.user_data.get("delete_tasks", [])
            date_key = context.user_data.get("delete_date_key")
            
            if 1 <= task_number <= len(tasks):
                deleted_task = tasks[task_number - 1]
                
                # حذف از دیتابیس
                users_db[user_id]["dated_tasks"][date_key].pop(task_number - 1)
                
                # اگر لیست خالی شد، تاریخ رو حذف کن
                if not users_db[user_id]["dated_tasks"][date_key]:
                    del users_db[user_id]["dated_tasks"][date_key]
                
                Database.save(users_db)
                
                await update.message.reply_text(
                    f"✅ **کار حذف شد!**\n\n"
                    f"🗑️ **کار حذف شده:** {deleted_task['name']}"
                )
                
                return await show_main_menu(update, context)
        except Exception as e:
            logging.error(f"Error in delete selection: {e}")
    
    await update.message.reply_text("❌ لطفاً از گزینه‌ها استفاده کن")
    return DELETE_TASK_SELECT

async def view_tasks_select_date(update: Update, context: CallbackContext) -> int:
    return await select_year(update, context, "view")

async def show_tasks_for_date(update: Update, context: CallbackContext, date_key, date_display):
    user_id = str(update.effective_user.id)
    
    all_tasks = []
    
    # اگر تاریخ امروز باشد، کارهای روزانه را هم نشان بده
    if date_key == get_date_key():
        for task in users_db[user_id].get("daily_tasks", []):
            status = "✅" if task.get("completed", False) else "◻️"
            all_tasks.append(f"📅 {status} {task['name']}")
    
    # کارهای ویژه آن تاریخ
    if date_key in users_db[user_id].get("dated_tasks", {}):
        for task in users_db[user_id]["dated_tasks"][date_key]:
            status = "✅" if task.get("completed", False) else "◻️"
            all_tasks.append(f"⭐ {status} {task['name']}")
    
    tasks_text = "\n".join(all_tasks) if all_tasks else "📝 هیچ کاری برای این تاریخ ثبت نشده"
    
    # نمایش تاریخ
    try:
        date_obj = datetime.strptime(date_key, "%Y-%m-%d")
        jdate = jdatetime.datetime.fromgregorian(datetime=date_obj)
        
        persian_days = {
            'Saturday': 'شنبه', 'Sunday': 'یکشنبه', 'Monday': 'دوشنبه',
            'Tuesday': 'سه‌شنبه', 'Wednesday': 'چهارشنبه',
            'Thursday': 'پنجشنبه', 'Friday': 'جمعه'
        }
        english_day = date_obj.strftime('%A')
        persian_day = persian_days.get(english_day, english_day)
        
        date_info = f"""
📅 **تاریخ درخواستی:**

🇮🇷 **شمسی:** {jdate.strftime('%Y/%m/%d')} - {jdate.strftime('%A')}
🌍 **میلادی:** {date_obj.strftime('%Y-%m-%d')} - {persian_day}
"""
    except:
        date_info = f"📅 **تاریخ:** {date_display}"
    
    response_text = f"""
{date_info}

📋 **برنامه کاری:**

{tasks_text}
"""
    
    keyboard = [[KeyboardButton("🏠 منوی اصلی")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(response_text, reply_markup=reply_markup)
    return MAIN_MENU

async def show_today_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    today_key = get_date_key()
    
    all_tasks = []
    
    # کارهای روزانه
    for task in users_db[user_id].get("daily_tasks", []):
        status = "✅" if task.get("completed", False) else "◻️"
        all_tasks.append(f"📅 {status} {task['name']}")
    
    # کارهای ویژه امروز
    if today_key in users_db[user_id].get("dated_tasks", {}):
        for task in users_db[user_id]["dated_tasks"][today_key]:
            status = "✅" if task.get("completed", False) else "◻️"
            all_tasks.append(f"⭐ {status} {task['name']}")
    
    tasks_text = "\n".join(all_tasks) if all_tasks else "📝 هیچ کاری برای امروز ثبت نشده"
    
    response_text = f"""
{get_three_calendars()}

📅 **برنامه امروز:**

{tasks_text}
"""
    
    keyboard = [
        [KeyboardButton("🔧 مدیریت کارها"), KeyboardButton("✅ چک لیست امروز")],
        [KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(response_text, reply_markup=reply_markup)
    return MAIN_MENU

async def show_checklist(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    today_key = get_date_key()
    
    checklist_tasks = []
    
    # کارهای روزانه
    for task in users_db[user_id].get("daily_tasks", []):
        checklist_tasks.append({
            "name": task["name"],
            "completed": task.get("completed", False),
            "type": "daily"
        })
    
    # کارهای ویژه امروز
    if today_key in users_db[user_id].get("dated_tasks", {}):
        for task in users_db[user_id]["dated_tasks"][today_key]:
            checklist_tasks.append({
                "name": task["name"],
                "completed": task.get("completed", False),
                "type": "special"
            })
    
    if not checklist_tasks:
        await update.message.reply_text("📝 امروز هیچ کاری برای چک لیست وجود نداره!")
        return await show_main_menu(update, context)
    
    keyboard = []
    for i, task in enumerate(checklist_tasks, 1):
        status = "✅" if task["completed"] else "❌"
        keyboard.append([KeyboardButton(f"{i}. {status} {task['name'][:30]}")])
    
    keyboard.append([KeyboardButton("💾 ثبت و ذخیره"), KeyboardButton("🏠 منوی اصلی")])
    
    context.user_data["checklist_tasks"] = checklist_tasks
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    checklist_text = "\n".join([f"{i}. {'✅' if task['completed'] else '❌'} {task['name']}" 
                              for i, task in enumerate(checklist_tasks, 1)])
    
    await update.message.reply_text(
        f"✅ **چک لیست امروز**\n\n"
        f"{get_three_calendars()}\n"
        f"{checklist_text}\n\n"
        "روی هر کار کلیک کن تا وضعیتش تغییر کنه:",
        reply_markup=reply_markup
    )
    return TASK_CHECKLIST

async def handle_checklist_selection(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    today_key = get_date_key()
    
    if "منوی اصلی" in message_text:
        return await show_main_menu(update, context)
    
    elif "ثبت و ذخیره" in message_text:
        await update.message.reply_text("✅ وضعیت کارها ذخیره شد!")
        return await show_main_menu(update, context)
    
    elif message_text and message_text[0].isdigit():
        try:
            task_number = int(message_text.split(".")[0])
            checklist_tasks = context.user_data.get("checklist_tasks", [])
            
            if 1 <= task_number <= len(checklist_tasks):
                task = checklist_tasks[task_number - 1]
                task["completed"] = not task["completed"]
                
                # آپدیت در دیتابیس
                if task["type"] == "daily":
                    for db_task in users_db[user_id]["daily_tasks"]:
                        if db_task["name"] == task["name"]:
                            db_task["completed"] = task["completed"]
                else:
                    for db_task in users_db[user_id]["dated_tasks"][today_key]:
                        if db_task["name"] == task["name"]:
                            db_task["completed"] = task["completed"]
                
                Database.save(users_db)
                
                status = "تکمیل شد ✅" if task["completed"] else "لغو تکمیل ❌"
                await update.message.reply_text(f"✅ کار '{task['name']}' {status}!")
            
            return await show_checklist(update, context)
            
        except Exception as e:
            logging.error(f"Error in checklist: {e}")
            await update.message.reply_text("❌ خطا در به‌روزرسانی کار")
    
    return await show_checklist(update, context)

async def show_stats(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("📊 ۵ روز گذشته"), KeyboardButton("📊 ۱۰ روز گذشته")],
        [KeyboardButton("📊 این هفته"), KeyboardButton("📊 این ماه")],
        [KeyboardButton("📊 امسال"), KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📊 **آمار و گزارش**\n\n"
        "برای کدوم بازه زمانی می‌خوای آمار ببینی؟",
        reply_markup=reply_markup
    )
    return STATS_PERIOD

async def handle_stats_period(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    period = update.message.text
    
    if "منوی اصلی" in period:
        return await show_main_menu(update, context)
    
    end_date = datetime.now()
    
    if "۵ روز" in period:
        start_date = end_date - timedelta(days=5)
        period_name = "۵ روز گذشته"
    elif "۱۰ روز" in period:
        start_date = end_date - timedelta(days=10)
        period_name = "۱۰ روز گذشته"
    elif "هفته" in period:
        start_date = end_date - timedelta(days=7)
        period_name = "این هفته"
    elif "ماه" in period:
        start_date = end_date - timedelta(days=30)
        period_name = "این ماه"
    elif "امسال" in period:
        start_date = datetime(end_date.year, 1, 1)
        period_name = f"امسال ({end_date.year})"
    else:
        return await show_stats(update, context)
    
    total_tasks = 0
    completed_tasks = 0
    current_date = start_date
    
    while current_date <= end_date:
        date_key = get_date_key(current_date)
        
        # کارهای روزانه
        for task in users_db[user_id].get("daily_tasks", []):
            total_tasks += 1
            if task.get("completed", False):
                completed_tasks += 1
        
        # کارهای ویژه
        if date_key in users_db[user_id].get("dated_tasks", {}):
            for task in users_db[user_id]["dated_tasks"][date_key]:
                total_tasks += 1
                if task.get("completed", False):
                    completed_tasks += 1
        
        current_date += timedelta(days=1)
    
    completion_rate = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    
    progress_bar = "🟩" * (completed_tasks // max(1, total_tasks // 10)) + "⬜" * (10 - (completed_tasks // max(1, total_tasks // 10)))
    
    stats_text = f"""
📊 **آمار {period_name}**

{progress_bar}
✅ **کارهای انجام شده:** {completed_tasks} از {total_tasks}
📈 **نرخ تکمیل:** {completion_rate}%

📅 **بازه زمانی:** 
{start_date.strftime('%Y-%m-%d')} تا {end_date.strftime('%Y-%m-%d')}

{"🎉 عملکرد عالی!" if completion_rate >= 80 else "💪 خوبه، ادامه بده!" if completion_rate >= 50 else "🚀 نیاز به تلاش بیشتر!"}
"""
    
    await update.message.reply_text(stats_text)
    return await show_main_menu(update, context)

def send_daily_checklists():
    """ارسال پیام چک لیست روزانه به همه کاربران"""
    now = datetime.now()
    today_key = get_date_key(now)
    
    for user_id, user_data in users_db.items():
        try:
            if user_data.get("last_checklist_date") != today_key:
                logging.info(f"Should send checklist to user {user_id}")
                user_data["last_checklist_date"] = today_key
        except Exception as e:
            logging.error(f"Error sending checklist to {user_id}: {e}")
    
    Database.save(users_db)

def setup_scheduler():
    """تنظیم زمان‌بند برای ارسال پیام‌های خودکار"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        send_daily_checklists,
        trigger=CronTrigger(hour=8, minute=0, timezone=pytz.utc),
        id='daily_checklists'
    )
    scheduler.start()

def main():
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable is not set!")
        return
    
    if not os.path.exists(DB_FILE):
        Database.save({})
    
    application = Application.builder().token(TOKEN).build()
    
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
            MANAGE_TASKS_MENU: [
                MessageHandler(filters.Regex("^➕ اضافه کار جدید$"), lambda u, c: select_year(u, c, "add")),
                MessageHandler(filters.Regex("^✏️ ویرایش کار موجود$"), lambda u, c: select_year(u, c, "edit")),
                MessageHandler(filters.Regex("^🗑️ حذف کار$"), lambda u, c: select_year(u, c, "delete")),
                MessageHandler(filters.Regex("^🏠 منوی اصلی$"), show_main_menu)
            ],
            ADD_TASK_DATE_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_selection)
            ],
            ADD_TASK_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_task_content)
            ],
            EDIT_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_task_select)
            ],
            EDIT_TASK_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_task_action)
            ],
            DELETE_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delete_task_select)
            ],
            VIEW_TASKS_DATE_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_selection)
            ],
            TASK_CHECKLIST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_checklist_selection)
            ],
            STATS_PERIOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stats_period)
            ]
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
    
    
    print("⏰ Setting up daily checklists scheduler...")
    setup_scheduler()
    # تشخیص محیط اجرا
    if os.environ.get('RENDER'):
        # حالت Webhook برای رندر
        PORT = int(os.environ.get('PORT', 10000))
        WEBHOOK_URL = f"https://daily-tasks-bot.onrender.com"  # ❗ اینجا اسم پروژه خودت رو بنویس
        
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
            secret_token='WEBHOOK_SECRET'
        )
    else:
        # حالت Polling برای اجرای محلی
        print("🤖 ربات فعال شد! (Polling Mode)")
        application.run_polling()
    
    

if __name__ == '__main__':
    main()


