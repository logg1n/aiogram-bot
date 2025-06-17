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
			# Определяем, что использовать для подписи
			if request.content_type == 'application/json':
				# Для обычных запросов используем сырое тело
				body = request.get_data()
			else:
				# Для верификационных запросов создаем JSON с verification_token
				body = json.dumps({"verification_token": secret})

			logger.info(f"Body for signature: {body[:100]}...")

			computed_signature = hmac.new(
				secret.encode('utf-8'),
				body.encode('utf-8') if isinstance(body, str) else body,
				hashlib.sha256
			).hexdigest()

			expected_signature = f"sha256={computed_signature}"
			result = hmac.compare_digest(signature, expected_signature)

			logger.info(f"Signature check: {'SUCCESS' if result else 'FAILED'}")
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
				"text": message[:50] if message else "Empty message",
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
	event_type = data.get('type')  # page.content_updated, page.properties_updated и т.д.
	entity_type = data.get('entity', {}).get('type')  # page, database, block

	logger.info(f"Processing event: {event_type} (entity: {entity_type})")

	if not event_type:
		logger.error("No event type in payload")
		return {"status": "error"}

	# Обработка событий страниц
	if event_type.startswith('page.'):
		page_id = data.get('entity', {}).get('id')
		message = f"📝 Page event: {event_type}\nPage ID: {page_id}"
		send_telegram_notification(message)
		return {"status": "processed"}

	# Обработка других типов событий
	else:
		logger.warning(f"Unhandled event type: {event_type}")
		return {"status": "skipped"}


@routes.route('/notion-webhook', methods=['GET', 'POST'])
def webhook_endpoint():
	try:
		logger.info(f"Token: {os.getenv('NOTION_WEBHOOK_TOKEN')[:5]}...")
		logger.info(f"Telegram token: {os.getenv('TELEGRAM_BOT_TOKEN')[:5]}...")
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
		# if not NotionWebhookHandler.verify_signature(request):
			# return jsonify({"error": "Invalid signature"}), 403

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