"""
24-hour local JSON cache for live price lookups, keyed by search query string.
Avoids re-hitting SerpApi for the same laptop within the TTL window.
"""

import json
import time
from pathlib import Path
from typing import Optional

DEFAULT_CACHE_PATH = Path(__file__).resolve().parents[1] / ".cache" / "serpapi_prices.json"
DEFAULT_TTL_SECONDS = 24 * 60 * 60


class PriceCache:
    def __init__(self, path: Path = DEFAULT_CACHE_PATH, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.path = path
        self.ttl_seconds = ttl_seconds

    def _read_all(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def get(self, key: str) -> Optional[dict]:
        entry = self._read_all().get(key)
        if not entry:
            return None
        if time.time() - entry["cached_at"] > self.ttl_seconds:
            return None
        return entry["value"]

    def set(self, key: str, value: dict) -> None:
        data = self._read_all()
        data[key] = {"cached_at": time.time(), "value": value}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))
