import os
import logging
from datetime import datetime
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ma'lumotlar bazasi yaratish
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_date TEXT
        )
    ''')
    
    # Guruhlar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY,
            group_name TEXT,
            added_date TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# Foydalanuvchini bazaga qo'shish
def add_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, joined_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    conn.close()

# Guruhni bazaga qo'shish
def add_group(group_id, group_name, is_admin=0):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO groups (group_id, group_name, added_date, is_admin)
        VALUES (?, ?, ?, ?)
    ''', (group_id, group_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), is_admin))
    
    conn.commit()
    conn.close()

# Admin qilingan guruhlar ro'yxati
def get_admin_groups():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT group_id, group_name FROM groups WHERE is_admin = 1')
    groups = cursor.fetchall()
    
    conn.close()
    return groups

# Barcha foydalanuvchilar ro'yxati
def get_all_users():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    
    conn.close()
    return [user[0] for user in users]

# Statistika olish
def get_stats():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    users_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM groups')
    groups_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM groups WHERE is_admin = 1')
    admin_groups_count = cursor.fetchone()[0]
    
    conn.close()
    return users_count, groups_count, admin_groups_count

# Admin foydalanuvchi ID'si (o'zingizning Telegram ID'ingizni kiriting)
ADMIN_USER_ID = 7563536517  # Bu yerga o'zingizning Telegram ID'ingizni kiriting

# Start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    
    # Guruhga qo'shish tugmasi
    keyboard = [
        [InlineKeyboardButton("Guruhga qo'shish", 
                             url=f"https://t.me/{context.bot.username}?startgroup=true")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """Salom! Men guruhlardagi kirdi-chiqdi xabarlarni o'chirib beruvchi botman.

Meni guruhingizga qo'shing va admin qiling.

Men quyidagi ishlarni bajaraman:
• Guruhga yangi a'zolar qo'shilganda "kirdi" xabarini o'chiraman
• Guruhga hech qanday ortiqcha xabar yozmayman"""
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Admin panel
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Sizda admin huquqi yo'q!")
        return
    
    users_count, groups_count, admin_groups_count = get_stats()
    
    keyboard = [
        [InlineKeyboardButton("Statistika", callback_data="stats")],
        [InlineKeyboardButton("Admin guruhlar", callback_data="admin_groups")],
        [InlineKeyboardButton("Guruhlarga xabar", callback_data="broadcast_groups")],
        [InlineKeyboardButton("Foydalanuvchilarga xabar", callback_data="broadcast_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_text = f"""Admin Panel

Statistika:
• Foydalanuvchilar: {users_count}
• Guruhlar: {groups_count}
• Admin guruhlar: {admin_groups_count}"""
    
    await update.message.reply_text(admin_text, reply_markup=reply_markup)

# Callback handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("Sizda admin huquqi yo'q!")
        return
    
    if query.data == "stats":
        users_count, groups_count, admin_groups_count = get_stats()
        stats_text = f"""Bot Statistikasi

Foydalanuvchilar: {users_count}
Guruhlar: {groups_count}
Admin guruhlar: {admin_groups_count}
Oxirgi yangilanish: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        await query.edit_message_text(stats_text)
    
    elif query.data == "admin_groups":
        admin_groups = get_admin_groups()
        if admin_groups:
            groups_text = "Admin qilingan guruhlar:\n\n"
            for group_id, group_name in admin_groups:
                groups_text += f"• {group_name} (ID: {group_id})\n"
        else:
            groups_text = "Hozircha admin qilingan guruhlar yo'q"
        await query.edit_message_text(groups_text)
    
    elif query.data == "broadcast_groups":
        context.user_data['broadcast_mode'] = 'groups'
        await query.edit_message_text("Barcha guruhlarga yuboriladigan xabarni yozing:")
    
    elif query.data == "broadcast_users":
        context.user_data['broadcast_mode'] = 'users'
        await query.edit_message_text("Barcha foydalanuvchilarga yuboriladigan xabarni yozing:")

# Broadcast xabar yuborish
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    if 'broadcast_mode' not in context.user_data:
        return
    
    message_text = update.message.text
    broadcast_mode = context.user_data['broadcast_mode']
    
    if broadcast_mode == 'groups':
        admin_groups = get_admin_groups()
        success_count = 0
        
        for group_id, group_name in admin_groups:
            try:
                await context.bot.send_message(chat_id=group_id, text=message_text)
                success_count += 1
            except Exception as e:
                logger.error(f"Guruhga xabar yuborishda xato {group_id}: {e}")
        
        await update.message.reply_text(f"Xabar {success_count}/{len(admin_groups)} guruhga yuborildi")
    
    elif broadcast_mode == 'users':
        users = get_all_users()
        success_count = 0
        
        for user_id in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=message_text)
                success_count += 1
            except Exception as e:
                logger.error(f"Foydalanuvchiga xabar yuborishda xato {user_id}: {e}")
        
        await update.message.reply_text(f"Xabar {success_count}/{len(users)} foydalanuvchiga yuborildi")
    
    del context.user_data['broadcast_mode']

# Guruhga qo'shilganda - sodda versiya
async def handle_group_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot guruhga qo'shilganda ishga tushadi"""
    chat = update.effective_chat
    
    if chat.type in ['group', 'supergroup']:
        # Guruhni bazaga qo'shish
        add_group(chat.id, chat.title)
        
        # Bot admin ekanligini tekshirish
        try:
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if bot_member.status == 'administrator':
                conn = sqlite3.connect('bot_data.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE groups SET is_admin = 1 WHERE group_id = ?', (chat.id,))
                conn.commit()
                conn.close()
                logger.info(f"Bot {chat.title} guruhida admin qilindi")
        except Exception as e:
            logger.error(f"Admin holatini tekshirishda xato: {e}")

# Yangi a'zo qo'shilganda xabarni o'chirish
async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # Faqat guruhlar uchun
    if message.chat.type not in ['group', 'supergroup']:
        return
    
    # Yangi a'zolar qo'shilganda xabarni o'chirish
    if message.new_chat_members:
        try:
            await message.delete()
            logger.info(f"Yangi a'zo xabari o'chirildi: {message.chat.title}")
        except Exception as e:
            logger.error(f"Xabarni o'chirishda xato: {e}")

# Chiqib ketganda xabarni o'chirish
async def handle_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # Faqat guruhlar uchun
    if message.chat.type not in ['group', 'supergroup']:
        return
    
    # A'zo chiqib ketganda xabarni o'chirish
    if message.left_chat_member:
        try:
            await message.delete()
            logger.info(f"Chiqib ketgan a'zo xabari o'chirildi: {message.chat.title}")
        except Exception as e:
            logger.error(f"Xabarni o'chirishda xato: {e}")

def main():
    # Ma'lumotlar bazasini yaratish
    init_db()
    
    # Bot tokenini o'rnatish (BotFather'dan olgan tokeningizni kiriting)
    BOT_TOKEN = "7489430978:AAFJ9Y0Zpg6Fy_rTHsPKBB0Tj6n3-eN0Ox8"  # Bu yerga o'zingizning bot tokeningizni kiriting
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Bot tokenini kiriting!")
        return
    
    # Application yaratish
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlar qo'shish
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_broadcast))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_member))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS, handle_group_join))
    
    # Botni ishga tushirish
    print("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()