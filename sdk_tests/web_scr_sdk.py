import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs


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


class WebGetsocratixSDK:
    BASE_URL = "https://getsocratix.ai"

    def __init__(self, api_key=None, session_headers=None, timeout=15):
        self.proxy = CredentialProxy(api_key, session_headers)
        self.timeout = timeout

    def fetch_page(self, path="/", params=None):
        url = urljoin(self.BASE_URL, path)
        resp = self.proxy.make_request("GET", url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def search(self, query, page=1):
        params = {"q": query, "page": page} if query else {"page": page}
        resp = self.fetch_page("/", params=params)
        return resp

    def list_items(self, category=None, page=1):
        params = {"page": page}
        if category:
            params["category"] = category
        resp = self.fetch_page("/products", params=params)
        return resp

    def parse_items(self, html):
        soup = BeautifulSoup(html, "html.parser")
        items = []
        for card in soup.select("div.product-card, div.item, article.product, div.listing-item"):
            title_elem = card.select_one("h3, h2, .title, .product-title")
            price_elem = card.select_one(".price, .product-price, [class*='price']")
            link_elem = card.select_one("a[href]")
            img_elem = card.select_one("img[src]")
            if title_elem:
                items.append({
                    "title": title_elem.get_text(strip=True),
                    "price": price_elem.get_text(strip=True) if price_elem else None,
                    "url": urljoin(self.BASE_URL, link_elem.get("href", "")) if link_elem else None,
                    "image": img_elem.get("src") if img_elem else None,
                })
        return items

    def get_item_detail(self, item_path):
        resp = self.fetch_page(item_path)
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.select_one("h1, .product-title, .item-title")
        price = soup.select_one(".price, .product-price, [class*='price']")
        desc = soup.select_one(".description, .product-desc, .item-desc, [class*='desc']")
        return {
            "title": title.get_text(strip=True) if title else None,
            "price": price.get_text(strip=True) if price else None,
            "description": desc.get_text(strip=True) if desc else None,
            "html": resp.text,
        }

    def paginate(self, html):
        soup = BeautifulSoup(html, "html.parser")
        next_link = soup.select_one("a.next, a[rel='next'], .pagination a:last-child")
        if next_link and next_link.get("href"):
            return next_link["href"]
        return None