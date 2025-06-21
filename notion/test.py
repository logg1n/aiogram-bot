from notion_client import Client
import os
from pprint import pprint
from typing import Optional

# Инициализация Notion клиента

# Пример использования
if __name__ == "__main__":
	notion = Client(auth="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")  # Токен с префиксом secret_ или ntn_
	# Получаем ID страницы из переменных окружения или вводим вручную
	pprint(notion.pages.retrieve(page_id='21185b6bd4cc80b0b129f2ebc68965ce'))
