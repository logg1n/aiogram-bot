import requests
import time
import os
import logging

logger = logging.getLogger('notion_webhook')

def send_telegram_notification(message: str, retries=3, timeout=5, delay=2) -> bool:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        logger.error("❌ Не настроены переменные TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message[:1000],
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"📡 Отправка уведомления в Telegram (попытка {attempt})")
            response = requests.post(url, data=payload, timeout=timeout)
            logger.debug(f"Telegram response: {response.status_code} | {response.text}")
            response.raise_for_status()
            logger.info("✅ Уведомление успешно отправлено")
            return True
        except requests.exceptions.ReadTimeout:
            logger.warning(f"⏱️ Таймаут Telegram (попытка {attempt})")
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"⚠️ HTTP ошибка от Telegram: {http_err}")
            logger.error(f"Ответ: {response.text}")
            # не повторяем при 400 или 403
            break
        except Exception as e:
            logger.exception(f"🚨 Неожиданная ошибка при отправке: {e}")
            break
        time.sleep(delay)

    logger.error("❌ Уведомление в Telegram не отправлено после повторов")
    return False


import requests
import time
import os
import logging

logger = logging.getLogger('notion_webhook')

вместо properties = get_page_properties(page_id)
		properties = safe_get_page_properties(page_id)



def safe_get_page_properties(page_id, retries=3, timeout=10, delay=2):
    """Безопасный запрос к Notion API с повторами и логированием"""
    token = os.getenv("NOTION_TOKEN")
    if not token:
        logger.error("❌ NOTION_TOKEN не найден в окружении.")
        return None

    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"🌐 Попытка {attempt}: запрос к {url}")
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            logger.info("✅ Свойства страницы получены")
            return response.json().get("properties", {})
        except requests.exceptions.ReadTimeout:
            logger.warning(f"⏱️ Таймаут при обращении к Notion (попытка {attempt})")
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"🔴 HTTP ошибка: {response.status_code} – {response.text}")
            break  # не повторяем в случае 401/404
        except Exception as e:
            logger.exception(f"⚠️ Неожиданная ошибка запроса: {e}")
            break
        time.sleep(delay)

    logger.error("❌ Не удалось получить данные после нескольких попыток.")
    return None
