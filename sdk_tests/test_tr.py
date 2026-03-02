from sdk_tests.web_tr_sdk import WebTracerootSDK
from bs4 import BeautifulSoup


def run_traceroot_smoke_test() -> None:
	sdk = WebTracerootSDK(listing_path="/")

	print("=== WebTracerootSDK Smoke Test ===")

	try:
		home_response = sdk.fetch_page("/")
		home_response.raise_for_status()
		print("fetch_page('/'): OK")
		print("home status/url/bytes:", home_response.status_code, home_response.url, len(home_response.text))
		home_soup = BeautifulSoup(home_response.text, "html.parser")
		page_title = home_soup.title.get_text(strip=True) if home_soup.title else None
		meta_desc = home_soup.select_one("meta[name='description'], meta[property='og:description']")
		headings = [h.get_text(strip=True) for h in home_soup.select("h1, h2") if h.get_text(strip=True)][:5]
		sample_links = [a.get("href") for a in home_soup.select("a[href]")[:5]]
		print("home title:", page_title)
		print("home meta description:", meta_desc.get("content") if meta_desc else None)
		print("home headings (top 5):", headings)
		print("home links (top 5):", sample_links)
	except Exception as exc:
		print(f"fetch_page('/'): FAILED ({exc})")
		return

	try:
		list_response = sdk.list_items(page=1)
		list_response.raise_for_status()
		list_items = sdk.parse_items(list_response.text)
		print(f"list_items(page=1): OK | parsed={len(list_items)}")
		print("parsed items preview (up to 3):", list_items[:3])
		print("parsed item urls (up to 5):", [item.get("url") for item in list_items[:5]])
	except Exception as exc:
		print(f"list_items/parse_items: FAILED ({exc})")
		list_items = []
		list_response = None

	try:
		search_response = sdk.search("ai", page=1)
		search_response.raise_for_status()
		search_items = sdk.parse_items(search_response.text)
		print(f"search('ai'): OK | parsed={len(search_items)}")
		print("search items preview (up to 3):", search_items[:3])
	except Exception as exc:
		print(f"search/parse_items: FAILED ({exc})")

	try:
		detail_target = "/"
		if list_items and list_items[0].get("url"):
			detail_target = list_items[0]["url"]
		detail = sdk.get_item_detail(detail_target)
		print("get_item_detail(...):", "OK" if detail is not None else "FAILED")
		print(
			"detail sample:",
			{k: detail.get(k) for k in ("title", "price", "description", "url")} if detail else None,
		)
		if detail and detail.get("description"):
			print("detail description snippet:", detail["description"][:200])
	except Exception as exc:
		print(f"get_item_detail: FAILED ({exc})")

	try:
		if list_response is not None:
			next_link = sdk.paginate(list_response.text, current_url=list_response.url)
			print(f"paginate(...): OK | next={next_link}")
		else:
			print("paginate(...): SKIPPED (no listing response)")
	except Exception as exc:
		print(f"paginate(...): FAILED ({exc})")


if __name__ == "__main__":
	run_traceroot_smoke_test()
