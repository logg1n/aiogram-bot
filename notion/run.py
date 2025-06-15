import logging
from logging import StreamHandler
from flask import Flask, request, jsonify, Blueprint
from dotenv import load_dotenv
import os
import hmac
import hashlib
import json

# Настройка логирования
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[StreamHandler()]
)
logger = logging.getLogger('notion_webhook')

app = Flask(__name__)
load_dotenv('.env')
routes = Blueprint("routes", __name__)


class SignatureVerifier:
	@staticmethod
	def verify(request):
		secret = os.getenv('NOTION_WEBHOOK_TOKEN')
		if not secret:
			logger.error("Webhook secret not configured")
			return False

		signature = request.headers.get('Notion-Signature')
		if not signature:
			logger.warning("Missing signature header")
			return False

		try:
			body = request.get_data()
			computed_signature = hmac.new(
				secret.encode('utf-8'),
				body,
				hashlib.sha256
			).hexdigest()

			if not hmac.compare_digest(signature, computed_signature):
				logger.error(f"Signature mismatch. Received: {signature}, Computed: {computed_signature}")
				return False

			return True
		except Exception as e:
			logger.error(f"Signature verification error: {str(e)}")
			return False


@routes.route('/notion-webhook', methods=['GET', 'POST'])
def handle_webhook():
	try:
		logger.info(f"Incoming {request.method} request from {request.remote_addr}")

		# GET запрос для проверки работоспособности
		if request.method == 'GET':
			return jsonify({
				"status": "active",
				"service": "notion-webhook",
				"secret_configured": bool(os.getenv('NOTION_WEBHOOK_TOKEN'))
			}), 200

		# Проверка Content-Type для POST запросов
		if not request.is_json:
			logger.error("Invalid content type")
			return jsonify({"error": "Content-Type must be application/json"}), 400

		# Обработка JSON
		try:
			data = request.get_json()
		except Exception as e:
			logger.error(f"JSON parse error: {str(e)}")
			return jsonify({"error": "Invalid JSON"}), 400

		# Верификационный запрос от Notion
		if data.get('type') == 'webhook_verification':
			if 'challenge' in data:
				logger.info("Webhook verification successful")
				return jsonify({"challenge": data['challenge']}), 200
			return jsonify({"error": "Missing challenge"}), 400

		# Проверка подписи для обычных запросов
		if not SignatureVerifier.verify(request):
			return jsonify({"error": "Invalid signature"}), 403

		# Обработка основных событий
		return handle_notion_event(data)

	except Exception as e:
		logger.exception("Unhandled exception in webhook handler")
		return jsonify({"error": "Internal server error"}), 500


def handle_notion_event(data):
	event_type = data.get('type')
	object_type = data.get('object')
	object_id = data.get('id')

	logger.info(f"Processing {event_type} for {object_type} {object_id}")

	# Добавьте здесь свою бизнес-логику
	if object_type == 'page':
		logger.info("Page event received")
	elif object_type == 'database':
		logger.info("Database event received")

	return jsonify({
		"status": "processed",
		"event": event_type,
		"object": object_type
	}), 200


app.register_blueprint(routes)

if __name__ == '__main__':
	from waitress import serve

	port = 5000
	logger.info(f"Starting server on port {port}")
	serve(app, host="0.0.0.0", port=port)