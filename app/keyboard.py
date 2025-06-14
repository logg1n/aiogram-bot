from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

reply_keyboard_markup = ReplyKeyboardMarkup(
	keyboard=[
		[
			KeyboardButton(text='Catalog'),
			KeyboardButton(text='Contacts')
		],
		[
			KeyboardButton(text='Trash')
		]
	],
	resize_keyboard=True,
	input_field_placeholder="Please select cell menu"
)

inline_keyboard_markup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='YouTube',
                url='https://www.youtube.com/'
            )
        ]
    ]
)

cars = ['BMW', 'Renaut', 'Porche', 'Opel']

async def inline_cars():
	keyboard = InlineKeyboardBuilder()
	for car in cars:
		keyboard.add(InlineKeyboardButton(text=car, url='https://127.0.0.1'))
	return  keyboard.adjust(2).as_markup()


