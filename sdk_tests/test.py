from sdk_tests.web_notion_sdk import WebNotionSDK

sdk = WebNotionSDK()

home_html = sdk.fetch_page("/")
print("Home HTML:", "ok" if home_html else "failed")

templates_html = sdk.list_items("/templates")
items = sdk.parse_items(templates_html)
print("Parsed items:", len(items))
print("First item:", items[0] if items else None)

meta = sdk.get_page_metadata(home_html)
print("Metadata:", meta)