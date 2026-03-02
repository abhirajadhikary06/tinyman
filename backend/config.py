from typing import Optional, Dict

class CredentialProxy:
    """Independent custom proxy model layer for secure credential vaulting.
    Never logs or hardcodes real keys/tokens. All requests go through here."""
    def __init__(self, api_key: Optional[str] = None, session_headers: Optional[Dict] = None):
        self._api_key = api_key          # vaulted
        self._session_headers = session_headers or {}

    def get_headers(self) -> Dict:
        headers = self._session_headers.copy()
        if self._api_key:
            headers.setdefault("Authorization", f"Bearer {self._api_key}")
        return headers

    def make_request(self, method: str, url: str, **kwargs):
        """Secure proxy request - credentials never appear in logs."""
        import requests
        headers = self.get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        kwargs["headers"] = headers
        return requests.request(method, url, **kwargs)

# Full class source that will be injected into every generated SDK
PROXY_CLASS_CODE = """
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
"""