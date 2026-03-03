import requests
from urllib.parse import urljoin
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

class WebFacebookSDK:
    BASE_URL = "https://www.facebook.com"
    
    def __init__(self, credential_proxy=None):
        self.proxy = credential_proxy or CredentialProxy()
    
    def fetch_page(self, path="/"):
        url = urljoin(self.BASE_URL, path)
        resp = self.proxy.make_request("GET", url, timeout=10)
        resp.raise_for_status()
        return resp
    
    def search(self, query, path="/search/top/"):
        params = {"q": query}
        candidates = [path, "/search/", "/search/top/", "/"]
        last_error = None

        for candidate in candidates:
            try:
                url = urljoin(self.BASE_URL, candidate)
                resp = self.proxy.make_request("GET", url, params=params, timeout=10)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                return resp
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    last_error = exc
                    continue
                raise
            except Exception as exc:
                last_error = exc
                continue

        if last_error:
            raise last_error

        raise requests.HTTPError("Facebook search failed for all candidate paths")
    
    def list_items(self, listing_path="/"):
        resp = self.fetch_page(listing_path)
        return resp
    
    def parse_items(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        selectors = [
            'div[role="article"]',
            'div[data-pagelet]',
            'div:-soup-contains("post")',
            'div:-soup-contains("story")'
        ]
        items = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for el in elements:
                    item = {}
                    title_el = el.select_one('h1, h2, h3, h4, [role="heading"]')
                    if title_el:
                        item['title'] = title_el.get_text(strip=True)
                    link_el = el.select_one('a[href]')
                    if link_el:
                        item['url'] = urljoin(self.BASE_URL, link_el.get('href'))
                    desc_el = el.select_one('div:-soup-contains("description"), p, span')
                    if desc_el:
                        item['description'] = desc_el.get_text(strip=True)
                    if item:
                        items.append(item)
                break
        return items
    
    def get_item_detail(self, path):
        resp = self.fetch_page(path)
        soup = BeautifulSoup(resp.text, 'html.parser')
        detail = {}
        title_el = soup.select_one('h1, h2, h3, [role="heading"]')
        if title_el:
            detail['title'] = title_el.get_text(strip=True)
        content_el = soup.select_one('div:-soup-contains("content"), article, main')
        if content_el:
            detail['content'] = content_el.get_text(strip=True)
        return detail
    
    def paginate(self, path="/", page_param="page"):
        items = []
        page = 1
        while True:
            params = {page_param: page}
            url = urljoin(self.BASE_URL, path)
            resp = self.proxy.make_request("GET", url, params=params, timeout=10)
            resp.raise_for_status()
            page_items = self.parse_items(resp.text)
            if not page_items:
                break
            items.extend(page_items)
            page += 1
        return items