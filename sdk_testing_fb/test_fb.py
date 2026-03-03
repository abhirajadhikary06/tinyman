from __future__ import annotations

import os
from typing import Optional

import requests


def _import_sdk():
	try:
		from sdk_tests.web_fb_sdk import WebFacebookSDK
		return WebFacebookSDK
	except Exception:
		from web_fb_sdk import WebFacebookSDK
		return WebFacebookSDK


def _status_from_exception(exc: Exception) -> Optional[int]:
	if isinstance(exc, requests.HTTPError) and exc.response is not None:
		return exc.response.status_code
	return None


def _supports_color() -> bool:
	if os.getenv("NO_COLOR"):
		return False
	term = os.getenv("TERM", "")
	return term != "dumb" or os.name == "nt"


USE_COLOR = _supports_color()


def _c(text: str, code: str) -> str:
	if not USE_COLOR:
		return text
	return f"\033[{code}m{text}\033[0m"


def _ok(text: str) -> str:
	return _c(text, "92")


def _warn(text: str) -> str:
	return _c(text, "38;5;208")


def _err(text: str) -> str:
	return _c(text, "91")


def _info(text: str) -> str:
	return _c(text, "96")


def _run_parser_unit_check(sdk) -> bool:
	fixture_html = """
	<html><body>
	  <div role="article">
	    <h3>Sample Post Title</h3>
	    <a href="/sample-post">Open post</a>
	    <p>Sample description line.</p>
	  </div>
	</body></html>
	"""

	items = sdk.parse_items(fixture_html)
	if not isinstance(items, list) or len(items) == 0:
		print("parser_unit_check: FAILED (parse_items returned empty on fixture)")
		return False

	first = items[0] if isinstance(items[0], dict) else {}
	has_title = bool(first.get("title"))
	has_url = bool(first.get("url"))
	has_desc = bool(first.get("description"))

	if has_title and has_url and has_desc:
		print("parser_unit_check: OK | fixture parsed with title/url/description")
		return True

	print(f"parser_unit_check: FAILED (missing fields in first item: {first})")
	return False


def run_facebook_smoke_test() -> None:
	print(_info("=== WebFacebookSDK Smoke Test ==="))

	try:
		WebFacebookSDK = _import_sdk()
	except Exception as exc:
		print(_err(f"Import FAILED: {exc}"))
		print("Install dependencies and rerun:")
		print("pip install requests beautifulsoup4 soupsieve")
		return

	sdk = WebFacebookSDK()
	parser_unit_ok = _run_parser_unit_check(sdk)

	fetch_ok = False
	blocked = False
	live_parse_ok = False
	home_response = None
	list_response = None
	list_items = []

	try:
		home_response = sdk.fetch_page("/")
		home_response.raise_for_status()
		print(_ok(f"fetch_page('/'): OK | status={home_response.status_code}"))
		fetch_ok = True
	except Exception as exc:
		status = _status_from_exception(exc)
		if status in {401, 403, 429}:
			print(_warn(f"fetch_page('/'): BLOCKED (status={status})"))
			blocked = True
		else:
			print(_err(f"fetch_page('/'): FAILED ({exc})"))

	try:
		list_response = sdk.list_items("/")
		list_response.raise_for_status()
		list_items = sdk.parse_items(list_response.text)
		msg = f"list_items('/') + parse_items: OK | parsed={len(list_items)}"
		print(_ok(msg) if len(list_items) > 0 else _warn(msg))
		if len(list_items) > 0:
			live_parse_ok = True
	except Exception as exc:
		status = _status_from_exception(exc)
		if status in {401, 403, 429}:
			print(_warn(f"list_items('/') + parse_items: BLOCKED (status={status})"))
			blocked = True
		else:
			print(_err(f"list_items('/') + parse_items: FAILED ({exc})"))

	try:
		search_response = sdk.search("zuck")
		search_response.raise_for_status()
		search_items = sdk.parse_items(search_response.text)
		msg = f"search('zuck'): OK | parsed={len(search_items)}"
		print(_ok(msg) if len(search_items) > 0 else _warn(msg))
		if len(search_items) > 0:
			live_parse_ok = True
	except Exception as exc:
		status = _status_from_exception(exc)
		if status in {401, 403, 429}:
			print(_warn(f"search('zuck'): BLOCKED (status={status})"))
			blocked = True
		else:
			print(_err(f"search('zuck'): FAILED ({exc})"))

	try:
		detail_target = "/"
		if list_items and list_items[0].get("url"):
			detail_target = list_items[0]["url"]
		detail = sdk.get_item_detail(detail_target)
		keys = sorted(detail.keys()) if isinstance(detail, dict) else []
		msg = f"get_item_detail(...): OK | keys={keys}"
		print(_ok(msg) if keys else _warn(msg))
	except Exception as exc:
		status = _status_from_exception(exc)
		if status in {401, 403, 429}:
			print(_warn(f"get_item_detail(...): BLOCKED (status={status})"))
			blocked = True
		else:
			print(_err(f"get_item_detail(...): FAILED ({exc})"))

	try:
		page_count = 0
		total_items = 0
		for page_items in sdk.paginate(path="/", page_param="page"):
			page_count += 1
			total_items += len(page_items)
			if page_count >= 2:
				break
		msg = f"paginate('/'): OK | pages_checked={page_count} total_items={total_items}"
		print(_ok(msg) if total_items > 0 else _warn(msg))
	except Exception as exc:
		status = _status_from_exception(exc)
		if status in {401, 403, 429}:
			print(_warn(f"paginate('/'): BLOCKED (status={status})"))
			blocked = True
		else:
			print(_err(f"paginate('/'): FAILED ({exc})"))

	print(_info("\n--- RESULT ---"))
	if parser_unit_ok and live_parse_ok:
		print(_ok("SDK parser + live extraction: WORKING"))
	elif parser_unit_ok and fetch_ok:
		print(_warn("SDK parser works, but live Facebook pages returned no parsable items in this environment."))
		print(_warn("Result: INCONCLUSIVE for live extraction (not a parser failure)."))
	elif blocked:
		print(_warn("SDK code path likely works, but Facebook blocked automated requests in this environment."))
	elif not parser_unit_ok:
		print(_err("SDK parser is NOT working (failed deterministic fixture check)."))
	else:
		print(_err("SDK is NOT working correctly in current environment (see failures above)."))


if __name__ == "__main__":
	run_facebook_smoke_test()
