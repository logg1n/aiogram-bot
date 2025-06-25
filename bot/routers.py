from notion_client import AsyncClient
import os
from notion_client import Client
from dotenv import load_dotenv

import asyncio
import aiohttp
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from trade import get_info_ticker
from keyboard import reply_keyboard_markup as rkm
from keyboard import inline_keyboard_markup as ikm
from keyboard import inline_cars

load_dotenv()
router: Router = Router()


async def fetch_ticker():
    # если get_info_ticker синхронная — обернём её
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: get_info_ticker('BTCUSDT'))


async def fetch_webhook_status():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://loggiin.pythonanywhere.com/notion-webhook') as resp:
                return resp.status
    except Exception as e:
        return f"Error: {e}"



async def fetch_notion_status(page_id, token):
    try:
        notion = AsyncClient(auth=token)
        page = await notion.pages.retrieve(page_id=page_id)
        return "Connected" if page else "Failed"
    except Exception as e:
        return f"Error: {e}"


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    chat_id = message.chat.id

    # Параллельный запуск задач
    ticker_task = fetch_ticker()
    notion_task = fetch_notion_status(os.getenv("PARENT_PAGE_ID"), os.getenv("NOTION_TOKEN"))
    webhook_task = fetch_webhook_status()

    tiker, notion_status, webhook_status = await asyncio.gather(
        ticker_task, notion_task, webhook_task
    )

    response = (
        f"Привет, {user_name}!\n"
        f"Твой ID: `{user_id}`\n"
        f"Чат ID: `{chat_id}`\n"
        f"Notion: *{notion_status}*\n"
        f"Webhook: *{webhook_status}*\n"
        f"Цена {tiker.get('symbol')}: `{tiker.get('lastPrice')}`"
    )

    await message.answer(response, parse_mode="Markdown")

@router.message(F.text.startswith("/myinfo"))
async def myinfo(message: Message):
    telegram_id = str(message.from_user.id)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://127.0.0.1:8000/api/user-info/?telegram_id={telegram_id}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = (
                        f"👤 Имя: {data.get('username')}\n"
                        f"📧 Email: {data.get('email')}\n"
                        f"📱 Телефон: {data.get('phone_number') or 'не указан'}"
                    )
                    await message.answer(response)
                elif resp.status == 404:
                    await message.answer("❌ Ты ещё не зарегистрирован. Введи команду /register email@example.com для регистрации.")
                else:
                    error_data = await resp.json()
                    await message.answer(f"⚠️ Ошибка: {error_data.get('error', 'Неизвестная ошибка')}")
    except Exception as e:
        await message.answer(f"🚨 Ошибка при соединении с API: {e}")


@router.message(F.text.startswith("/register"))
async def register_user(message: Message):
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("⚠️ Используй: /register твой_email@example.com")
        return

    email = parts[1]
    telegram_id = str(message.from_user.id)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:8000/api/register-telegram/",
                json={"email": email, "telegram_id": telegram_id}
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    await message.answer("✅ Telegram ID успешно привязан!")
                else:
                    await message.answer(f"❌ Ошибка: {data.get('error', 'Неизвестная ошибка')}")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при соединении с API: {e}")


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer('Command Help')


@router.message(Command('price'))
async def cmd_price(message: Message):
    ticker = message.text.split()[1].upper()
    info = get_info_ticker(ticker)
    if info:
        price = float(info.get("lastPrice", "Информация о цене недоступна"))
        await message.reply(f"Текущая цена {ticker}: {price}")
    else:
        await message.reply("Не удалось получить информацию о цене.")


@router.message(Command('get_photo'))
async def get_photo(message: Message):
    await message.answer_photo(photo='', caption='')


@router.message(F.text == 'Как дела?')
async def get_how_are_you(message: Message):
    await message.answer('OK')


@router.message(F.photo)
async def get_photo(message: Message):
    await message.answer(f'ID Фото: {message.photo[-1].file_id}')
