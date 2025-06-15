# Настройка для продакшена
from waitress import serve
from flask import Flask
from dotenv import load_dotenv
import os

# Инициализация Flask приложения
app = Flask(__name__)

ENV_PATH = '.env'
# Загрузка переменных окружения
load_dotenv(ENV_PATH)  # Указываем путь к .env на уровень выше

# Регистрация blueprint (перенесем ваш код)
from flask import Blueprint, request, jsonify
from dotenv import set_key, get_key
import json

routes = Blueprint("routes", __name__)


@routes.route('/notion-webhook', methods=['GET', 'POST'])
def handle_webhook():
	# Вывод информации о запросе в консоль
	print(f"\n=== Новый запрос {request.method} ===")
	print("Заголовки:", dict(request.headers))

	try:
		# GET-метод для проверки работы
		if request.method == 'GET':
			print("GET-запрос получен")
			return jsonify({
				"status": "Webhook is running",
				"env_file": str(ENV_PATH),
				"env_exists": os.path.exists(ENV_PATH),
				"current_token": get_key(str(ENV_PATH), "NOTION_WEBHOOK_TOKEN")
			}), 200

		# POST-метод (основная логика)
		if not request.is_json:
			print("Ошибка: Content-Type не application/json")
			return jsonify({"error": "Request must be JSON"}), 400

		data = request.get_json()
		print("Тело запроса:", json.dumps(data, indent=2))

		# 1. Верификационный запрос (при создании вебхука)
		if 'type' in data and data['type'] == 'webhook_verification':
			challenge = data.get('challenge')
			if challenge:
				print("Отправляем challenge в ответ")
				return jsonify({"challenge": challenge}), 200

		# 2. Обработка обычного вебхука
		saved_token = get_key(str(ENV_PATH), "NOTION_WEBHOOK_TOKEN")
		if not saved_token:
			print("Токен не найден в .env")
			return jsonify({"error": "Token not registered"}), 403

		incoming_token = request.headers.get('X-Notion-Signature', '')
		if incoming_token and incoming_token != saved_token:
			print("Неверный токен в заголовке")
			return jsonify({"error": "Invalid token"}), 403

		# 3. Обработка событий
		event_type = data.get('type')
		object_type = data.get('object')

		print(f"Событие: {event_type}, Объект: {object_type}")

		# Пример обработки разных событий
		if object_type == 'page':
			page_id = data.get('id')
			print(f"Обработка страницы: {page_id}")

			if event_type == 'page.created':
				print("Новая страница создана")
			elif event_type == 'page.updated':
				print("Страница обновлена")

		print("Вебхук успешно обработан")
		return jsonify({"status": "success"}), 200

	except Exception as e:
		print(f"Критическая ошибка: {str(e)}")
		return jsonify({"error": str(e)}), 500


# Регистрируем blueprint
app.register_blueprint(routes)

if __name__ == '__main__':
	serve(app, host="0.0.0.0", port=5000)