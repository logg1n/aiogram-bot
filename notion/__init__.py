import os

from pprint import pprint
from typing import Any, Dict, List
from datetime import datetime

from notion_client import Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

notion_token = os.getenv('NOTION_TOKEN')
client = Client(auth=notion_token)


class Utils:
	@staticmethod
	def extract_property_value(prop: dict):
		match prop.get("type"):
			case "title":
				return "".join(t.get("plain_text", "") for t in prop["title"])
			case "rich_text":
				return "".join(t.get("plain_text", "") for t in prop["rich_text"])
			case "number":
				return prop.get("number")
			case "select":
				return prop.get("select", {}).get("name")
			case "multi_select":
				return [opt.get("name") for opt in prop.get("multi_select", [])]
			case "date":
				return prop.get("date", {}).get("start")
			case "checkbox":
				return prop.get("checkbox")
			case "url":
				return prop.get("url")
			case "email":
				return prop.get("email")
			case "phone_number":
				return prop.get("phone_number")
			case "people":
				return [p.get("name", "") for p in prop.get("people", [])]
			case _:
				return f"[{prop.get("type")}]"


	def format_notion_telegram_message(results: List[dict], with_links: bool = True) -> str:
		if not results:
			return "⚠️ Обновление получено, но данные страницы не были извлечены."

		messages = []

		for entry in results:
			lines = []

			ticker = entry.get("Тикер", "Без тикера")
			deal_type = entry.get("Тип сделки", "Сделка")
			status = entry.get("Статус", "")
			page_id = entry.get("id")

			# 🟢 Статус → эмодзи
			status_emoji = {
				"Активна": "🟢",
				"Закрыта": "🔴",
				"Отменена": "⚪",
			}.get(status, "⚙️")

			# 📈 Тип сделки → эмодзи
			deal_emoji = {
				"Long": "📈",
				"Short": "📉",
			}.get(deal_type, "💼")

			header = f"{status_emoji} <b>{ticker}</b> — {deal_emoji} <i>{deal_type}</i> <code>{status}</code>"

			# Добавляем ссылку на страницу
			if with_links and page_id:
				clean_id = page_id.replace("-", "")
				url = f"https://www.notion.so/{clean_id}"
				header += f"\n🔗 <a href='{url}'>Открыть в Notion</a>"

			lines.append(header)
			lines.append("")

			for field, value in entry.items():
				if field in ("Тикер", "Статус", "Тип сделки", "id"):
					continue

				if isinstance(value, str) and field == "Дата сделки":
					try:
						value = datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d.%m.%Y")
					except Exception:
						pass

				if value in (None, "", [], {}):
					value = "—"

				# Добавляем эмодзи к ключевым полям
				field_emoji = {
					"Дата сделки": "🗓",
					"Цена входа": "💰",
					"Цена выхода": "🏁",
					"Объем": "📦",
					"Комиссии": "💸",
					"Комментарий": "📝",
				}.get(field, "•")

				lines.append(f"{field_emoji} <b>{field}:</b> {value}")

			messages.append("\n".join(lines))

		return "\n\n".join(messages)
