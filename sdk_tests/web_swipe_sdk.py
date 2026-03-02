import requests
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup

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


class WebGetswipeSDK:
    BASE_URL = "https://getswipe.in"
    TIMEOUT = 15

    ITEM_SELECTORS = [
        "article.product-card",
        "div.product-item",
        "div[itemtype*='Product']",
        ".product-card",
        ".product-item",
        "div.listing-item",
        "a.product-link",
    ]

    TITLE_SELECTORS = ["h3", "h2", ".product-title", ".title", "[itemprop='name']", "a.product-name"]
    PRICE_SELECTORS = [".price", ".product-price", "[itemprop='price']", ".amount", "span[itemprop='price']"]
    LINK_SELECTORS = ["a[href]", "a.product-link", "a.item-link"]

    def __init__(self, proxy=None, listing_path="/"):
        self.proxy = proxy or CredentialProxy()
        self.listing_path = listing_path if listing_path else "/"

    def fetch_page(self, path=None, params=None):
        path = path or self.listing_path
        url = urljoin(self.BASE_URL, path)
        return self.proxy.make_request("GET", url, params=params, timeout=self.TIMEOUT)

    def search(self, query, page=1):
        params = {"q": query, "page": page} if page > 1 else {"q": query}
        return self.fetch_page(params=params)

    def list_items(self, page=1, category=None):
        params = {"page": page} if page > 1 else {}
        if category:
            params["category"] = category
        return self.fetch_page(params=params)

    def parse_items(self, html):
        items = []
        if not html:
            return items
        soup = BeautifulSoup(html, "html.parser")
        for selector in self.ITEM_SELECTORS:
            elements = soup.select(selector)
            if elements:
                for el in elements:
                    item = self._extract_item(el)
                    if item:
                        items.append(item)
                if items:
                    break
        return items

    def _extract_item(self, el):
        title, price, link = None, None, None
        for sel in self.TITLE_SELECTORS:
            node = el.select_one(sel)
            if node:
                title = node.get_text(strip=True)
                break
        for sel in self.PRICE_SELECTORS:
            node = el.select_one(sel)
            if node:
                price = node.get_text(strip=True)
                break
        for sel in self.LINK_SELECTORS:
            node = el.select_one(sel)
            if node and node.get("href"):
                link = urljoin(self.BASE_URL, node.get("href"))
                break
        if not title:
            title = el.get("title") or el.get("aria-label") or el.name
        if title or link:
            return {"title": title, "price": price, "url": link}
        return None

    def get_item_detail(self, path_or_url):
        url = path_or_url if path_or_url.startswith("http") else urljoin(self.BASE_URL, path_or_url)
        try:
            resp = self.proxy.make_request("GET", url, timeout=self.TIMEOUT)
            resp.raise_for_status()
            return self._parse_detail(resp.text)
        except requests.RequestException:
            return {}

    def _parse_detail(self, html):
        soup = BeautifulSoup(html, "html.parser")
        data = {"title": None, "price": None, "description": None}
        title_sel = ["h1", "h2", ".product-title", "[itemprop='name']"]
        for sel in title_sel:
            el = soup.select_one(sel)
            if el:
                data["title"] = el.get_text(strip=True)
                break
        price_sel = [".price", ".product-price", "[itemprop='price']", ".amount"]
        for sel in price_sel:
            el = soup.select_one(sel)
            if el:
                data["price"] = el.get_text(strip=True)
                break
        desc_sel = ["[itemprop='description']", ".description", ".product-desc", "meta[name='description']"]
        for sel in desc_sel:
            el = soup.select_one(sel)
            if el:
                data["description"] = el.get("content") or el.get_text(strip=True)
                break
        return data

    def paginate(self, response, next_text="next", page_param="page"):
        if not response or not hasattr(response, "text"):
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        next_sel = f"a:-soup-contains('{next_text}')", "a.next", ".pagination a:last-child", "a[rel='next']"
        for sel in next_sel:
            try:
                link = soup.select_one(sel)
                if link and link.get("href"):
                    return link.get("href")
            except Exception:
                continue
        current_url = response.url
        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)
        current_page = int(params.get(page_param, [1])[0])
        params[page_param] = [current_page + 1]
        new_query = "&".join(f"{k}={v[0]}" for k, v in params.items())
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}" if new_query else None