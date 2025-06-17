import os
import hmac
import hashlib
import json
import requests
from flask import Flask, request, jsonify, Blueprint
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Инициализация
load_dotenv('.env')
app = Flask(__name__)
routes = Blueprint("routes", __name__)


# Настройка логирования
def setup_logging():
	logger = logging.getLogger('notion_webhook')
	logger.setLevel(logging.INFO)

	handler = RotatingFileHandler(
		'notion_webhook.log',
		maxBytes=1024 * 1024,
		backupCount=3
	)
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	return logger


logger = setup_logging()


class NotionWebhookHandler:
	@staticmethod
	def verify_signature(request):
		secret = os.getenv('NOTION_WEBHOOK_TOKEN')
		if not secret:
			logger.error("Notion secret not configured")
			return False

		signature = request.headers.get('X-Notion-Signature')
		if not signature:
			logger.warning("Missing X-Notion-Signature header")
			return False

		try:
			# Получаем сырые данные как bytes
			body = request.get_data()
			logger.info(f"Raw body length: {len(body)} bytes")

			# Вычисляем подпись в точном соответствии с документацией Notion
			computed_signature = hmac.new(
				secret.encode('utf-8'),
				body,
				hashlib.sha256
			).hexdigest()

			# Формируем подпись в формате 'sha256=...'
			expected_signature = f"sha256={computed_signature}"

			# Сравниваем подписи безопасным способом
			result = hmac.compare_digest(signature, expected_signature)

			logger.info(f"Signature verification {'successful' if result else 'failed'}")
			logger.info(f"Expected: {expected_signature}")
			logger.info(f"Received: {signature}")

			return result

		except Exception as e:
			logger.error(f"Signature verification error: {str(e)}")
			return False


def send_telegram_notification(message):
	TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
	CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

	if not TELEGRAM_TOKEN or not CHAT_ID:
		logger.error("Telegram credentials not configured")
		return False

	try:
		response = requests.post(
			f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
			json={
				"chat_id": CHAT_ID,
				"text": message,
				"parse_mode": "Markdown"
			},
			timeout=5
		)
		response.raise_for_status()
		logger.info("Notification sent to Telegram")
		return True
	except Exception as e:
		logger.error(f"Failed to send Telegram notification: {str(e)}")
		return False


def process_notion_event(data):
	try:
		# Для событий обновления страницы
		if data.get('type') in ['page.updated', 'page.properties_updated']:
			page_id = data.get('entity', {}).get('id', '')
			title = "No title"

			# Попробуйте получить заголовок из разных мест
			if data.get('properties', {}).get('title'):
				title = data['properties']['title'][0]['text']['content']
			elif data.get('data', {}).get('title'):
				title = data['data']['title']

			message = f"📄 Page updated\nID: {page_id}\nTitle: {title}"
			send_telegram_notification(message)
			return {"status": "processed"}

		# Для других событий
		else:
			logger.warning(f"Unhandled event type: {data.get('type')}")
			return {"status": "skipped"}

	except Exception as e:
		logger.error(f"Error processing event: {str(e)}")
		return {"status": "error"}


@routes.route('/notion-webhook', methods=['GET', 'POST'])
def webhook_endpoint():
	try:


		logger.info(f"Incoming {request.method} request from {request.remote_addr}")
		logger.info(f"Headers: {dict(request.headers)}")
		logger.info(f"Content-Type: {request.content_type}")
		logger.info(f"Raw body (first 200 chars): {str(request.get_data())[:200]}")

		if request.method == 'GET':
			return jsonify({
				"status": "active",
				"service": "notion-webhook",
				"telegram_configured": bool(os.getenv('TELEGRAM_BOT_TOKEN'))
			}), 200

		if not request.is_json:
			logger.error("Invalid content type")
			return jsonify({"error": "Content-Type must be application/json"}), 400

		try:
			data = request.get_json()
			send_telegram_notification(data)
			# После request.get_json()
			logger.info(f"Full event type: {data.get('type')}")
			logger.info(f"Object type: {data.get('object')}")
			logger.info(f"Parsed JSON data: {data}")
		except Exception as e:
			logger.error(f"JSON parse error: {str(e)}")
			raise
		logger.debug(f"Request data: {json.dumps(data, indent=2)}")

		# Верификационный запрос
		if data.get('type') == 'webhook_verification':
			if 'challenge' in data:
				logger.info("Webhook verification successful")
				return jsonify({"challenge": data['challenge']}), 200
			return jsonify({"error": "Missing challenge"}), 400

		# Проверка подписи
		if not NotionWebhookHandler.verify_signature(request):

			return jsonify({"error": "Invalid signature"}), 403

		# Обработка события
		result = process_notion_event(data)
		return jsonify(result), 200

	except Exception as e:
		logger.exception("Unhandled exception in webhook handler")
		return jsonify({"error": "Internal server error"}), 500


app.register_blueprint(routes)

if __name__ == '__main__':
	from waitress import serve

	port = int(os.getenv('PORT', 5000))
	logger.info(f"Starting server on port {port}")
	serve(app, host="0.0.0.0", port=port)