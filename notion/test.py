import requests

def update_page_title(new_title: str):
	"""
	Обновляет заголовок страницы в Notion

	:param page_id: ID страницы (например "21185b6b-d4cc-80b0-b129-f2ebc68965ce")
	:param new_title: Новый заголовок страницы
	:return: True если успешно, False если ошибка
	"""
	if not new_title:
		print("❌ Ошибка: new_title обязательны")
		return False

	url = f"https://api.notion.com/v1/pages/{PARENT_PAGE_ID}"

	headers = {
		"Authorization": f"Bearer {NOTION_TOKEN}",
		"Notion-Version": "2022-06-28",
		"Content-Type": "application/json"
	}

	# Структура для обновления заголовка
	payload = {
		"properties": {
			"title": {  # Если это обычное свойство Title
				"title": [
					{
						"text": {
							"content": new_title
						}
					}
				]
			}
		}
	}

	try:
		response = requests.patch(url, headers=headers, json=payload)

		if response.status_code == 200:
			print(f"✅ Заголовок успешно изменен на: '{new_title}'")
			return True

		# Обработка ошибок
		print(f"❌ Ошибка {response.status_code}: {response.text}")

		if response.status_code == 401:
			print("Проверьте:")
			print("1. Верный ли NOTION_API_KEY в .env")
			print("2. Добавлена ли интеграция к странице (⋮ → Add connections)")

		return False

	except Exception as e:
		print(f"🚨 Ошибка при запросе: {str(e)}")
		return False
