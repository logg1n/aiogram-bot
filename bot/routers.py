from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from trade import get_info_ticker
from keyboard import reply_keyboard_markup as rkm
from keyboard import inline_keyboard_markup as ikm
from keyboard import inline_cars

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
	await message.reply(
		f'Привет.\n Твой ID: {message.from_user.id}\nИмя: {message.from_user.first_name}\nЧат ID: {message.chat.id}',
		reply_markup=await inline_cars(),

	)


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