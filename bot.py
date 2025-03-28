import os
import logging
import tempfile
import zipfile
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Active | Use /start in Telegram", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
WHITELIST_IDS = os.environ.get('WHITELIST_IDS', '')
WHITELIST = list(map(int, WHITELIST_IDS.split(','))) if WHITELIST_IDS else []
REQUEST_TIMEOUT = 30

# Validate environment variables
if not all([BOT_TOKEN, ADMIN_ID, WHITELIST]):
    logging.error("❌ Missing required environment variables!")
    exit(1)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in WHITELIST:
        await update.message.reply_text("🚫 Access Denied!")
        return
    await update.message.reply_text(
        "📚 NHentai Download Bot\n"
        "Usage: /download [manga_id]\n"
        "Example: /download 177013"
    )

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... [остальная часть кода из предыдущего ответа] ...

async def add_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... [код для добавления в белый список] ...

def main():
    Thread(target=run_flask).start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("add_whitelist", add_whitelist))
    
    logger.info("✅ Bot started successfully")
    application.run_polling()

if __name__ == "__main__":
    main()
