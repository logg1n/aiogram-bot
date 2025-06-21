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
            async with session.get('https://test-loggiin.amvera.io/notion-webhook') as resp:
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


@router.message(Command('chatid'))
async def send_chat_id(message: Message):
    chat_id = message.chat.id
    response_text = f"🆔 Ваш chat_id: `{chat_id}`"

    # Для групп/каналов добавляем дополнительную информацию
    if message.chat.type != 'private':
        response_text += (
            f"\n\nℹ️ Дополнительно:\n"
            f"Тип чата: `{message.chat.type}`\n"
            f"Название: `{message.chat.title}`"
        )

    await message.reply(response_text, parse_mode='Markdown')


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
