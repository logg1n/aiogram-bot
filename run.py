from flask import Flask
from app.webhook_notion import routes  # Импортируем Blueprint
import asyncio
import os
import threading

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from app.routers import router

# Загрузка переменных
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

app = Flask(__name__)
app.register_blueprint(routes)  # Регистрируем маршруты

async def telegram_bot():
    dp.include_router(router)
    await dp.start_polling(bot)

def run_flask():
    app.run()

if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Запускаем Telegram-бота в asyncio
    asyncio.run(telegram_bot())
