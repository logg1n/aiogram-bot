import os

from pprint import  pprint
from typing import Any

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


if __name__ == "__main__":
	database_id = "21185b6b-d4cc-816a-8ff6-d542fdaf02aa"

	# client.blocks.children.list(os.getenv('PARENT_PAGE_ID'))
	# client.blocks.retrieve("21185b6b-d4cc-816a-8ff6-d542fdaf02a")
	# val = client.blocks.retrieve('21185b6bd4cc81e48c76c4b2b20a7a1b')
	# pages = client.databases.query(database_id=database_id).get("results", [])
	'21185b6bd4cc81e48c76c4b2b20a7a1b'
	# if val.get('parent')['type'] == 'database_id':
	page = client.pages.retrieve('21185b6b-d4cc-81e4-8c76-c4b2b20a7a1b')
	pprint(page)



	new_page = {
		"parent": {"database_id": database_id},
		"properties": {
			"Тикер": {
				"title": [
					{
						"text": {
							"content": "ZPL"
						}
					}
				]
			},
			"Дата сделки": {
				"date": {
					"start": datetime.now().date().isoformat()
				}
			},
			"Статус": {
				"select": {
					"name": "Активна"
				}
			},
			"Тип сделки": {
				"select": {
					"name": "Long"
				}
			},
			"Объем": {
				"number": 15
			},
			"Комиссии": {
				"number": 2.5
			},
			"Цена входа": {
				"number": 185.3
			},
			"Цена выхода": {
				"number": 190.7
			},
			"Комментарий": {
				"rich_text": [
					{
						"text": {
							"content": "Позиция открыта по сигналу от 20.06"
						}
					}
				]
			}
		}
	}

	# client.pages.create( **new_page)
	# 21185b6b-d4cc-816a-8ff6-d542fdaf02aa
