import asyncio
import threading
import os

from flask import Flask
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from webhook_notion import routes  # Импорт Blueprint с вебхуком
from routers import router  # Импорт роутеров бота

# Инициализация Flask
app = Flask(__name__)
app.register_blueprint(routes)  # Регистрация вебхука

# Инициализация бота
load_dotenv()
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
dp = Dispatcher()


async def run_bot():
	dp.include_router(router)
	await dp.start_polling(bot)


def start_bot():
	asyncio.run(run_bot())


if __name__ == '__main__':
	# Запускаем бот в отдельном потоке
	bot_thread = threading.Thread(target=start_bot)
	bot_thread.start()

	# Запускаем Flask-приложение
	app.run(host='0.0.0.0', port=5000)