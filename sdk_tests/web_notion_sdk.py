import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

class CredentialProxy:
    def __init__(self, api_key=None, session_headers=None):
        self._api_key = api_key
        self._session_headers = session_headers or {}

    def get_headers(self):
        headers = self._session_headers.copy()
        if self._api_key:
            headers.setdefault("Authorization", f"Bearer {self._api_key}")
        return headers

    def make_request(self, method, url, **kwargs):
        headers = self.get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        kwargs["headers"] = headers
        return requests.request(method, url, **kwargs)


class WebNotionSDK:
    BASE_URL = "https://notion.com"

    def __init__(self, proxy=None, timeout=10, max_retries=3):
        self.proxy = proxy or CredentialProxy()
        self.timeout = timeout
        self.max_retries = max_retries

    def _fetch_with_retry(self, url, params=None):
        for attempt in range(self.max_retries):
            try:
                resp = self.proxy.make_request("GET", url, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp
                if resp.status_code == 429:
                    time.sleep(2 ** attempt)
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(1)
        return None

    def fetch_page(self, path="/", params=None):
        url = f"{self.BASE_URL}{path}" if path.startswith("/") else path
        resp = self._fetch_with_retry(url, params)
        return resp.text if resp else None

    def search(self, query, page=1):
        params = {"q": query, "page": page}
        html = self.fetch_page("/search", params)
        return html

    def list_items(self, path="/templates", page=1):
        params = {"page": page} if page > 1 else None
        html = self.fetch_page(path, params)
        return html

    def parse_items(self, html, selector=".card, .template-card, article, .product-item"):
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        items = []
        for el in soup.select(selector):
            title = el.get("title") or el.find(["h1", "h2", "h3", "a"])
            title = title.get_text(strip=True) if hasattr(title, "get_text") else str(title)
            link = el.find("a")
            href = link.get("href") if link else None
            if href and not href.startswith("http"):
                href = f"{self.BASE_URL}{href}"
            items.append({"title": title, "url": href, "raw": str(el)[:200]})
        return items

    def parse_navigation(self, html):
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        nav_items = []
        for a in soup.select("nav a, header a, .nav-link"):
            text = a.get_text(strip=True)
            href = a.get("href", "")
            if text and href:
                if not href.startswith("http"):
                    href = f"{self.BASE_URL}{href}" if href.startswith("/") else href
                nav_items.append({"label": text, "url": href})
        return nav_items

    def get_page_metadata(self, html):
        if not html:
            return {}
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        return {
            "title": title.get_text(strip=True) if title else None,
            "description": meta_desc.get("content") if meta_desc else None
        }