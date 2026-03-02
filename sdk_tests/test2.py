from sdk_tests.web_scr_sdk import WebGetsocratixSDK

sdk = WebGetsocratixSDK()

home_resp = sdk.fetch_page("/")
print("Home fetch:", "ok" if home_resp and home_resp.status_code == 200 else "failed")

products_resp = sdk.list_items(page=1)
items = sdk.parse_items(products_resp.text)
print("Parsed products:", len(items))
print("First product:", items[0] if items else None)

search_resp = sdk.search("ai", page=1)
search_items = sdk.parse_items(search_resp.text)
print("Search results:", len(search_items))

sample_detail_path = "/"
if items and items[0].get("url"):
	sample_detail_path = items[0]["url"]

detail = sdk.get_item_detail(sample_detail_path)
print("Detail title:", detail.get("title"))

next_link = sdk.paginate(products_resp.text)
print("Next page link:", next_link)