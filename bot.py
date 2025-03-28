import os
import logging
import tempfile
import zipfile
import requests
import telebot
from flask import Flask, request
from threading import Thread

# Инициализация Flask для Render.com
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 NHentai Bot is running", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# Конфигурация
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

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    if message.from_user.id not in WHITELIST:
        bot.reply_to(message, "🚫 Доступ запрещен!")
        return
    
    help_text = (
        "📚 NHentai Download Bot\n\n"
        "Доступные команды:\n"
        "/start - Показать это сообщение\n"
        "/download [ID] - Скачать мангу\n"
        "/add_whitelist [ID] - Добавить пользователя (только для админа)\n"
        "/get_id - Показать свой ID\n\n"
        "Пример:\n"
        "/download 177013"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['download'])
def download_manga(message):
    """Загрузка манги по ID"""
    if message.from_user.id not in WHITELIST:
        bot.reply_to(message, "🚫 Доступ запрещен!")
        return
    
    try:
        manga_id = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "❌ Укажите ID манги (например: /download 177013)")
        return

    msg = bot.reply_to(message, f"⏳ Загружаю мангу #{manga_id}...")

    try:
        # Получаем метаданные
        response = requests.get(
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
                url = f"https://nhentai.net/galleries/{media_id}/{i}.{ext}"
                
                img_data = requests.get(url, timeout=REQUEST_TIMEOUT)
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
            with open(zip_path, 'rb') as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"✅ Манга #{manga_id} успешно загружена",
                    reply_to_message_id=message.message_id
                )
            bot.delete_message(message.chat.id, msg.message_id)

    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"❌ Ошибка при загрузке: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        bot.reply_to(message, "❌ Произошла непредвиденная ошибка")

@bot.message_handler(commands=['add_whitelist'])
def add_to_whitelist(message):
    """Добавление пользователя в белый список"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🚫 Недостаточно прав!")
        return
    
    try:
        new_user = int(message.text.split()[1])
        if new_user not in WHITELIST:
            WHITELIST.append(new_user)
            bot.reply_to(message, f"✅ Пользователь {new_user} добавлен в белый список!")
        else:
            bot.reply_to(message, "ℹ️ Пользователь уже в белом списке")
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Используйте: /add_whitelist [USER_ID]")

@bot.message_handler(commands=['get_id'])
def get_user_id(message):
    """Показать ID пользователя"""
    bot.reply_to(message, f"🆔 Ваш ID: {message.from_user.id}")

if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    Thread(target=run_flask).start()
    
    logger.info("Бот успешно запущен")
    bot.infinity_polling()
