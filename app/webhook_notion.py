from flask import Flask, request, jsonify
from dotenv import load_dotenv, set_key, get_key
import os
import json

app = Flask(__name__)

# Загружаем переменные окружения
load_dotenv()
TOKEN_FILE = '.env'  # Файл для хранения токена


@app.route('/notion-webhook', methods=['POST'])
def handle_webhook():
	try:
		data = request.json

		# 1. Проверка верификационного запроса
		if 'verification_token' in data:
			verification_token = data['verification_token']

			# Сохраняем токен в .env
			set_key(TOKEN_FILE, "NOTION_WEBHOOK_TOKEN", verification_token)
			print(f"🔑 Получен verification_token: {verification_token}")

			# Ответ на challenge
			if 'challenge' in data:
				return jsonify({"challenge": data['challenge']}), 200
			return jsonify({"status": "Token saved"}), 200

		# 2. Обработка обычного вебхука
		saved_token = get_key(TOKEN_FILE, "NOTION_WEBHOOK_TOKEN")

		if not saved_token:
			return jsonify({"error": "Token not registered"}), 403

		# Проверка токена (пример)
		incoming_token = request.headers.get('X-Notion-Signature', '')
		if incoming_token and incoming_token != saved_token:
			return jsonify({"error": "Invalid token"}), 403

		print("📢 Получен вебхук:", json.dumps(data, indent=2))
		return jsonify({"status": "success"}), 200

	except Exception as e:
		print(f"❌ Ошибка: {str(e)}")
		return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
	if not os.path.exists(TOKEN_FILE):
		print("⚠️ Файл .env не найден. Ожидаю верификационный запрос...")
	app.run(host='0.0.0.0', port=5000)