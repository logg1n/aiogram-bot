import os
import hmac
import hashlib
import json
import urllib.parse
from notion_client import Client
from waitress import serve
from flask import Flask, request, jsonify, Blueprint
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Инициализация
load_dotenv()
app = Flask(__name__)
routes = Blueprint("routes", __name__)


# Настройка логирования
def setup_logging():
	logger = logging.getLogger('notion_webhook')
	logger.setLevel(logging.DEBUG)

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

# Инициализация Notion Client
notion = Client(auth=os.getenv("NOTION_TOKEN"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_TOKEN = os.getenv("NOTION_WEBHOOK_TOKEN")


class NotionWebhookHandler:
	@staticmethod
	def verify_signature(request) -> bool:
		if not WEBHOOK_TOKEN:
			logger.error("Notion WEBHOOK_TOKEN not configured")
			return False

		signature_header = request.headers.get('X-Notion-Signature')
		if not signature_header:
			logger.warning("Missing X-Notion-Signature header")
			return False

		body_bytes = request.get_data()
		mac = hmac.new(WEBHOOK_TOKEN.encode('utf-8'), body_bytes, hashlib.sha256)
		expected = "sha256=" + mac.hexdigest()

		if not hmac.compare_digest(expected, signature_header):
			logger.error("Signature mismatch")
			return False

		return True


def send_telegram_notification(message: str) -> bool:
	if not TELEGRAM_TOKEN or not CHAT_ID:
		logger.error("Telegram credentials not configured")
		return False

	url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
	payload = {
		"chat_id": CHAT_ID,
		"text": message[:1000] or "Empty message",
		"parse_mode": "Markdown"
	}

	try:
		response = requests.post(url, json=payload, timeout=20)
		response.raise_for_status()
		return True
	except Exception as e:
		logger.error(f"Failed to send Telegram notification: {str(e)}")
		return False


def get_page_properties(page_id: str):
	"""Получает свойства страницы через Notion SDK"""
	try:
		page = notion.pages.retrieve(page_id=page_id)
		return page.get("properties", {})
	except Exception as e:
		logger.error(f"Notion SDK error: {str(e)}")
		return None


def update_page_title(page_id: str, new_title: str) -> bool:
	"""Обновляет заголовок страницы через Notion SDK"""
	try:
		notion.pages.update(
			page_id=page_id,
			properties={
				"title": {
					"title": [{"text": {"content": new_title}}]
				}
			}
		)
		logger.info(f"Title updated to: {new_title}")
		return True
	except Exception as e:
		logger.error(f"Failed to update title: {str(e)}")
		return False


def process_notion_event(data):
	event_type = data.get('type')
	entity = data.get('entity', {})
	entity_type = entity.get('type')

	logger.info(f"Processing event: {event_type} (entity: {entity_type})")

	if event_type == "page.properties_updated":
		page_id = entity.get('id')
		updated_properties = data.get('data', {}).get('updated_properties', [])

		properties = get_page_properties(page_id)
		if not properties:
			return {"status": "error"}

		message = "📝 *Page Updated*\n"
		for prop_id in updated_properties:
			prop_name = next((name for name, prop in properties.items()
							  if prop.get('id') == prop_id), prop_id)
			message += f"- {prop_name}\n"

		send_telegram_notification(message)

		# Пример обновления заголовка
		if "title" in updated_properties:
			update_page_title(page_id, "New Updated Title")

		return {"status": "processed"}

	return {"status": "skipped"}


@routes.route('/notion-webhook', methods=['GET', 'POST'])
def webhook_endpoint():
	try:
		if request.method == 'GET':
			return jsonify({"status": "active"}), 200

		if not request.is_json:
			return jsonify({"error": "Content-Type must be application/json"}), 400

		data = request.get_json()

		if data.get('type') == 'webhook_verification':
			return jsonify({"challenge": data['challenge']}), 200

		# if not NotionWebhookHandler.verify_signature(request):
		# 	return jsonify({"error": "Invalid signature"}), 403

		result = process_notion_event(data)
		return jsonify(result), 200

	except Exception as e:
		logger.exception("Webhook error")
		return jsonify({"error": str(e)}), 500


app.register_blueprint(routes)

if __name__ == '__main__':
	port = int(os.getenv('PORT', 5000))
	logger.info(f"Starting server on port {port}")
	serve(app, host="0.0.0.0", port=port)