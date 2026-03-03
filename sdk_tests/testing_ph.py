from __future__ import annotations

import re
from urllib.parse import urljoin

import requests


POST_PATH_RE = re.compile(r"^/posts/[a-z0-9-]+/?$", re.IGNORECASE)
PH_PATH_CANDIDATES = ["/", "/latest", "/posts", "/all"]


def _browser_headers() -> dict:
	return {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
		"Accept-Language": "en-US,en;q=0.9",
		"Referer": "https://www.producthunt.com/",
		"Cache-Control": "no-cache",
		"Pragma": "no-cache",
	}


def _norm(text: str) -> str:
	return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _canonical_post_url(base_url: str, href: str) -> str:
	full_url = urljoin(base_url, href)
	full_url = full_url.split("?", 1)[0].split("#", 1)[0]
	return full_url.rstrip("/")


def _is_post_href(href: str) -> bool:
	href = (href or "").strip()
	if not href:
		return False
	if href.startswith("http"):
		if "producthunt.com" not in href:
			return False
		href = "/" + href.split("producthunt.com", 1)[-1].lstrip("/")
	href = href.split("?", 1)[0].split("#", 1)[0]
	return bool(POST_PATH_RE.match(href))


def _extract_source_posts(base_url: str, path: str = "/", limit: int = 15) -> list[dict]:
	response = requests.get(
		urljoin(base_url, path),
		timeout=20,
		headers=_browser_headers(),
	)
	response.raise_for_status()
	html = response.text

	# Regex fallback extraction to keep this script independent and robust.
	links = re.findall(r'<a[^>]+href=["\']([^"\']*/posts/[^"\']*)["\'][^>]*>(.*?)</a>', html, flags=re.I | re.S)

	items: list[dict] = []
	seen: set[str] = set()
	for href, inner in links:
		if not _is_post_href(href):
			continue
		title = _norm(re.sub(r"<[^>]+>", " ", inner))
		if not title:
			continue

		url = _canonical_post_url(base_url, href)
		if url in seen:
			continue
		seen.add(url)
		items.append({"title": title, "url": url})

		if len(items) >= limit:
			break

	return items


def _extract_sdk_posts(sdk, path: str = "/", limit: int = 15) -> list[dict]:
	response = sdk.list_items(path)
	response.raise_for_status()
	raw_items = sdk.parse_items(response.text)

	items: list[dict] = []
	seen: set[str] = set()
	for item in raw_items:
		title = (item.get("title") or "").strip()
		url = (item.get("url") or "").strip()
		if not title or not url:
			continue
		if not _is_post_href(url):
			continue

		canonical = _canonical_post_url(sdk.BASE_URL, url)
		if canonical in seen:
			continue
		seen.add(canonical)

		items.append({"title": _norm(title), "url": canonical})
		if len(items) >= limit:
			break

	return items


def run_producthunt_manual_match() -> None:
	print("=== WebProducthuntSDK Smoke + Manual Match Test ===")

	try:
		from web_ph_sdk import WebProducthuntSDK
	except Exception as exc:
		print(f"SDK import failed: {exc}")
		print("Install dependencies and rerun:")
		print("pip install requests beautifulsoup4 soupsieve")
		return

	sdk = WebProducthuntSDK()
	working_path = None

	for candidate in PH_PATH_CANDIDATES:
		try:
			home = sdk.fetch_page(candidate)
			home.raise_for_status()
			working_path = candidate
			print(f"fetch_page('{candidate}'): OK")
			break
		except Exception as exc:
			print(f"fetch_page('{candidate}'): FAILED ({exc})")

	if working_path is None:
		print("All Product Hunt page probes were blocked (403/anti-bot).")
		print("Try again later or run behind a browser-backed session/proxy.")
		return

	try:
		search = sdk.search("ai", path="/search")
		search.raise_for_status()
		search_items = sdk.parse_items(search.text)
		print(f"search('ai'): OK | parsed={len(search_items)}")
	except Exception as exc:
		print(f"search('ai'): FAILED ({exc})")

	try:
		sdk_items = _extract_sdk_posts(sdk, path=working_path, limit=15)
		print(f"sdk snapshot ({working_path}): OK | extracted={len(sdk_items)}")
	except Exception as exc:
		print(f"sdk snapshot: FAILED ({exc})")
		sdk_items = []

	try:
		source_items = _extract_source_posts(sdk.BASE_URL, path=working_path, limit=15)
		print(f"source snapshot ({working_path}): OK | extracted={len(source_items)}")
	except Exception as exc:
		print(f"source snapshot: FAILED ({exc})")
		source_items = []

	sdk_preview = sdk_items[:10]
	source_preview = source_items[:10]

	print("\n--- SDK HOLDS (first 10) ---")
	if not sdk_preview:
		print("No SDK items captured.")
	else:
		for idx, item in enumerate(sdk_preview, start=1):
			print(f"{idx:02d}. {item['title']} | {item['url']}")

	print("\n--- ORIGINAL PAGE SNAPSHOT (first 10) ---")
	if not source_preview:
		print("No source items captured.")
	else:
		for idx, item in enumerate(source_preview, start=1):
			print(f"{idx:02d}. {item['title']} | {item['url']}")

	sdk_title_set = {_norm(item["title"]) for item in sdk_preview}
	src_title_set = {_norm(item["title"]) for item in source_preview}
	sdk_url_set = {item["url"] for item in sdk_preview}
	src_url_set = {item["url"] for item in source_preview}

	title_overlap = len(sdk_title_set & src_title_set)
	url_overlap = len(sdk_url_set & src_url_set)
	overlap_ratio = (url_overlap / len(source_preview)) if source_preview else 0.0

	print("\n--- MANUAL MATCH SUMMARY ---")
	print(f"SDK items shown: {len(sdk_preview)}")
	print(f"Source items shown: {len(source_preview)}")
	print(f"Title overlap count: {title_overlap}")
	print(f"URL overlap count: {url_overlap}")
	print(f"URL overlap ratio: {overlap_ratio:.2%}")

	print("\nDecision guide:")
	print("- 70%+ overlap: strong evidence SDK output matches live page content.")
	print("- 40-69% overlap: partial match, parser likely needs refinements.")
	print("- <40% overlap: low match, review parse_items selectors.")

	if not sdk_preview:
		print("\nFinal verdict: SDK returned no comparable Product Hunt post items.")
	elif not source_preview:
		print("\nFinal verdict: Could not capture source snapshot (site/network issue).")
	elif overlap_ratio >= 0.7:
		print("\nFinal verdict: PASS — SDK and manual source are well aligned.")
	elif overlap_ratio >= 0.4:
		print("\nFinal verdict: PARTIAL — usable, but parser can be improved.")
	else:
		print("\nFinal verdict: LOW MATCH — parser needs adjustment.")


if __name__ == "__main__":
	run_producthunt_manual_match()
