import os
import logging
import asyncio
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from PIL import Image

logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)

TOKEN = "8703848956:AAGl1OWsR51UisC7o2VWEXrv48cMZGHVqd0"
user_sessions = {}

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("🚀 **PDF Bot Online!**\nSend an album of photos or a .docx/.pptx (Max 10MB).")

# --- IMAGES TO PDF ---
async def handle_images(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {'images': [], 'timer': None}

    photo_file = await update.message.photo[-1].get_file()
    file_name = f"img_{user_id}_{len(user_sessions[user_id]['images'])}.jpg"
    await photo_file.download_to_drive(file_name)
    user_sessions[user_id]['images'].append(file_name)

    if user_sessions[user_id]['timer']:
        user_sessions[user_id]['timer'].cancel()
    user_sessions[user_id]['timer'] = asyncio.create_task(send_menu(update, context, user_id))

async def send_menu(update: Update, context: CallbackContext, user_id: int):
    await asyncio.sleep(2.5)
    count = len(user_sessions[user_id]['images'])
    kb = [[InlineKeyboardButton(f"✅ Gen PDF ({count})", callback_data='gen')],
          [InlineKeyboardButton("❌ Clear", callback_data='clr')]]
    await context.bot.send_message(chat_id=user_id, text="Ready?", reply_markup=InlineKeyboardMarkup(kb))

# --- DOCS TO PDF (WITH 10MB LIMIT) ---
async def handle_docs(update: Update, context: CallbackContext):
    doc = update.message.document
    if doc.file_size > 10 * 1024 * 1024:
        await update.message.reply_text("❌ File exceeds 10MB limit!")
        return

    ext = os.path.splitext(doc.file_name.lower())[1]
    if ext in ['.docx', '.doc', '.pptx', '.ppt', '.txt']:
        msg = await update.message.reply_text("⚙️ Converting...")
        path = await (await doc.get_file()).download_to_drive(doc.file_name)
        try:
            subprocess.run(['lowriter', '--headless', '--convert-to', 'pdf', path], timeout=60)
            pdf = path.replace(ext, ".pdf")
            await update.message.reply_document(document=open(pdf, 'rb'))
            os.remove(path); os.remove(pdf)
        except Exception:
            await update.message.reply_text("❌ Conversion failed.")
        await msg.delete()

async def buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    if query.data == 'gen':
        await query.edit_message_text("🔄 Processing...")
        pdf = f"res_{uid}.pdf"
        imgs =['images']]
        imgs[0].save(pdf, save_all=True, append_images=imgs[1:])
        await context.bot.send_document(chat_id=uid, document=open(pdf, 'rb'))
        for p in user_sessions[uid]['images']: os.remove(p)
        os.remove(pdf); del user_sessions[uid]
    elif query.data == 'clr':
        del user_sessions[uid]; await query.edit_message_text("Cleared.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_images))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_docs))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()

if __name__ == '__main__':
    main()
