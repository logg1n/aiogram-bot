import asyncio
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from routers import router

# Загрузка переменных
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

async def main():
	dp.include_router(router)
	await dp.start_polling(bot)

if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		print('Exit')