import requests
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from bs4 import BeautifulSoup
from soupsieve import select_one, select

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
        extra_headers = kwargs.pop("headers", None)
        if extra_headers:
            headers.update(extra_headers)
        kwargs["headers"] = headers
        return requests.request(method, url, **kwargs)


class WebGetnaoSDK:
    BASE_URL = "https://getnao.io"
    TIMEOUT = 15

    def __init__(self, proxy=None, listing_path="/"):
        self.proxy = proxy or CredentialProxy()
        self.listing_path = listing_path.lstrip("/")

    def fetch_page(self, path="", params=None, headers=None):
        url = urljoin(self.BASE_URL, path)
        request_kwargs = {"params": params, "timeout": self.TIMEOUT}
        if headers:
            request_kwargs["headers"] = headers
        resp = self.proxy.make_request("GET", url, **request_kwargs)
        resp.raise_for_status()
        return resp

    def search(self, query, page=1, params=None):
        params = params or {}
        params.setdefault("q", query)
        params.setdefault("page", page)
        return self.fetch_page(self.listing_path, params)

    def list_items(self, page=1, params=None):
        return self.search("", page, params)

    def parse_items(self, html):
        soup = BeautifulSoup(html, "html.parser")
        items = []

        selectors = [
            "article.item, div.product-card, div.listing-item, li.product",
            "div[class*='product'], div[class*='item'], a[href*='/product/']",
            ".grid-item, .card, [data-testid*='item']"
        ]

        for sel in selectors:
            nodes = select(soup, sel)
            if nodes:
                for node in nodes:
                    item = self._extract_item(node, soup)
                    if item:
                        items.append(item)
                if items:
                    break

        return items

    def _extract_item(self, node, context_soup):
        href = None
        link = select_one(node, "a") or node if node.name == "a" else select_one(node, "a[href]")
        if link and link.get("href"):
            href = urljoin(self.BASE_URL, link["href"])

        title_selectors = ["h2", "h3", ".title", ".name", "[class*='title']", "a"]
        title = None
        for sel in title_selectors:
            title_el = select_one(node, sel)
            if title_el:
                title = title_el.get_text(strip=True)
                break

        price_selectors = [".price", "[class*='price']", "[data-price]"]
        price = None
        for sel in price_selectors:
            price_el = select_one(node, sel)
            if price_el:
                price = price_el.get_text(strip=True)
                break

        if not title and href:
            title = urlparse(href).path.rstrip("/").split("/")[-1]

        if title or href:
            return {"title": title, "price": price, "url": href}
        return None

    def get_item_detail(self, path_or_url):
        url = urljoin(self.BASE_URL, path_or_url if path_or_url.startswith("/") else "/" + path_or_url)
        resp = self.fetch_page(url)
        return self.parse_detail(resp.text, url)

    def parse_detail(self, html, url=None):
        soup = BeautifulSoup(html, "html.parser")
        data = {"url": url, "title": None, "price": None, "description": None}

        title_selectors = ["h1", ".product-title", "[class*='title']"]
        for sel in title_selectors:
            el = select_one(soup, sel)
            if el:
                data["title"] = el.get_text(strip=True)
                break

        price_selectors = [".price", "[class*='price']", "[data-price]"]
        for sel in price_selectors:
            el = select_one(soup, sel)
            if el:
                data["price"] = el.get_text(strip=True)
                break

        desc_selectors = [".description", "[class*='description']", "meta[name='description']", "meta[property='og:description']"]
        for sel in desc_selectors:
            el = select_one(soup, sel)
            if el:
                if el.name == "meta":
                    data["description"] = el.get("content", "")
                else:
                    data["description"] = el.get_text(strip=True)
                break

        return data

    def paginate(self, html, base_path=None):
        soup = BeautifulSoup(html, "html.parser")
        next_url = None

        link_selectors = [
            "a[rel='next']", "a.next", "a[class*='next']",
            "a[aria-label*='next']", "a[aria-label*='Next']",
            "button[aria-label*='next']"
        ]

        for sel in link_selectors:
            el = select_one(soup, sel)
            if el and el.get("href"):
                next_url = urljoin(self.BASE_URL, el["href"])
                break

        if not next_url:
            page_selectors = ["a[href*='page']", ".pagination a"]
            for sel in page_selectors:
                links = select(soup, sel)
                for link in links:
                    text = link.get_text(strip=True).lower()
                    if text.isdigit() and int(text) > 1:
                        next_url = urljoin(self.BASE_URL, link.get("href"))
                        break
                if next_url:
                    break

        return next_url