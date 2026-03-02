from sdk_tests.web_scr_sdk import WebGetsocratixSDK


def run_check() -> None:
	sdk = WebGetsocratixSDK()

	print("=== WebGetsocratixSDK Output Check ===")

	try:
		home_resp = sdk.fetch_page("/")
		home_ok = bool(home_resp and home_resp.text and len(home_resp.text) > 0)
		print(f"fetch_page('/'): {'OK' if home_ok else 'FAILED'}")
	except Exception as exc:
		print(f"fetch_page('/'): FAILED ({exc})")
		return

	try:
		list_resp = sdk.list_items(page=1)
		list_html = list_resp.text if list_resp else ""
		items = sdk.parse_items(list_html)
		print(f"list_items(page=1): {'OK' if list_resp else 'FAILED'}")
		print(f"parse_items(...): {'OK' if items is not None else 'FAILED'}")
		print(f"items count: {len(items)}")
		if items:
			print(f"first item: {items[0]}")
	except Exception as exc:
		print(f"list/parse flow: FAILED ({exc})")
		items = []

	try:
		search_resp = sdk.search("ai", page=1)
		search_items = sdk.parse_items(search_resp.text)
		print(f"search('ai'): {'OK' if search_resp else 'FAILED'}")
		print(f"search parsed count: {len(search_items)}")
	except Exception as exc:
		print(f"search flow: FAILED ({exc})")

	try:
		detail_path = "/"
		if items and items[0].get("url"):
			detail_path = items[0]["url"]
		detail = sdk.get_item_detail(detail_path)
		has_any_detail = any(detail.get(k) for k in ("title", "price", "description"))
		print(f"get_item_detail(...): {'OK' if detail else 'FAILED'}")
		print(f"detail has parsed fields: {'YES' if has_any_detail else 'NO'}")
	except Exception as exc:
		print(f"get_item_detail flow: FAILED ({exc})")

	try:
		next_link = sdk.paginate(list_html)
		print(f"paginate(...): OK (next_link={next_link})")
	except Exception as exc:
		print(f"paginate(...): FAILED ({exc})")


if __name__ == "__main__":
	run_check()
