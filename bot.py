from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from ultimate_bomber import UltimateBomberTelegram
import os
import json
import asyncio

# ایجاد نمونه بمب‌افکن
bomber = UltimateBomberTelegram()

# دیکشنری برای ذخیره وضعیت کاربران
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    user_id = update.effective_user.id
    user_sessions[user_id] = {"phone": None, "attack_type": None, "requests": 100}
    
    welcome_text = """
🤖 **Ultimate Bomber Bot** 🚀

یک بمب‌افکن پیشرفته پیامک و تماس با ۲۰۰+ سرویس فعال

**دستورات اصلی:**
🔹 /bomb - شروع حمله جدید
🔹 /stop - توقف حمله فعلی  
🔹 /status - وضعیت فعلی
🔹 /help - راهنمای کامل

**مثال استفاده:**
1. ابتدا شماره را وارد کنید
2. سپس نوع حمله را انتخاب کنید
3. تعداد درخواست‌ها را مشخص کنید

⚠️ **هشدار:** این ربات فقط برای اهداف آموزشی ارائه شده است.
    """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def bomb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع حمله جدید"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"phone": None, "attack_type": None, "requests": 100}
    
    # اگر شماره در کامند ارائه شده
    if context.args:
        phone = context.args[0]
        if any(c.isdigit() for c in phone):
            user_sessions[user_id]["phone"] = phone
            await ask_attack_type(update, context)
            return
    
    await update.message.reply_text("📱 لطفا شماره تلفن را وارد کنید:\n\nمثال: `09123456789`", parse_mode='Markdown')

async def ask_attack_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پرسش نوع حمله"""
    keyboard = [
        [{"text": "📱 فقط SMS", "callback_data": "sms"}],
        [{"text": "📞 فقط تماس", "callback_data": "call"}],
        [{"text": "💣 هر دو (SMS + تماس)", "callback_data": "both"}]
    ]
    
    await update.message.reply_text(
        "🎯 **نوع حمله را انتخاب کنید:**",
        reply_markup={"inline_keyboard": keyboard},
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌های اینلاین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"phone": None, "attack_type": None, "requests": 100}
    
    if data in ["sms", "call", "both"]:
        user_sessions[user_id]["attack_type"] = data
        await ask_requests_count(query, context)
    elif data.startswith("requests_"):
        requests_count = int(data.split("_")[1])
        user_sessions[user_id]["requests"] = requests_count
        await start_attack(query, context)

async def ask_requests_count(update, context: ContextTypes.DEFAULT_TYPE):
    """پرسش تعداد درخواست‌ها"""
    if hasattr(update, 'message'):
        message = update.message
    else:
        message = update.callback_query.message
    
    keyboard = [
        [{"text": "50 درخواست", "callback_data": "requests_50"}],
        [{"text": "100 درخواست", "callback_data": "requests_100"}],
        [{"text": "200 درخواست", "callback_data": "requests_200"}],
        [{"text": "500 درخواست", "callback_data": "requests_500"}]
    ]
    
    await message.reply_text(
        "🔢 **تعداد درخواست‌ها را انتخاب کنید:**",
        reply_markup={"inline_keyboard": keyboard},
        parse_mode='Markdown'
    )

async def start_attack(update, context: ContextTypes.DEFAULT_TYPE):
    """شروع عملیات حمله"""
    if hasattr(update, 'message'):
        message = update.message
        user_id = update.effective_user.id
    else:
        message = update.callback_query.message
        user_id = update.callback_query.from_user.id
    
    user_data = user_sessions.get(user_id, {})
    phone = user_data.get("phone")
    attack_type = user_data.get("attack_type", "both")
    requests_count = user_data.get("requests", 100)
    
    if not phone:
        await message.reply_text("❌ شماره تلفن تنظیم نشده است!")
        return
    
    # اعتبارسنجی شماره
    if not any(c.isdigit() for c in phone):
        await message.reply_text("❌ شماره تلفن معتبر نیست!")
        return
    
    # نمایش اطلاعات حمله
    attack_type_text = {
        "sms": "📱 فقط SMS",
        "call": "📞 فقط تماس", 
        "both": "💣 SMS + تماس"
    }.get(attack_type, "💣 SMS + تماس")
    
    info_text = f"""
🎯 **شروع حمله**

📞 شماره: `{phone}`
💣 نوع: {attack_type_text}
🔢 تعداد: {requests_count} درخواست

⏳ لطفا منتظر بمانید...
    """
    
    status_message = await message.reply_text(info_text, parse_mode='Markdown')
    
    try:
        # شروع حمله
        result = bomber.start_attack(phone, requests_count, attack_type)
        
        if "error" in result:
            await status_message.edit_text(f"❌ **خطا:**\n`{result['error']}`", parse_mode='Markdown')
        else:
            # ساخت متن نتیجه
            result_text = f"""
🎯 **حمله تکمیل شد!** ✅

📞 شماره: `{result['phone']}`
⏱️ زمان: {result['duration']}
📊 درخواست‌ها: {result['total_requests']}
✅ موفق: {result['successful']}
❌ ناموفق: {result['failed']}
🎯 نرخ موفقیت: {result['success_rate']}
⚡ سرعت: {result['speed']}

🛠️ **سرویس‌های فعال:**
"""
            
            # اضافه کردن سرویس‌های فعال
            if result.get('working_services'):
                for service in result['working_services'][:5]:  # فقط 5 تا اول
                    result_text += f"• {service}\n"
            else:
                result_text += "• هیچ سرویس فعالی یافت نشد\n"
            
            result_text += "\n🔄 برای حمله جدید /bomb را بفرستید"
            
            await status_message.edit_text(result_text, parse_mode='Markdown')
            
    except Exception as e:
        await status_message.edit_text(f"❌ **خطا در اجرا:**\n`{str(e)}`", parse_mode='Markdown')

async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """توقف حمله"""
    bomber.stop_attack()
    await update.message.reply_text("🛑 **حمله متوقف شد**", parse_mode='Markdown')

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وضعیت فعلی"""
    status = "🟢 فعال" if bomber.is_running else "🔴 غیرفعال"
    
    status_text = f"""
📊 **وضعیت بمب‌افکن**

🔄 وضعیت: {status}
✅ موفق: {bomber.success_count}
❌ ناموفق: {bomber.failed_count}
🧵 حداکثر thread: {bomber.max_threads}

🛠️ سرویس‌های فعال: {len(bomber.working_services)}
"""
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای کامل"""
    help_text = """
📖 **راهنمای Ultimate Bomber Bot**

**دستورات:**
🔹 /start - شروع کار با ربات
🔹 /bomb - شروع حمله جدید
🔹 /stop - توقف حمله فعلی
🔹 /status - وضعیت فعلی
🔹 /help - این راهنما

**مراحل حمله:**
1. شماره تلفن را وارد کنید
2. نوع حمله را انتخاب کنید
3. تعداد درخواست‌ها را مشخص کنید
4. منتظر نتیجه بمانید

**انواع حمله:**
📱 **SMS** - فقط ارسال پیامک
📞 **Call** - فقط تماس صوتی  
💣 **Both** - هر دو (پیامک + تماس)

**نکات مهم:**
⚠️ این ربات فقط برای اهداف آموزشی است
⚡ سرعت بستگی به سرور و سرویس‌ها دارد
🔒 اطلاعات شما محفوظ می‌ماند

**پشتیبانی:** @YourSupportChannel
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"phone": None, "attack_type": None, "requests": 100}
    
    # اگر متن شامل شماره است
    if any(c.isdigit() for c in text) and len(text) >= 10:
        user_sessions[user_id]["phone"] = text
        await ask_attack_type(update, context)
    else:
        await update.message.reply_text("❌ لطفا یک شماره تلفن معتبر وارد کنید")

def main():
    """تابع اصلی اجرای ربات"""
    # دریافت توکن از environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
        return
    
    # ایجاد اپلیکیشن تلگرام
    app = Application.builder().token(token).build()
    
    # اضافه کردن handlerها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bomb", bomb_handler))
    app.add_handler(CommandHandler("stop", stop_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # اضافه کردن handler برای دکمه‌های اینلاین
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # شروع ربات
    print("🤖 ربات Ultimate Bomber شروع به کار کرد...")
    print("🔗 در حال گوش دادن به پیام‌ها...")
    
    app.run_polling()

if __name__ == "__main__":
    # غیرفعال کردن هشدارهای SSL
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main()
