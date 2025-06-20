import os
import hmac
import hashlib
import json
import requests
from requests import Response

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

WEBHOOK_TOKEN = os.getenv('NOTION_WEBHOOK_TOKEN')
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

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
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("Telegram credentials not configured: "
                     f"TOKEN={bool(TELEGRAM_TOKEN)}, CHAT_ID={bool(CHAT_ID)}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message[:1000] or "Empty message",
        # "parse_mode": "Markdown"  # закомментируй для теста!
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
    """Получает свойства страницы Notion с расширенной диагностикой ошибок"""
    # Проверяем формат ID страницы
    if not page_id:
        logger.error(f"⚠️ Неверный формат ID страницы: {page_id}")
        return None

    logger.info(f"Webhook стартует... TOKEN = {repr(os.getenv('NOTION_TOKEN'))}")

    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    try:
        logger.info(f"🔍 Запрос свойств страницы: {page_id}")
        response = requests.get(url, headers=headers, timeout=5)

        # test_response = requests.get(
        #     url="https://api.notion.com/v1/pages/21185b6bd4cc80b0b129f2ebc68965ce",
        #     headers={
        #         "Authorization": "Bearer secret_epg5fxwiHdLmh58HR3K70KEbjcRssWYqnOIzrIkQyiM",
        #         "Notion-Version": "2022-06-28",
        #         "Content-Type": "application/json",
        #     }
        # )
        # logger.info(f"------------------------------------------"
        #             f"Test Request: {test_response.status_code}"
        #             f"------------------------------------------")

        logger.debug(f"Final headers: {test_response.request.headers}")

        # Анализ ответа API
        if response.status_code == 401:
            logger.error("❌ Ошибка 401: Неавторизованный доступ. Проверьте NOTION_TOKEN")
            return None
        elif response.status_code == 404:
            logger.error(f"❌ Ошибка 404: Страница не найдена. Убедитесь, что бот имеет доступ к странице {page_id}")
            return None
        elif response.status_code == 429:
            logger.error("❌ Ошибка 429: Слишком много запросов. Попробуйте позже")
            return None

        response.raise_for_status()

        # Проверка наличия свойств
        data = response.json()
        properties = data.get("properties")
        if not properties:
            logger.warning("⚠️ Страница не содержит свойств (пустой объект properties)")

        return properties

    except requests.exceptions.RequestException as e:
        logger.error(f"🚨 Ошибка при запросе к Notion API: {e}")
        return None


def debug_page_access(page_id):
    """Проверяет доступ к странице и возвращает информацию для диагностики"""
    if not NOTION_TOKEN:
        return "❌ NOTION_TOKEN не настроен"

    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        return f"Статус: {response.status_code}\nОтвет: {response.text[:200]}"
    except Exception as e:
        return f"Ошибка: {str(e)}"


def get_property_value(prop_data):
    """Извлекает значение свойства в читаемом формате"""
    if not prop_data:
        return ""

    prop_type = prop_data.get('type')
    if not prop_type:
        return "[unknown type]"

    try:
        # Обработка разных типов свойств
        if prop_type == "title":
            return "".join(t["plain_text"] for t in prop_data.get("title", []))

        elif prop_type == "rich_text":
            return "".join(t["plain_text"] for t in prop_data.get("rich_text", []))

        elif prop_type == "number":
            return str(prop_data.get("number", ""))

        elif prop_type == "select":
            select = prop_data.get("select")
            return select["name"] if select else ""

        elif prop_type == "multi_select":
            options = prop_data.get("multi_select", [])
            return ", ".join(opt["name"] for opt in options)

        elif prop_type == "checkbox":
            return "☑" if prop_data.get("checkbox") else "☐"

        elif prop_type == "date":
            date_obj = prop_data.get("date")
            if not date_obj:
                return ""
            start = date_obj.get("start", "")
            end = date_obj.get("end", "")
            return f"{start} → {end}" if end else start

        elif prop_type == "url":
            return prop_data.get("url", "")

        elif prop_type == "email":
            return prop_data.get("email", "")

        elif prop_type == "phone_number":
            return prop_data.get("phone_number", "")

        elif prop_type == "people":
            people = prop_data.get("people", [])
            return ", ".join(p.get("name", "unknown") for p in people)

        elif prop_type == "files":
            files = prop_data.get("files", [])
            return ", ".join(f.get("name", "unnamed") for f in files)

        else:
            return f"[{prop_type}]"

    except Exception as e:
        logger.error(f"Ошибка обработки свойства {prop_type}: {e}")
        return "[error]"


def escape_markdown(text):
    """Экранирует спецсимволы Markdown для Telegram"""
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))


def process_notion_event(data):
    """Обрабатывает событие от Notion"""
    event_type = data.get('type')
    entity = data.get('entity', {})
    entity_type = entity.get('type')

    logger.info(f"Обработка события: {event_type} (сущность: {entity_type})")

    if not event_type:
        logger.error("Тип события не указан")
        return {"status": "error"}

    # Обработка событий страниц
    if event_type.startswith('page.'):
        page_id = entity.get('id')
        if not page_id:
            logger.error("ID страницы отсутствует")
            return {"status": "error"}

        # Базовое сообщение
        page_url = f"https://www.notion.so/{page_id}"
        message = (
            f"📝 *Обновление страницы*\n"
            f"Тип события: `{event_type}`\n"
            f"Страница: [открыть]({page_url})\n"
        )

        # Обработка обновления свойств
        if event_type == "page.properties_updated":
            updated_properties = data.get('data', {}).get('updated_properties', [])
            properties = get_page_properties(page_id)

            # Формируем базовое сообщение
            page_url = f"https://www.notion.so/{page_id}"
            message = (
                f"📝 *Обновление страницы*\n"
                f"Тип события: `{event_type}`\n"
                f"Страница: [открыть]({page_url})\n"
            )

            # Если не удалось получить свойства
            if properties is None:
                debug_info = debug_page_access(page_id)
                message += (
                    "\n⚠️ *Не удалось получить свойства страницы*\n"
                    f"Проверьте:\n"
                    f"1. Добавлен ли бот на страницу\n"
                    f"2. Корректность NOTION_TOKEN\n"
                    f"3. Доступность страницы\n\n"
                    f"Диагностика:\n```\n{debug_info}\n```"
                )
            else:
                message += "\n*Измененные свойства:*\n"
                found_updates = False

                for encoded_prop_id in updated_properties:
                    try:
                        # Декодируем ID свойства
                        prop_id = urllib.parse.unquote(encoded_prop_id)
                    except Exception as e:
                        logger.error(f"Ошибка декодирования {encoded_prop_id}: {e}")
                        continue

                    # Ищем свойство по ID
                    prop_data = None
                    prop_name = "unknown"

                    for name, data in properties.items():
                        if data.get('id') == prop_id:
                            prop_data = data
                            prop_name = name
                            break

                    if not prop_data:
                        message += f"• `{prop_id}`: свойство не найдено\n"
                        continue

                    # Получаем значение свойства
                    prop_value = get_property_value(prop_data)
                    message += (
                        f"• *{escape_markdown(prop_name)}*: "
                        f"{escape_markdown(prop_value)}\n"
                    )
                    found_updates = True

                if not found_updates:
                    message += "Нет доступных данных об изменениях"

        # Отправка уведомления в Telegram
        send_telegram_notification(message)
        return {"status": "processed"}

    # Обработка других событий
    else:
        logger.warning(f"Неподдерживаемый тип события: {event_type}")
        return {"status": "skipped"}


@routes.route('/notion-webhook', methods=['GET', 'POST'])
def webhook_endpoint():
    try:
        # logger.info(f"Token: {os.getenv('NOTION_WEBHOOK_TOKEN')[:5]}...")
        # logger.info(f"Telegram token: {os.getenv('TELEGRAM_BOT_TOKEN')[:5]}...")
        # logger.info(f"Incoming {request.method} request from {request.remote_addr}")
        # logger.info(f"Headers: {dict(request.headers)}")
        # logger.info(f"Content-Type: {request.content_type}")
        # logger.info(f"Raw body (first 200 chars): {str(request.get_data())[:200]}")

        if request.method == 'GET':
            return jsonify({
                "status": "active",
                "service": "notion-webhook",
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