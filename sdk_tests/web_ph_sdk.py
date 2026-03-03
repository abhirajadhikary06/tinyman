import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import soupsieve

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
        import requests
        headers = self.get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        kwargs["headers"] = headers
        return requests.request(method, url, **kwargs)

class WebProducthuntSDK:
    BASE_URL = "https://www.producthunt.com"
    DEFAULT_TIMEOUT = 10

    def __init__(self, credential_proxy=None):
        self.proxy = credential_proxy or CredentialProxy()

    def _browser_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.BASE_URL,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def fetch_page(self, path="/"):
        url = urljoin(self.BASE_URL, path)
        resp = self.proxy.make_request("GET", url, headers=self._browser_headers(), timeout=self.DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp

    def search(self, query, path="/search"):
        params = {"q": query}
        url = urljoin(self.BASE_URL, path)
        resp = self.proxy.make_request("GET", url, params=params, headers=self._browser_headers(), timeout=self.DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp

    def list_items(self, listing_path="/"):
        return self.fetch_page(listing_path)

    def parse_items(self, html):
        soup = BeautifulSoup(html, "html.parser")
        items = []
        selectors = [
            '[data-test*="post-item"]',
            '.postItem',
            '[class*="post"]',
            '[class*="item"] a[href*="/posts/"]'
        ]
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for el in elements:
                    link = el.get('href')
                    if link and '/posts/' in link:
                        title_el = el.select_one('h3, [class*="title"], [class*="name"]') or el
                        title = title_el.get_text(strip=True) if title_el else None
                        items.append({
                            "title": title,
                            "url": urljoin(self.BASE_URL, link)
                        })
                break
        return items

    def get_item_detail(self, item_url):
        resp = self.proxy.make_request("GET", item_url, headers=self._browser_headers(), timeout=self.DEFAULT_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title_el = soup.select_one('h1, [data-test*="title"]')
        description_el = soup.select_one('[data-test*="description"], .description, [class*="content"]')
        return {
            "title": title_el.get_text(strip=True) if title_el else None,
            "description": description_el.get_text(strip=True) if description_el else None,
            "url": item_url
        }

    def paginate(self, path, page_param="page"):
        page = 1
        while True:
            params = {page_param: page}
            resp = self.proxy.make_request(
                "GET",
                urljoin(self.BASE_URL, path),
                params=params,
                headers=self._browser_headers(),
                timeout=self.DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            items = self.parse_items(resp.text)
            if not items:
                break
            yield items
            page += 1