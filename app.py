import os
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import jdatetime
import json

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

MAIN_MENU, MANAGE_TASKS_MENU, ADD_TASK_DATE_SELECT, ADD_TASK_CONTENT = range(4)

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
سلام {user_name} عزیز!

به ربات مدیریت کارها خوش آمدي.

منوي اصلي:
📅 برنامه امروز
🔧 مديريت کارها
📊 آمار و گزارش
"""
    await update.message.reply_text(welcome_text, reply_markup=ReplyKeyboardRemove())
    return await show_main_menu(update, context)

async def show_main_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("📅 برنامه امروز"), KeyboardButton("🔧 مديريت کارها")],
        [KeyboardButton("📊 آمار و گزارش")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "منوي اصلي - لطفا انتخاب کن:",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def show_today_tasks(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    today_key = get_date_key()
    
    tasks = []
    if today_key in users_db[user_id].get("dated_tasks", {}):
        tasks = users_db[user_id]["dated_tasks"][today_key]
    
    tasks_text = "\n".join([f"• {task['name']}" for task in tasks]) if tasks else "هيچ کاري براي امروز ثبت نشده"
    
    await update.message.reply_text(
        f"📅 برنامه امروز:\n\n{tasks_text}"
    )
    return await show_main_menu(update, context)

async def show_manage_tasks_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("➕ اضافه کار جديد")],
        [KeyboardButton("🏠 منوي اصلي")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "مديريت کارها - انتخاب کن:",
        reply_markup=reply_markup
    )
    return MANAGE_TASKS_MENU

async def select_year(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("📅 1404"), KeyboardButton("📅 1405")],
        [KeyboardButton("🏠 منوي اصلي")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "انتخاب سال:",
        reply_markup=reply_markup
    )
    return ADD_TASK_DATE_SELECT

async def handle_date_selection(update: Update, context: CallbackContext) -> int:
    selection = update.message.text
    
    if "منوي اصلي" in selection:
        return await show_main_menu(update, context)
    
    if "1404" in selection or "1405" in selection:
        year = 1404 if "1404" in selection else 1405
        context.user_data["selected_year"] = year
        
        keyboard = [
            [KeyboardButton("فروردين"), KeyboardButton("ارديبهشت")],
            [KeyboardButton("🏠 منوي اصلي")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"سال {year} - انتخاب ماه:",
            reply_markup=reply_markup
        )
        return ADD_TASK_DATE_SELECT
    
    months = ["فروردين", "ارديبهشت"]
    if selection in months:
        year = context.user_data.get("selected_year", 1404)
        context.user_data["selected_month"] = selection
        
        await update.message.reply_text(
            f"کارهايت رو براي {selection} {year} وارد کن (هر خط يک کار):",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_TASK_CONTENT
    
    return ADD_TASK_DATE_SELECT

async def handle_add_task_content(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    tasks_text = update.message.text.strip()
    
    tasks_list = [task.strip() for task in tasks_text.split('\n') if task.strip()]
    
    if not tasks_list:
        await update.message.reply_text("هيچ کاري وارد نکردي!")
        return await show_main_menu(update, context)
    
    year = context.user_data.get("selected_year", 1404)
    month = context.user_data.get("selected_month", "فروردين")
    
    date_key = get_date_key()
    
    if date_key not in users_db[user_id]["dated_tasks"]:
        users_db[user_id]["dated_tasks"][date_key] = []
    
    for task_name in tasks_list:
        users_db[user_id]["dated_tasks"][date_key].append({
            "name": task_name,
            "completed": False,
            "created_at": get_date_key()
        })
    
    Database.save(users_db)
    
    await update.message.reply_text(
        f"✅ {len(tasks_list)} کار ثبت شد!\n\n"
        f"براي {month} {year}"
    )
    
    return await show_main_menu(update, context)

async def show_stats(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    
    total_tasks = 0
    completed_tasks = 0
    
    for date_tasks in users_db[user_id].get("dated_tasks", {}).values():
        total_tasks += len(date_tasks)
        completed_tasks += sum(1 for task in date_tasks if task.get("completed", False))
    
    completion_rate = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    
    await update.message.reply_text(
        f"📊 آمار شما:\n\n"
        f"✅ کارهاي انجام شده: {completed_tasks} از {total_tasks}\n"
        f"📈 نرخ تکميل: {completion_rate}%"
    )
    return await show_main_menu(update, context)

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
                MessageHandler(filters.Regex("^📅 برنامه امروز$"), show_today_tasks),
                MessageHandler(filters.Regex("^🔧 مديريت کارها$"), show_manage_tasks_menu),
                MessageHandler(filters.Regex("^📊 آمار و گزارش$"), show_stats)
            ],
            MANAGE_TASKS_MENU: [
                MessageHandler(filters.Regex("^➕ اضافه کار جديد$"), select_year),
                MessageHandler(filters.Regex("^🏠 منوي اصلي$"), show_main_menu)
            ],
            ADD_TASK_DATE_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_selection)
            ],
            ADD_TASK_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_task_content)
            ]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    application.add_handler(conv_handler)
    
    print("🤖 ربات فعال شد!")
    application.run_polling()

if __name__ == "__main__":
    main()
