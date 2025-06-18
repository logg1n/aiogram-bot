import os
import hmac
import hashlib
import json
import requests

from waitress import serve
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
    def verify_signature(request) -> bool:
        secret = os.getenv('NOTION_WEBHOOK_TOKEN')
        if not secret:
            logger.error("Notion secret not configured")
            return False

        signature_header = request.headers.get('X-Notion-Signature')
        if not signature_header:
            logger.warning("Missing X-Notion-Signature header")
            return False

        # Считаем HMAC от _сырых_ байт тела
        body_bytes = request.get_data()

        # Для отладки выведем первые 200 байт
        logger.debug(f"Raw body for HMAC: {body_bytes[:200]!r}")

        mac = hmac.new(secret.encode('utf-8'),
                       body_bytes,
                       hashlib.sha256)
        expected = "sha256=" + mac.hexdigest()

        logger.debug(f"Expected sig: {expected}")
        logger.debug(f"Received sig: {signature_header}")

        if not hmac.compare_digest(expected, signature_header):
            logger.error("Signature mismatch")
            return False

        return True

def send_telegram_notification(message: str) -> bool:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        logger.error("Telegram credentials not configured: "
                     f"TOKEN={bool(token)}, CHAT_ID={bool(chat_id)}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message[:1000] or "Empty message",
        "parse_mode": "Markdown"  # закомментируй для теста!
    }

    try:
        # Отправляем JSON, чтобы Telegram сразу принял формат
        response = requests.post(url, json=payload, timeout=5)
        # Логируем статус и тело ответа, чтобы видеть текст ошибки:
        logger.info(f"Telegram API response: {response.status_code} {response.text}")

        # Если статус != 200, response.raise_for_status() вызовет HTTPError
        response.raise_for_status()
        return True

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTPError from Telegram: {http_err}")
    except Exception as e:
        logger.exception(f"Unexpected error sending to Telegram: {e}")

    return False


def get_page_properties(page_id):
    NOTION_API_KEY = os.getenv('NOTION_TOKEN')  # Добавьте в .env
    url = f"https://api.notion.com/v1/pages/{page_id}"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("properties", {})
    except Exception as e:
        logger.error(f"Failed to get page properties: {str(e)}")
        return {}

def process_notion_event(data):
    event_type = data.get('type')  # page.content_updated, page.properties_updated и т.д.
    entity_type = data.get('entity', {}).get('type')  # page, database, block
    escape_chars = '_*[]()~`>#+-=|{}.!'
    escape_markdown = lambda text: ''.join(f'\\{char}' if char in escape_chars else char for char in text)

    logger.info(f"Processing event: {event_type} (entity: {entity_type})")

    if not event_type:
        logger.error("No event type in payload")
        return {"status": "error"}

    # Обработка событий страниц
    if event_type.startswith('page.'):
        page_id = data.get('entity', {}).get('id')
        message = f"📝 Page event: {event_type}\nPage ID: {page_id}"

        if event_type == "page.properties_updated":
            # Получаем все свойства страницы
            updated_properties = data.get('data', {}).get('updated_properties', [])
            properties = get_page_properties(page_id)


            for prop_name in updated_properties:
                prop_data = properties.get(prop_name, {})
                prop_type = prop_data.get('type')
                prop_value = ""

                if prop_type == "title":
                    # Обработка заголовка
                    prop_value = "".join([t["plain_text"] for t in prop_data.get("title", [])])

                message += f"• {prop_name}: {prop_value}\n"

        # with open('response.txt', 'a') as f:
        #     json.dump(data, f)


        send_telegram_notification(escape_markdown(message))
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

    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting server on port {port}")
    serve(app, host="0.0.0.0", port=port)