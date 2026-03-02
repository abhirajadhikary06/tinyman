import time
from typing import Optional

class URLCache:
    """24-hour cache based on target_url + mode (A/B)"""
    def __init__(self):
        self._store: dict = {}

    def get(self, key: str) -> Optional[str]:
        if key in self._store:
            data, ts = self._store[key]
            if time.time() - ts < 86400:  # 24 hours
                return data
            del self._store[key]
        return None

    def set(self, key: str, value: str):
        self._store[key] = (value, time.time())

cache = URLCache()