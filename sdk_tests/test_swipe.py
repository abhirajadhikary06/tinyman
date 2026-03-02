from sdk_tests.web_swipe_sdk import WebGetswipeSDK


def run_swipe_smoke_test() -> None:
	sdk = WebGetswipeSDK(listing_path="/")

	print("=== WebGetswipeSDK Smoke Test ===")

	try:
		home_response = sdk.fetch_page("/")
		home_response.raise_for_status()
		print("fetch_page('/'): OK")
	except Exception as exc:
		print(f"fetch_page('/'): FAILED ({exc})")
		return

	try:
		list_response = sdk.list_items(page=1)
		list_response.raise_for_status()
		list_items = sdk.parse_items(list_response.text)
		print(f"list_items(page=1): OK | parsed={len(list_items)}")
		print(f"first parsed item: {list_items[0] if list_items else None}")
	except Exception as exc:
		print(f"list_items/parse_items: FAILED ({exc})")
		list_items = []
		list_response = None

	try:
		search_response = sdk.search("invoice", page=1)
		search_response.raise_for_status()
		search_items = sdk.parse_items(search_response.text)
		print(f"search('invoice'): OK | parsed={len(search_items)}")
	except Exception as exc:
		print(f"search/parse_items: FAILED ({exc})")

	try:
		detail_target = "/"
		if list_items and list_items[0].get("url"):
			detail_target = list_items[0]["url"]
		detail = sdk.get_item_detail(detail_target)
		print("get_item_detail(...):", "OK" if detail is not None else "FAILED")
		print("detail sample:", {k: detail.get(k) for k in ("title", "price", "description")} if detail else None)
	except Exception as exc:
		print(f"get_item_detail: FAILED ({exc})")

	try:
		if list_response is not None:
			next_link = sdk.paginate(list_response)
			print(f"paginate(...): OK | next={next_link}")
		else:
			print("paginate(...): SKIPPED (no listing response)")
	except Exception as exc:
		print(f"paginate(...): FAILED ({exc})")


if __name__ == "__main__":
	run_swipe_smoke_test()
