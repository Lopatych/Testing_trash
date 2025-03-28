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

# Инициализация Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 NHentai Bot is running", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# Конфигурация из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
WHITELIST = list(map(int, os.environ.get('WHITELIST_IDS', '').split(','))) if os.environ.get('WHITELIST_IDS') else []
REQUEST_TIMEOUT = 30

# Проверка конфигурации
if not all([BOT_TOKEN, ADMIN_ID, WHITELIST]):
    logging.error("Missing required environment variables!")
    exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    if user_id not in WHITELIST:
        await update.message.reply_text("🚫 Доступ запрещен!")
        return
    
    help_text = (
        "📚 NHentai Download Bot\n\n"
        "Доступные команды:\n"
        "/start - Показать это сообщение\n"
        "/download [ID] - Скачать мангу\n"
        "/add_whitelist [ID] - Добавить пользователя (только для админа)\n\n"
        "Пример:\n"
        "/download 177013"
    )
    await update.message.reply_text(help_text)

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Загрузка манги по ID"""
    user_id = update.effective_user.id
    if user_id not in WHITELIST:
        await update.message.reply_text("🚫 Доступ запрещен!")
        return
    
    try:
        manga_id = context.args[0]
    except IndexError:
        await update.message.reply_text("❌ Укажите ID манги (например: /download 177013)")
        return

    await update.message.reply_text(f"⏳ Загружаю мангу #{manga_id}...")

    try:
        # Получаем метаданные
        response = await asyncio.to_thread(
            requests.get,
            f"https://nhentai.net/api/gallery/{manga_id}",
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        # Создаем временную папку
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_paths = []
            media_id = data['media_id']
            
            # Скачиваем страницы
            for i, page in enumerate(data['images']['pages'], 1):
                ext = {'j': 'jpg', 'p': 'png', 'g': 'gif'}.get(page['t'], 'jpg')
                url = f"https://i.nhentai.net/galleries/{media_id}/{i}.{ext}"
                
                img_data = await asyncio.to_thread(
                    requests.get, url, timeout=REQUEST_TIMEOUT
                )
                img_data.raise_for_status()
                
                img_path = os.path.join(tmp_dir, f"{i}.{ext}")
                with open(img_path, 'wb') as f:
                    f.write(img_data.content)
                img_paths.append(img_path)
            
            # Создаем ZIP-архив
            zip_path = os.path.join(tmp_dir, f"{manga_id}.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for img in img_paths:
                    zipf.write(img, os.path.basename(img))
            
            # Отправляем файл
            await update.message.reply_document(
                document=open(zip_path, 'rb'),
                filename=f"{manga_id}.zip",
                caption=f"✅ Манга #{manga_id} успешно загружена"
            )

    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"❌ Ошибка при загрузке: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await update.message.reply_text("❌ Произошла непредвиденная ошибка")

async def add_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление пользователя в белый список"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Недостаточно прав!")
        return
    
    try:
        new_user = int(context.args[0])
        if new_user not in WHITELIST:
            WHITELIST.append(new_user)
            await update.message.reply_text(f"✅ Пользователь {new_user} добавлен в белый список!")
        else:
            await update.message.reply_text("ℹ️ Пользователь уже в белом списке")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Используйте: /add_whitelist [USER_ID]")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать ID пользователя"""
    await update.message.reply_text(f"🆔 Ваш ID: {update.effective_user.id}")

def main():
    # Запускаем Flask в отдельном потоке
    Thread(target=run_flask).start()
    
    # Инициализируем бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("add_whitelist", add_whitelist))
    application.add_handler(CommandHandler("get_id", get_id))
    
    logger.info("Бот успешно запущен")
    application.run_polling()

if __name__ == "__main__":
    main()
