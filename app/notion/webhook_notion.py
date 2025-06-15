from flask import Flask
from dotenv import load_dotenv
import os

# Инициализация Flask приложения
app = Flask(__name__)

# Загрузка переменных окружения
load_dotenv('../.env')  # Указываем путь к .env на уровень выше

# Регистрация blueprint (перенесем ваш код)
from flask import Blueprint, request, jsonify
from dotenv import set_key, get_key
import json

routes = Blueprint("routes", __name__)


@routes.route('/notion-webhook', methods=['POST'])
def handle_webhook():
	try:
		# Проверка Content-Type
		if not request.is_json:
			return jsonify({"error": "Request must be JSON"}), 400

		data = request.get_json()

		# 1. Верификационный запрос
		if 'verification_token' in data:
			verification_token = data['verification_token']
			set_key('../.env', "NOTION_WEBHOOK_TOKEN", verification_token)

			if 'challenge' in data:
				return jsonify({"challenge": data['challenge']}), 200
			return jsonify({"status": "Token saved"}), 200

		# 2. Обработка обычного вебхука
		saved_token = get_key('../.env', "NOTION_WEBHOOK_TOKEN")
		if not saved_token:
			return jsonify({"error": "Token not registered"}), 403

		# Проверка подписи Notion
		incoming_token = request.headers.get('X-Notion-Signature', '')
		if incoming_token and incoming_token != saved_token:
			return jsonify({"error": "Invalid token"}), 403

		# Логирование полученных данных
		app.logger.info("📢 Получен вебхук: %s", json.dumps(data, indent=2))
		return jsonify({"status": "success"}), 200

	except Exception as e:
		app.logger.error("❌ Ошибка: %s", str(e))
		return jsonify({"error": str(e)}), 500


# Регистрируем blueprint
app.register_blueprint(routes)

if __name__ == '__main__':
	# Настройка для продакшена
	from waitress import serve

	serve(app, host="0.0.0.0", port=5000)