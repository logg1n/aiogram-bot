from waitress import serve
from flask import Flask, request, jsonify, Blueprint
from dotenv import load_dotenv, set_key, get_key
import os
import hmac
import hashlib
import json

# Инициализация Flask приложения
app = Flask(__name__)

ENV_PATH = '.env'
load_dotenv(ENV_PATH)

routes = Blueprint("routes", __name__)


def verify_notion_signature(request):
	"""Проверка подписи Notion вебхука"""
	secret = os.getenv('NOTION_WEBHOOK_TOKEN')
	if not secret:
		return False

	signature = request.headers.get('Notion-Signature')
	if not signature:
		return False

	body = request.get_data()
	computed_signature = hmac.new(
		secret.encode('utf-8'),
		body,
		hashlib.sha256
	).hexdigest()

	return hmac.compare_digest(signature, computed_signature)


@routes.route('/notion-webhook', methods=['GET', 'POST'])
def handle_webhook():
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
				"current_secret": bool(get_key(str(ENV_PATH), "NOTION_WEBHOOK_TOKEN"))
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

		# 2. Проверка подписи для обычных вебхуков
		if not verify_notion_signature(request):
			print("Неверная подпись вебхука")
			return jsonify({"error": "Invalid signature"}), 403

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

		return jsonify({"status": "success"}), 200

	except Exception as e:
		print(f"Критическая ошибка: {str(e)}")
		return jsonify({"error": str(e)}), 500


app.register_blueprint(routes)

if __name__ == '__main__':
	serve(app, host="0.0.0.0", port=5000)