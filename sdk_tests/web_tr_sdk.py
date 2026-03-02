import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import json

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
        extra_headers = kwargs.pop("headers", None)
        if extra_headers:
            headers.update(extra_headers)
        kwargs["headers"] = headers
        return requests.request(method, url, **kwargs)


class WebTracerootSDK:
    BASE_URL = "https://traceroot.ai"
    TIMEOUT = 15

    def __init__(self, proxy=None, listing_path="/"):
        self.proxy = proxy or CredentialProxy()
        self.listing_path = listing_path if listing_path else "/"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        })

    def fetch_page(self, path="", params=None):
        base = self.BASE_URL.rstrip("/")
        path = path.lstrip("/") if path else ""
        url = f"{base}/{path}" if path else base
        resp = self.proxy.make_request(
            "GET",
            url,
            params=params,
            timeout=self.TIMEOUT,
            headers=dict(self.session.headers),
        )
        resp.raise_for_status()
        return resp

    def search(self, query, page=1):
        params = {"search": query, "page": page} if page > 1 else {"search": query}
        resp = self.fetch_page(self.listing_path, params)
        return resp

    def list_items(self, page=1, **filters):
        params = {"page": page}
        params.update(filters)
        resp = self.fetch_page(self.listing_path, params)
        return resp

    def parse_items(self, html):
        soup = BeautifulSoup(html, "html.parser")
        items = []

        json_ld_items = self._extract_json_ld_items(soup)
        if json_ld_items:
            items.extend(json_ld_items)

        selectors = [
            "div[class*='item']", "div[class*='card']", "div[class*='product']",
            "article", "li[class*='item']", ".listing-item", ".product-card"
        ]
        elements = []
        for sel in selectors:
            elements = soup.select(sel)
            if elements:
                break
        if elements:
            for el in elements:
                title = None
                for sel in ["h2", "h3", "h4", ".title", ".name", "[class*='title']", "a"]:
                    node = el.select_one(sel)
                    if node and node.get_text(strip=True):
                        title = node.get_text(strip=True)
                        break
                price = None
                for sel in [".price", "[class*='price']", ".amount", ".cost"]:
                    node = el.select_one(sel)
                    if node:
                        price = node.get_text(strip=True)
                        break
                url = None
                link = el.find("a", href=True)
                if link:
                    url = urljoin(self.BASE_URL, link["href"])
                if title:
                    items.append({"title": title, "price": price, "url": url})

        if not items:
            seen = set()
            for link in soup.select("a[href]"):
                href = link.get("href", "").strip()
                text = link.get_text(" ", strip=True)
                if not href or not text:
                    continue
                full_url = urljoin(self.BASE_URL, href)
                parsed = urlparse(full_url)
                if parsed.netloc and "traceroot.ai" not in parsed.netloc:
                    continue
                if len(text) < 3:
                    continue
                key = (text.lower(), full_url)
                if key in seen:
                    continue
                seen.add(key)
                items.append({"title": text, "price": None, "url": full_url})
                if len(items) >= 25:
                    break

        return items

    def _extract_json_ld_items(self, soup):
        items = []
        scripts = soup.select("script[type='application/ld+json']")
        for script in scripts:
            raw = script.string or script.get_text(strip=True)
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue

            nodes = payload if isinstance(payload, list) else [payload]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                graph = node.get("@graph")
                graph_nodes = graph if isinstance(graph, list) else [node]
                for g in graph_nodes:
                    if not isinstance(g, dict):
                        continue
                    node_type = g.get("@type")
                    types = node_type if isinstance(node_type, list) else [node_type]
                    if not any(t in {"Product", "SoftwareApplication", "Service", "Article"} for t in types):
                        continue
                    name = g.get("name") or g.get("headline")
                    url = g.get("url")
                    offers = g.get("offers") if isinstance(g.get("offers"), dict) else {}
                    price = offers.get("price") if offers else None
                    if name or url:
                        items.append(
                            {
                                "title": str(name).strip() if name else None,
                                "price": str(price).strip() if price else None,
                                "url": urljoin(self.BASE_URL, str(url)) if url else None,
                            }
                        )
        return items

    def get_item_detail(self, path_or_url):
        if path_or_url.startswith("http"):
            url = path_or_url
        else:
            url = f"{self.BASE_URL}/{path_or_url.lstrip('/')}"
        resp = self.proxy.make_request("GET", url, timeout=self.TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = None
        for sel in ["h1", "h2.product-title", "[class*='title']"]:
            node = soup.select_one(sel)
            if node:
                title = node.get_text(strip=True)
                break
        if not title:
            meta_title = soup.select_one("meta[property='og:title'], meta[name='twitter:title']")
            if meta_title:
                title = meta_title.get("content", "").strip() or None
        price = None
        for sel in [".price", "[class*='price']", ".product-price", ".amount"]:
            node = soup.select_one(sel)
            if node:
                price = node.get_text(strip=True)
                break
        desc = None
        for sel in [".description", "[class*='desc']", "[class*='detail']", "meta[name='description']"]:
            node = soup.select_one(sel)
            if node:
                if node.name == "meta":
                    desc = node.get("content", "")
                else:
                    desc = node.get_text(strip=True)
                break
        return {"title": title, "price": price, "description": desc, "url": url}

    def paginate(self, html, current_url=None):
        soup = BeautifulSoup(html, "html.parser")
        next_selectors = [
            "a[rel='next']", "a.next", "a:-soup-contains('Next')",
            "a:-soup-contains('›')", ".pagination a:last-child", "nav a:last-child"
        ]
        for sel in next_selectors:
            link = soup.select_one(sel)
            if link and link.get("href"):
                return urljoin(self.BASE_URL, link["href"])
        page_selectors = [".pagination a", ".pages a", "nav a"]
        for sel in page_selectors:
            links = soup.select(sel)
            for link in links:
                text = link.get_text(strip=True)
                if text.isdigit() and int(text) > (parse_qs(urlparse(current_url or "").query).get("page", ["1"])[0]):
                    return urljoin(self.BASE_URL, link["href"])
        return None