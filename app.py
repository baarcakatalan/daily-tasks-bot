import os
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import jdatetime
import json

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# حالت‌های مکالمه
MAIN_MENU, MANAGE_TASKS_MENU, ADD_TASK_DATE_SELECT, ADD_TASK_CONTENT, \
EDIT_TASK_SELECT, DELETE_TASK_SELECT, TASK_CHECKLIST, STATS_PERIOD = range(8)

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
    
    return f"""
📅 تاریخ امروز:

🇮🇷 شمسی: {jdate.strftime('%Y/%m/%d')} - {jdate.strftime('%A')}
🌍 میلادی: {now.strftime('%Y-%m-%d')}
"""

def get_date_key(date_obj=None):
    if date_obj is None:
        date_obj = datetime.now()
    return date_obj.strftime("%Y-%m-%d")

async def start(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    if user_id not in users_db:
        users_db[user_id] = {
            "daily_tasks": [],
            "dated_tasks": {},
            "created_at": get_date_key(),
            "user_name": user_name
        }
        Database.save(users_db)
    
    welcome_text = f"""
👋 سلام {user_name} عزیز!

به ربات مدیریت کارهای روزانه خوش آمدی.

🏠 منوی اصلی شامل:

📅 برنامه امروز - مشاهده کارهای امروز
🔧 مدیریت کارها - اضافه/ویرایش/حذف کارها  
📋 مشاهده برنامه - کارهای تاریخ مشخص
✅ چک لیست امروز - ثبت انجام کارها
📊 آمار و گزارش - عملکرد شما
"""
    await update.message.reply_text(welcome_text, reply_markup=ReplyKeyboardRemove())
    return await show_main_menu(update, context)

async def show_main_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("📅 برنامه امروز"), KeyboardButton("🔧 مدیریت کارها")],
        [KeyboardButton("📋 مشاهده برنامه"), KeyboardButton("✅ چک لیست امروز")],
        [KeyboardButton("📊 آمار و گزارش")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🏠 منوی اصلی - لطفا انتخاب کن:",
        reply_markup=reply_markup
    )
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

📅 برنامه امروز:

{tasks_text}
"""
    
    keyboard = [
        [KeyboardButton("🔧 مدیریت کارها"), KeyboardButton("✅ چک لیست امروز")],
        [KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(response_text, reply_markup=reply_markup)
    return MAIN_MENU

async def show_manage_tasks_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("➕ اضافه کار جدید"), KeyboardButton("✏️ ویرایش کار")],
        [KeyboardButton("🗑️ حذف کار"), KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔧 مدیریت کارها - انتخاب کن:",
        reply_markup=reply_markup
    )
    return MANAGE_TASKS_MENU

async def select_year_for_add(update: Update, context: CallbackContext):
    context.user_data["purpose"] = "add"
    return await select_year(update, context)

async def select_year_for_edit(update: Update, context: CallbackContext):
    context.user_data["purpose"] = "edit" 
    return await select_year(update, context)

async def select_year_for_delete(update: Update, context: CallbackContext):
    context.user_data["purpose"] = "delete"
    return await select_year(update, context)

async def select_year(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("📅 1404"), KeyboardButton("📅 1405")],
        [KeyboardButton("🏠 منوی اصلی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "انتخاب سال:",
        reply_markup=reply_markup
    )
    return ADD_TASK_DATE_SELECT

async def handle_date_selection(update: Update, context: CallbackContext) -> int:
    selection = update.message.text
    purpose = context.user_data.get("purpose", "add")
    
    if "منوی اصلی" in selection:
        return await show_main_menu(update, context)
    
    if "1404" in selection or "1405" in selection:
        year = 1404 if "1404" in selection else 1405
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
            f"سال {year} - انتخاب ماه:",
            reply_markup=reply_markup
        )
        return ADD_TASK_DATE_SELECT
    
    months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", 
              "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    
    if selection in months:
        year = context.user_data.get("selected_year", 1404)
        context.user_data["selected_month"] = selection
        
        if purpose == "add":
            await update.message.reply_text(
                f"کارهایت رو برای {selection} {year} وارد کن (هر خط یک کار):\n\n"
                "مثال:\n"
                "ورزش صبحگاهی\n"
                "مطالعه 30 دقیقه\n"
                "پروژه برنامه نویسی",
                reply_markup=ReplyKeyboardRemove()
            )
            return ADD_TASK_CONTENT
        else:
            # برای ویرایش و حذف، فعلاً پیام ساده می‌دهیم
            await update.message.reply_text(
                f"این قابلیت برای {selection} {year} آماده است!"
            )
            return await show_main_menu(update, context)
    
    return ADD_TASK_DATE_SELECT

async def handle_add_task_content(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    tasks_text = update.message.text.strip()
    
    tasks_list = [task.strip() for task in tasks_text.split('\n') if task.strip()]
    
    if not tasks_list:
        await update.message.reply_text("❌ هیچ کاری وارد نکردی!")
        return await show_main_menu(update, context)
    
    year = context.user_data.get("selected_year", 1404)
    month = context.user_data.get("selected_month", "فروردین")
    
    # ساخت تاریخ نمونه (امروز)
    date_key = get_date_key()
    
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
    
    tasks_preview = "\n".join([f"• {task}" for task in tasks_list[:3]])
    if len(tasks_list) > 3:
        tasks_preview += f"\n• و {len(tasks_list) - 3} کار دیگر..."
    
    await update.message.reply_text(
        f"✅ {len(tasks_list)} کار با موفقیت ثبت شد!\n\n"
        f"📅 تاریخ: {month} {year}\n"
        f"📋 کارها:\n{tasks_preview}"
    )
    
    return await show_main_menu(update, context)

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
    
    checklist_text = "\n".join([f"{i}. {'✅' if task['completed'] else '❌'} {task['name']}" 
                              for i, task in enumerate(checklist_tasks, 1)])
    
    await update.message.reply_text(
        f"✅ چک لیست امروز\n\n"
        f"{checklist_text}\n\n"
        "برای تغییر وضعیت کارها، از مدیریت کارها استفاده کن."
    )
    
    return await show_main_menu(update, context)

async def show_stats(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    
    total_tasks = 0
    completed_tasks = 0
    
    # محاسبه آمار از کارهای روزانه
    for task in users_db[user_id].get("daily_tasks", []):
        total_tasks += 1
        if task.get("completed", False):
            completed_tasks += 1
    
    # محاسبه آمار از کارهای ویژه
    for date_tasks in users_db[user_id].get("dated_tasks", {}).values():
        total_tasks += len(date_tasks)
        completed_tasks += sum(1 for task in date_tasks if task.get("completed", False))
    
    completion_rate = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    
    progress_bar = "🟩" * (completed_tasks // max(1, total_tasks // 10)) + "⬜" * (10 - (completed_tasks // max(1, total_tasks // 10)))
    
    stats_text = f"""
📊 آمار کلی شما

{progress_bar}
✅ کارهای انجام شده: {completed_tasks} از {total_tasks}
📈 نرخ تکمیل: {completion_rate}%

{"🎉 عملکرد عالی!" if completion_rate >= 80 else "💪 خوبه، ادامه بده!" if completion_rate >= 50 else "🚀 نیاز به تلاش بیشتر!"}
"""
    
    await update.message.reply_text(stats_text)
    return await show_main_menu(update, context)

async def view_tasks_select_date(update: Update, context: CallbackContext):
    context.user_data["purpose"] = "view"
    return await select_year(update, context)

def main():
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN not set!")
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
                MessageHandler(filters.Regex("^📋 مشاهده برنامه$"), view_tasks_select_date),
                MessageHandler(filters.Regex("^✅ چک لیست امروز$"), show_checklist),
                MessageHandler(filters.Regex("^📊 آمار و گزارش$"), show_stats)
            ],
            MANAGE_TASKS_MENU: [
                MessageHandler(filters.Regex("^➕ اضافه کار جدید$"), select_year_for_add),
                MessageHandler(filters.Regex("^✏️ ویرایش کار$"), select_year_for_edit),
                MessageHandler(filters.Regex("^🗑️ حذف کار$"), select_year_for_delete),
                MessageHandler(filters.Regex("^🏠 منوی اصلی$"), show_main_menu)
            ],
            ADD_TASK_DATE_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_selection)
            ],
            ADD_TASK_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_task_content)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # دستورات مستقیم
    application.add_handler(CommandHandler("today", show_today_tasks))
    application.add_handler(CommandHandler("checklist", show_checklist))
    application.add_handler(CommandHandler("stats", show_stats))
    
    print("🤖 ربات فعال شد! (Polling Mode)")
    application.run_polling()

if __name__ == "__main__":
    main()
