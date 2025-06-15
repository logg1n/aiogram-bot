import logging
from logging import StreamHandler
from waitress import serve
from flask import Flask, request, jsonify, Blueprint
from dotenv import load_dotenv
import os
import hmac
import hashlib
import json


# Настройка логирования для Amvera
def setup_logging():
	logger = logging.getLogger('notion_webhook')
	logger.setLevel(logging.INFO)

	# Формат логов для Amvera
	formatter = logging.Formatter(
		'%(asctime)s - %(levelname)s - %(message)s'
	)

	# Вывод в stdout (Amvera перехватывает stdout/stderr)
	handler = StreamHandler()
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	return logger


logger = setup_logging()

app = Flask(__name__)
load_dotenv('.env')
routes = Blueprint("routes", __name__)


class NotionWebhookHandler:
	@staticmethod
	def verify_signature(request):
		secret = os.getenv('NOTION_WEBHOOK_TOKEN')
		if not secret:
			logger.error("Notion secret not configured in environment")
			return False

		signature = request.headers.get('Notion-Signature')
		if not signature:
			logger.warning("Missing Notion-Signature header")
			return False

		try:
			body = request.get_data()
			computed_signature = hmac.new(
				secret.encode('utf-8'),
				body,
				hashlib.sha256
			).hexdigest()

			return hmac.compare_digest(signature, computed_signature)
		except Exception as e:
			logger.error(f"Signature verification failed: {str(e)}")
			return False


@routes.route('/notion-webhook', methods=['GET', 'POST'])
def webhook_endpoint():
	try:
		logger.info(f"Incoming {request.method} request")

		if request.method == 'GET':
			logger.info("Health check received")
			return jsonify({
				"status": "active",
				"service": "notion-webhook",
				"environment": os.getenv('FLASK_ENV', 'development')
			}), 200

		if not request.is_json:
			logger.error("Non-JSON request received")
			return jsonify({"error": "JSON content expected"}), 400

		data = request.get_json()
		logger.debug(f"Request data: {json.dumps(data)}")

		# Webhook verification
		if data.get('type') == 'webhook_verification':
			logger.info("Processing verification request")
			return jsonify({"challenge": data['challenge']}), 200

		# Verify signature
		if not NotionWebhookHandler.verify_signature(request):
			logger.error("Invalid signature detected")
			return jsonify({"error": "Invalid signature"}), 403

		# Process Notion event
		return process_notion_event(data)

	except Exception as e:
		logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
		return jsonify({"error": "Internal server error"}), 500


def process_notion_event(data):
	event_type = data.get('type')
	object_type = data.get('object')
	object_id = data.get('id')

	logger.info(f"Processing {event_type} for {object_type} {object_id}")

	# Add your custom event processing logic here
	if object_type == 'page':
		logger.info(f"Page event: {event_type}")
	elif object_type == 'database':
		logger.info(f"Database event: {event_type}")

	return jsonify({
		"status": "processed",
		"event": event_type,
		"object": object_type
	}), 200


app.register_blueprint(routes)

if __name__ == '__main__':
	logger.info("Starting Notion Webhook Server")
	try:
		port = int(os.getenv('PORT', 5000))
		logger.info(f"Server running on port {port}")
		serve(app, host="0.0.0.0", port=port)
	except Exception as e:
		logger.error(f"Server failed to start: {str(e)}")
		raise