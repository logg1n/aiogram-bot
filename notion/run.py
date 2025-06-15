import logging
from logging.handlers import RotatingFileHandler
from waitress import serve
from flask import Flask, request, jsonify, Blueprint
from dotenv import load_dotenv
import os
import hmac
import hashlib
import json

# Настройка логирования
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                'notion_webhook.log',
                maxBytes=1024*1024,  # 1 MB
                backupCount=3
            ),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Инициализация Flask приложения
app = Flask(__name__)
load_dotenv('.env')
routes = Blueprint("routes", __name__)

class NotionWebhookVerifier:
    @staticmethod
    def verify_signature(request):
        """Проверка подписи Notion вебхука"""
        secret = os.getenv('NOTION_WEBHOOK_SECRET')
        if not secret:
            logger.error("Notion secret not configured")
            return False

        signature = request.headers.get('Notion-Signature')
        if not signature:
            logger.warning("Missing Notion-Signature header")
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
    logger.info(f"Received {request.method} request to /notion-webhook")

    try:
        # GET-метод для проверки работы
        if request.method == 'GET':
            logger.info("Health check request received")
            return jsonify({
                "status": "Webhook is operational",
                "environment_file": os.path.abspath('.env'),
                "secret_configured": bool(os.getenv('NOTION_WEBHOOK_SECRET'))
            }), 200

        # POST-метод (основная логика)
        if not request.is_json:
            logger.error("Invalid content type, expected JSON")
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        logger.debug(f"Request payload: {json.dumps(data, indent=2)}")

        # Верификационный запрос
        if data.get('type') == 'webhook_verification':
            challenge = data.get('challenge')
            if challenge:
                logger.info("Handling webhook verification challenge")
                return jsonify({"challenge": challenge}), 200

        # Проверка подписи
        if not NotionWebhookVerifier.verify_signature(request):
            logger.error("Signature verification failed")
            return jsonify({"error": "Invalid signature"}), 403

        # Обработка событий
        return handle_notion_event(data)

    except Exception as e:
        logger.exception("Unexpected error processing webhook")
        return jsonify({"error": "Internal server error"}), 500

def handle_notion_event(data):
    """Обработка событий от Notion"""
    event_type = data.get('type')
    object_type = data.get('object')
    event_id = data.get('id')

    logger.info(f"Processing {event_type} event for {object_type} (ID: {event_id})")

    if object_type == 'page':
        handle_page_event(event_type, data)
    elif object_type == 'database':
        handle_database_event(event_type, data)
    else:
        logger.info(f"Unhandled object type: {object_type}")

    return jsonify({"status": "processed"}), 200

def handle_page_event(event_type, data):
    """Обработка событий страницы"""
    page_id = data.get('id')
    page_title = data.get('properties', {}).get('title', {}).get('title', [{}])[0].get('plain_text', 'Untitled')

    if event_type == 'page.created':
        logger.info(f"New page created: {page_title} (ID: {page_id})")
    elif event_type == 'page.updated':
        logger.info(f"Page updated: {page_title} (ID: {page_id})")
    else:
        logger.info(f"Unhandled page event type: {event_type}")

def handle_database_event(event_type, data):
    """Обработка событий базы данных"""
    database_id = data.get('id')
    database_title = data.get('title', [{}])[0].get('plain_text', 'Untitled')

    if event_type == 'database.updated':
        logger.info(f"Database updated: {database_title} (ID: {database_id})")
    else:
        logger.info(f"Unhandled database event type: {event_type}")

app.register_blueprint(routes)

if __name__ == '__main__':
    logger.info("Starting Notion webhook server")
    try:
        serve(app, host="0.0.0.0", port=5000)
    except Exception as e:
        logger.critical(f"Server failed to start: {str(e)}")
        raise