import os
import asyncio
import aiohttp

from dotenv import load_dotenv
from notion_client import Client, AsyncClient

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version  # для старых Python

sdk_version = version("notion-client")
load_dotenv()

token = "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"
page_id = "21185b6b-d4cc-80b0-b129-f2ebc68965ce"


def validate_token_and_access(token, page_id):
    tips = []

    if not token:
        return "❌ Токен не задан", ["Проверь переменную окружения NOTION_TOKEN."]

    if not page_id:
        return "❌ ID страницы не задан", ["Проверь переменную PARENT_PAGE_ID."]

    if not (token.startswith("ntn_") or token.startswith("secret_")):
        tips.append("⚠️ Токен имеет нестандартный префикс — возможна ошибка копирования.")

    if len(token.strip()) < 40:
        tips.append("⚠️ Длина токена подозрительно короткая. Убедись, что он скопирован полностью.")

    if "-" not in page_id:
        tips.append("⚠️ ID страницы должен быть в формате UUID с тире (например, 2118-...)")

    tips.append("🧪 Убедись, что страница открыта для интеграции в Notion.")
    tips.append("→ Открой страницу в Notion → 'Share' → 'Connect with integrations' → выбери свою интеграцию.")

    return "🔎 Проверка токена и ID завершена", tips


def check_token_format(token):
    if token.startswith("ntn_"):
        return "✅ Новый формат (ntn_)"
    elif token.startswith("secret_"):
        return "☑️ Старый формат (secret_)"
    else:
        return "⚠️ Неизвестный формат"


async def check_async_access(token, page_id):
    notion = AsyncClient(auth=token)
    try:
        page = await notion.pages.retrieve(page_id=page_id)
        return "✅ Async доступ: OK", page.get("url")
    except Exception as e:
        return f"❌ Async ошибка доступа: {e}", None


def check_sync_access(token, page_id):
    notion = Client(auth=token)
    try:
        page = notion.pages.retrieve(page_id=page_id)
        return "✅ Sync доступ: OK", page.get("url")
    except Exception as e:
        return f"❌ Sync ошибка доступа: {e}", None


async def validate_via_http(token, page_id):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    results = {}

    async with aiohttp.ClientSession(headers=headers) as session:
        # Проверка токена через /users/me
        try:
            async with session.get("https://api.notion.com/v1/users/me") as resp:
                if resp.status == 200:
                    results["/users/me"] = "✅ Токен валиден"
                elif resp.status == 401:
                    results["/users/me"] = "❌ Токен не авторизован (401)"
                else:
                    results["/users/me"] = f"⚠️ Статус токена: {resp.status}"
        except Exception as e:
            results["/users/me"] = f"🚫 Ошибка запроса /users/me: {e}"

        # Проверка доступа к странице
        try:
            url = f"https://api.notion.com/v1/pages/{page_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    results["/pages"] = "✅ Доступ к странице есть"
                elif resp.status == 404:
                    results["/pages"] = "❌ Страница не найдена или недоступна"
                elif resp.status == 403:
                    results["/pages"] = "🚫 Доступ запрещён (403)"
                elif resp.status == 401:
                    results["/pages"] = "❌ Невалидный токен (401)"
                else:
                    results["/pages"] = f"⚠️ Статус страницы: {resp.status}"
        except Exception as e:
            results["/pages"] = f"🚨 Ошибка запроса к странице: {e}"

    return results


async def main():
    print("🔍 Notion Диагностика...\n")

    if not token or not page_id:
        print("🚫 Не найдены переменные окружения: NOTION_TOKEN и/или PARENT_PAGE_ID")
        return

    print(f"🔢 Версия SDK: {sdk_version}")
    print(f"🔐 Токен: {token[:10]}... ({len(token)} символов)")
    print(f"🧬 Формат токена: {check_token_format(token)}")
    print(f"📄 Page ID: {page_id}")

    print("\n📡 Проверка синхронного доступа...")
    sync_status, sync_url = check_sync_access(token, page_id)
    print(sync_status)
    if sync_url:
        print(f"🔗 URL страницы: {sync_url}")

    print("\n⚙️ Проверка асинхронного доступа...")
    async_status, async_url = await check_async_access(token, page_id)
    print(async_status)
    if async_url:
        print(f"🔗 URL страницы: {async_url}")

    print("\n🌐 Проверка HTTP-доступа (по REST):")
    results = await validate_via_http(token, page_id)
    for key, status in results.items():
        print(f"{key}: {status}")


if __name__ == "__main__":
    print("\n📋 Предварительная диагностика токена и страницы:")
    status, suggestions = validate_token_and_access(token, page_id)
    print(status)
    for line in suggestions:
        print(f"   {line}")

    asyncio.run(main())
