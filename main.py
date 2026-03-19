import sqlite3, random, string, os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ضع التوكن هنا أو في متغير بيئة BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN", "ضع_التوكن_هنا")
ADMIN_ID = 7900627755  # ضع معرف صاحب المحل هنا

# قاعدة البيانات
conn = sqlite3.connect("barbershop.db", check_same_thread=False)
cursor = conn.cursor()

# إعادة إنشاء الجدول بشكل صحيح
cursor.execute("DROP TABLE IF EXISTS queue")
cursor.execute("""
CREATE TABLE queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    code TEXT
)
""")

cursor.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)")
conn.commit()

default_products = [("زيت شعر", 1500), ("بوتين", 2000), ("عقدة", 1000), ("مقعد VIP", 5000)]
for p in default_products:
    cursor.execute("INSERT OR IGNORE INTO products (name, price) VALUES (?, ?)", p)
conn.commit()

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

# القائمة الرئيسية
async def show_main(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    keyboard = [
        [InlineKeyboardButton("احجز مكان 🪑", callback_data='book')],
        [InlineKeyboardButton("المنتجات 🛍️", callback_data='products')],
        [InlineKeyboardButton("إلغاء الحجز ❌", callback_data='cancel')],
        [InlineKeyboardButton("📱 أرسل رقمك للتواصل", callback_data='send_phone')],
        [InlineKeyboardButton("تواصل مع صاحب المحل 📞", callback_data='contact')],
        [InlineKeyboardButton("مواقيت العمل 🕒", callback_data='hours')]
    ]
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("نقص شخص 👤", callback_data='remove_one')])
        keyboard.append([InlineKeyboardButton("عدد الزبائن 👥", callback_data='count_queue')])
        keyboard.append([InlineKeyboardButton("قائمة الأكواد 🔑", callback_data='list_codes')])
        keyboard.append([InlineKeyboardButton("أرسل إشعار: حان دورك 📢", callback_data='notify_next')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "✂️ مرحبا بك في صالون الرجولة! اختر خدمة:"
    if edit:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# التعامل مع الأزرار
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == 'book':
        code = generate_code()
        cursor.execute("INSERT INTO queue (user_id, name, code) VALUES (?, ?, ?)", (user.id, user.first_name, code))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM queue")
        position = cursor.fetchone()[0]
        await query.message.edit_text(f"✅ تم حجز مكانك\nترتيبك: {position}\nكودك الخاص: {code}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))
        await context.bot.send_message(ADMIN_ID, f"📢 إشعار: {user.first_name} حجز مكان.\nترتيبه: {position}\nكوده: {code}")

    elif query.data == 'list_codes' and user.id == ADMIN_ID:
        cursor.execute("SELECT name, code FROM queue ORDER BY id ASC")
        rows = cursor.fetchall()
        if rows:
            text = "🔑 قائمة الأكواد:\n"
            for i, (name, code) in enumerate(rows, start=1):
                text += f"{i}: {code} ({name})\n"
        else:
            text = "🚫 لا يوجد زبائن في القائمة."
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))

    elif query.data == 'count_queue' and user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM queue")
        count = cursor.fetchone()[0]
        await query.message.edit_text(f"👥 عدد الزبائن الحاليين: {count}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))

    elif query.data == 'cancel':
        cursor.execute("DELETE FROM queue WHERE user_id=?", (user.id,))
        conn.commit()
        await query.message.edit_text("❌ تم إلغاء حجزك", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))
        await context.bot.send_message(ADMIN_ID, f"❌ إشعار: {user.first_name} ألغى حجزه.")

    elif query.data == 'send_phone':
        contact_button = KeyboardButton("📱 شارك رقمك", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
        await query.message.reply_text("📱 اضغط الزر لمشاركة رقم هاتفك مع صاحب المحل:", reply_markup=reply_markup)

    elif query.data == 'contact':
        await query.message.edit_text("📞 للتواصل:\nTelegram: @WH_S8\nهاتف: 0779109990", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))
    
    elif query.data == 'hours':
        await query.message.edit_text("🕒 مواقيت العمل:\nمن 09:00 صباحًا إلى 21:00 مساءً يوميًا.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))
    
    elif query.data == 'remove_one' and user.id == ADMIN_ID:
        cursor.execute("SELECT id, user_id, name FROM queue ORDER BY id ASC LIMIT 1")
        first = cursor.fetchone()
        if first:
            cursor.execute("DELETE FROM queue WHERE id=?", (first[0],))
            conn.commit()
            cursor.execute("SELECT user_id, name FROM queue ORDER BY id ASC")
            rows = cursor.fetchall()
            for i, (uid, name) in enumerate(rows, start=1):
                try:
                    await context.bot.send_message(uid, f"📢 إشعار: نقص شخص من القائمة.\nترتيبك الآن: {i}")
                except:
                    pass
            await query.message.edit_text("✅ تم إنقاص شخص من القائمة وإرسال إشعار للزبائن.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))
            await context.bot.send_message(ADMIN_ID, f"👤 إشعار: تم إنقاص شخص من القائمة.")
        else:
            await query.message.edit_text("🚫 لا يوجد زبائن في القائمة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))

    elif query.data == 'notify_next' and user.id == ADMIN_ID:
        cursor.execute("SELECT user_id, name, code FROM queue ORDER BY id ASC LIMIT 1")
        next_user = cursor.fetchone()
        if next_user:
            await context.bot.send_message(next_user[0], f"📢 حان دورك، تفضل للدخول!\nكودك: {next_user[2]}")
            await query.message.edit_text("✅ تم إرسال إشعار للشخص الأول في القائمة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))
            await context.bot.send_message(ADMIN_ID, f"📢 إشعار: تم إعلام {next_user[1]} أن دوره قد حان. كوده: {next_user[2]}")
        else:
            await query.message.edit_text("🚫 لا يوجد زبائن في القائمة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data='main')]]))

    elif query.data == 'main':
        await show_main(update, context, edit=True)

# استقبال رقم الهاتف
async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
        name = update.message.contact.first_name
        await context.bot.send_message(ADMIN_ID, f"📱 إشعار: {name} أرسل رقمه للتواصل: {phone}")
        await update.message.reply_text("✅ تم إرسال
