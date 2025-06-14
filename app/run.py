from flask import Flask
from routes import routes  # Импортируем Blueprint
import asyncio
import os

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

async def main():
	dp.include_router(router)
	await dp.start_polling(bot)

if __name__ == '__main__':
	try:
		app.run()
		asyncio.run(main())
	except KeyboardInterrupt:
		print('Exit')